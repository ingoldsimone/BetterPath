import base64
import json
from google import genai
import os
from PIL import Image
import io
import re

# "gemini-flash-latest" always points to Google's newest stable Flash model,
# so it keeps working when older models are retired. Override with GEMINI_MODEL.
DEFAULT_MODEL = "gemini-flash-latest"


class DemoObstacleDetector:
    """Stand-in used when GEMINI_API_KEY is not set, so the app can be demoed
    without a key. It does not analyze the photo: every report is accepted as
    an obstacle (and labelled as demo mode) so it still affects routing."""

    def verify_obstacle(self, image_bytes: bytes, coords: tuple):
        return {
            "is_obstacle": True,
            "obstacle_type": "demo mode (no Gemini API key, photo not analyzed)",
            "confidence": 1.0,
            "severity": "MEDIUM",
        }


class GeminiObstacleDetector:
    def __init__(self):
        # SECURITY: Use environment variable instead of hardcoded key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Missing GEMINI_API_KEY environment variable")
        
        self.client = genai.Client(api_key=api_key)
        self.model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)

    def verify_obstacle(self, image_bytes: bytes, coords: tuple):
        try:
            # convert raw bytes → PIL image
            image = Image.open(io.BytesIO(image_bytes))
            
            # resize image if too large (Gemini has size limits)
            max_size = 1024
            if image.width > max_size or image.height > max_size:
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            # simplified, more direct prompt
            prompt = """
            Analyze this image for accessibility obstacles. Look for stairs, curbs, barriers, debris, or anything blocking pedestrian paths.

            Respond with valid JSON only:
            {
                "is_obstacle": true,
                "obstacle_type": "description here",
                "confidence": 0.85,
                "severity": "HIGH"
            }

            Confidence: 0.0-1.0, Severity: NONE/LOW/MEDIUM/HIGH
            """

            print(f"🔍 Sending image to Gemini API...")
            
            # generate content with better error handling
            try:
                response = self.client.models.generate_content(model=self.model_name, contents=[prompt, image])
                print(f"Received response from Gemini")
                
                # check for safety blocks
                if getattr(response, 'prompt_feedback', None):
                    if getattr(response.prompt_feedback, 'block_reason', None):
                        print(f"Content blocked: {response.prompt_feedback.block_reason}")
                        return self._create_error_response(f"Content blocked: {response.prompt_feedback.block_reason}")

                # check if response exists
                if not response:
                    print("No response from Gemini API")
                    return self._create_error_response("No response from Gemini API")
                
                # check for text attribute
                if not hasattr(response, 'text'):
                    print("Response object has no text attribute")
                    print(f"Response object: {dir(response)}")
                    return self._create_error_response("Response object has no text attribute")
                
                # Check if text is empty
                if not response.text:
                    print("Empty text response from Gemini API")
                    return self._create_error_response("Empty text response from Gemini API")

                response_text = response.text.strip()
                print(f"Raw Gemini response: '{response_text}'")

            except Exception as api_error:
                print(f"Gemini API error: {str(api_error)}")
                return self._create_error_response(f"Gemini API error: {str(api_error)}")

            # Clean response text
            text_out = response_text.strip()
            
            # Remove markdown code blocks if present
            if text_out.startswith('```json'):
                text_out = text_out.replace('```json', '').replace('```', '').strip()
            elif text_out.startswith('```'):
                text_out = text_out.replace('```', '').strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', text_out, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
            else:
                print(f"No JSON found in response: '{text_out}'")
                return self._fallback_analysis(text_out, "No JSON structure found")

            # Parse JSON
            try:
                analysis = json.loads(json_text)
                print(f"Successfully parsed JSON: {analysis}")
            except json.JSONDecodeError as json_error:
                print(f"JSON parse error: {json_error}")
                print(f"Attempted to parse: '{json_text}'")
                return self._fallback_analysis(text_out, str(json_error))

            # Validate and clean up the response
            analysis = self._validate_response(analysis)
            return analysis

        except Exception as e:
            print(f"General error in verify_obstacle: {str(e)}")
            return self._create_error_response(str(e))

    def _validate_response(self, analysis):
        """Validate and fix the analysis response"""
        # Ensure required fields exist
        required_fields = {
            "is_obstacle": False,
            "obstacle_type": "unknown",
            "confidence": 0.0,
            "severity": "NONE"
        }
        
        for field, default in required_fields.items():
            if field not in analysis:
                analysis[field] = default

        # Ensure proper data types
        analysis["is_obstacle"] = bool(analysis.get("is_obstacle", False))
        
        # Handle confidence as float
        try:
            analysis["confidence"] = float(analysis.get("confidence", 0.0))
        except (ValueError, TypeError):
            analysis["confidence"] = 0.0
            
        # Ensure confidence is between 0 and 1
        analysis["confidence"] = max(0.0, min(1.0, analysis["confidence"]))
        
        # Validate severity
        valid_severities = ["NONE", "LOW", "MEDIUM", "HIGH"]
        severity = str(analysis.get("severity", "NONE")).upper()
        if severity not in valid_severities:
            analysis["severity"] = "NONE"
        else:
            analysis["severity"] = severity

        return analysis

    def _create_error_response(self, error_message: str):
        """Create a standardized error response"""
        return {
            "error": error_message,
            "is_obstacle": False,
            "obstacle_type": "unknown",
            "confidence": 0.0,
            "severity": "NONE"
        }

    def _fallback_analysis(self, raw_text: str, json_error: str):
        """Attempt to extract meaning from non-JSON responses"""
        raw_lower = raw_text.lower()
        
        # Simple keyword-based fallback
        obstacle_keywords = [
            "obstacle", "barrier", "blocked", "stairs", "curb", 
            "debris", "construction", "parked car", "uneven",
            "step", "bump", "hole", "crack", "tree", "pole"
        ]
        
        is_obstacle = any(word in raw_lower for word in obstacle_keywords)
        
        # Try to extract confidence if mentioned
        confidence_match = re.search(r'confidence[:\s]*([0-9.]+)', raw_lower)
        if confidence_match:
            try:
                confidence = float(confidence_match.group(1))
                if confidence > 1.0:  # Handle percentage format
                    confidence = confidence / 100.0
                confidence = max(0.0, min(1.0, confidence))
            except ValueError:
                confidence = 0.3 if is_obstacle else 0.1
        else:
            confidence = 0.3 if is_obstacle else 0.1
        
        return {
            "error": f"JSON parse failed: {json_error}",
            "is_obstacle": is_obstacle,
            "obstacle_type": "detected_via_keywords" if is_obstacle else "unknown",
            "confidence": confidence,
            "severity": "LOW" if is_obstacle else "NONE",
            "raw_response": raw_text
        }
 
#text to speech methods
    
    def _extract_json_obj(self, text: str): #extracts json
        import re, json
        s = text.strip()
        if s.startswith("```json"):
            s = s.replace("```json", "").replace("```", "").strip()
        elif s.startswith("```"):
            s = s.replace("```", "").strip()
        m = re.search(r"\{[\s\S]*\}", s)
        if not m:
            return None, s
        jtxt = m.group(0)
        try:
            return json.loads(jtxt), jtxt
        except Exception:
            return None, jtxt

    #generate directions from steps
    def generate_accessible_directions(self, route_steps: list, user_profile: dict = None, obstacles: list = None):
        """
        route_steps: list of dicts like:
          {"instruction": "...", "distance_m": 120, "duration_s": 90,
           "start": {"lat": ..., "lng": ...}, "end": {"lat": ..., "lng": ...}}
        obstacles: list of dicts like:
          {"type": "STAIRS", "lat": ..., "lng": ..., "severity": "HIGH", "note": "..."}
        """
        user_profile = user_profile or {"mobility": "wheelchair", "preferences": {"avoid_stairs": True, "avoid_curbs": True}}
        obstacles = obstacles or []

        prompt = f"""
You generate concise, **accessible** walking directions suitable for screen readers.

User profile:
{json.dumps(user_profile, ensure_ascii=False)}

Route steps (ordered):
{json.dumps(route_steps, ensure_ascii=False)}

Known obstacles (may be empty):
{json.dumps(obstacles, ensure_ascii=False)}

Return **valid JSON only**:
{{
  "summary": "one-sentence overview",
  "spoken_instructions": [
    {{
      "idx": 0,
      "say": "Turn left on Forbes Ave for 100 meters.",
      "expected_distance_m": 100,
      "expected_duration_s": 80
    }}
  ]
}}

Rules:
- Keep each 'say' under ~140 characters.
- Use step instructions given; do not invent new streets.
- If stairs/curbs/blocks exist, clearly warn and suggest an alternative using given steps if possible.
        """.strip()

        try: #try catch for errors
            resp = self.client.models.generate_content(model=self.model_name, contents=prompt)
            txt = (getattr(resp, "text", "") or "").strip()
        except Exception as e:
            return {"error": f"Gemini error: {e}"}

        data, raw = self._extract_json_obj(txt)
        if not data:
            return {"error": "No JSON in model output", "raw": txt or raw}

        if "spoken_instructions" not in data or not isinstance(data["spoken_instructions"], list):
            return {"error": "Model output missing 'spoken_instructions'", "raw": data}
        return data

    #helper: use macOS say if present, else print lines
    def speak_plan(self, plan: dict, block: bool = True, pause_between: float = 0.25):
        import shutil, subprocess, time
        steps = plan.get("spoken_instructions", [])
        if not steps:
            print("No spoken_instructions to narrate.")
            return

        say_path = shutil.which("say")
        if not say_path:
            #print lines if not
            for s in steps:
                print("[TTS]", s.get("say", ""))
                time.sleep(pause_between)
            return

        #mac tts
        for s in steps:
            line = s.get("say", "")
            if not line:
                continue
            p = subprocess.Popen([say_path, line])
            if block:
                p.wait()
            time.sleep(pause_between)

#test function to debug API connectivity
def test_gemini_connection():
    """Test if Gemini API is working"""
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("No API key found")
            return False
            
        client = genai.Client(api_key=api_key)

        #simple text test
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", DEFAULT_MODEL),
            contents="Say 'Hello, API is working!'",
        )
        print(f"API Test Response: {response.text}")
        return True
        
    except Exception as e:
        print(f"API Test Failed: {e}")
        return False

#example usage with debugging
if __name__ == "__main__":
    #test API connection first
    print("Testing Gemini API connection")
    if not test_gemini_connection():
        print("API connection failed. Check your API key.")
        exit(1)
    
    #test detector
    print("Testing obstacle detector")
    detector = GeminiObstacleDetector()
    
    #test with image file
    try:
        with open("test_image.jpg", "rb") as f:
            image_bytes = f.read()
        
        result = detector.verify_obstacle(image_bytes, (0, 0))
        print("Final result:")
        print(json.dumps(result, indent=2))
        
    except FileNotFoundError:
        print("Test image not found. Please provide a valid image file.")
    except Exception as e:
        print(f"Error: {e}")
    
    #narration test
    try:
        steps = [
            {
                "instruction": "Head east on Fifth Ave toward Bigelow Blvd",
                "distance_m": 120,
                "duration_s": 90,
                "start": {"lat": 40.4442, "lng": -79.9542},
                "end": {"lat": 40.4446, "lng": -79.9530}
            },
            {
                "instruction": "Turn left onto Bigelow Blvd",
                "distance_m": 80,
                "duration_s": 60,
                "start": {"lat": 40.4446, "lng": -79.9530},
                "end": {"lat": 40.4449, "lng": -79.9535}
            }
        ]

        known_obstacles = [
            {"type": "STAIRS", "lat": 40.44455, "lng": -79.95310, "severity": "HIGH", "note": "Temporary staircase at corner"}
        ]

        profile = {"mobility": "wheelchair", "preferences": {"avoid_stairs": True}}

        print("Generating accessible spoken directions")
        plan = detector.generate_accessible_directions(route_steps=steps, user_profile=profile, obstacles=known_obstacles)
        print(json.dumps(plan, indent=2))

        #auto speak (mac os say or print fallback)
        if "error" not in plan:
            detector.speak_plan(plan)
        else:
            print("Skipping TTS due to plan error.")
    except Exception as e:
        print(f"Route narration error: {e}")

    # call using
        plan = detector.generate_accessible_directions(route_steps=steps)
        detector.speak_plan(plan)