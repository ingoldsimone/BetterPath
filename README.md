# BetterPath: Accessible Navigation on Campus 

**Built for SteelHacks XII**  

---

##  Contributors  
- Simon Goldin — [simongoldin06@gmail.com](mailto:simongoldin06@gmail.com)  
- Vladimir Deianov — [Deyanovva@gmail.com](mailto:Deyanovva@gmail.com)  
- Diana Lysova — [dianaelysova@gmail.com](mailto:dianaelysova@gmail.com)  
- Evgenii Venediktov — [e.i.venediktov@gmail.com](mailto:e.i.venediktov@gmail.com)  

---

##  Languages, Frameworks, and Libraries  
- MapBox API  
- Gemini API  
- Python  
- TypeScript  
- JavaScript  
- MongoDB / Atlas  

---

## 📖 Overview  
**BetterPath** is a navigation app that allows users to upload photos of hazards to further inform navigation and ETA.  
The project was designed with **accessibility in mind**, helping users find the nearest accessible entrance.  

---

## 📂 Project Structure  

### Backend  
- **Core Modules**  
  - `coords.py`  
  - `database.py`  
  - `graph_edge.py`  
  - `graph_node.py`  
  - `obstacle.py`  
  > Framework for mapping building and hazard coordinates. Database connectivity  

- **Navigation Components**  
  - `build_graph.py`  
  - `coordinate_calc.py`  
  - `google_tts.py`  
  - `graph_points.txt`  
  - `navigator.py`  
  - `requirements.txt`  
  - `result_graph.txt`  
  - `streets_list.txt`  
  > Handle graph calculation, pathfinding, and data storage.  

- **API**  
  - `fastAPI.py` — creates the  Fast API for the program.  

- **Photo Validation**  
  - `gemini_obstacle_detector.py` — verifies user-uploaded obstacle photos and updates navigation accordingly.  

### Frontend  
- `script.js`  
- `index.html`  
> Provides a **MapBox-powered** user interface for navigation.  

### Optional Features  
- `insideEstimate.ts` — estimates travel time to specific floors for vertical navigation.  

---

##  AI Tools Used  
- GitHub Copilot  
- Claude  

---

##  Setup & Installation  

### Run Frontend  
```bash
cd frontend
python -m http.server 8000 --bind 127.0.0.1
### Backend in a separate terminal
uvicorn fastAPI:app --reload --host 0.0.0.0 --port 8000
