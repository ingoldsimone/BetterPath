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
- MapLibre GL JS + OpenFreeMap  
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
  - `memory_store.py`  
  - `graph_edge.py`  
  - `graph_node.py`  
  - `obstacle.py`  
  > Framework for mapping building and hazard coordinates. Database connectivity  

- **Demo Data**  
  - `data/graph_nodes.json`  
  - `data/graph_edges.json`  
  > Campus walking graph, used when no MongoDB database is configured.  

- **Navigation Components**  
  - `build_graph.py`  
  - `coordinate_calc.py`  
  - `google_tts.py`  
  - `graph_points.txt`  
  - `navigation_service.py`  
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
> Provides a **MapLibre-powered** user interface for navigation.  

### Optional Features  
- `insideEstimate.ts` — estimates travel time to specific floors for vertical navigation.  

---

##  AI Tools Used  
- GitHub Copilot  
- Claude  

---

##  Setup & Installation  

No API keys or database are needed to run the demo.

### Install  
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```
(On Windows, use `.venv\Scripts\python` instead of `.venv/bin/python`.)

### Run  
The backend also serves the frontend, so one command starts everything:
```bash
.venv/bin/python -m uvicorn fastAPI:app --port 8000
```
Then open http://127.0.0.1:8000/frontend/index.html. Use port 8000: the frontend expects the API there.

### Optional Environment Variables  
- `MONGO_URI` — MongoDB connection string. Without it, the app uses the graph in `data/` and keeps obstacle reports in memory (cleared on restart).
- `MONGO_DB_NAME` — database name (default `hackathon`).
- `GEMINI_API_KEY` — enables Gemini verification of obstacle photos. Without it, the app runs in demo mode: photos are not analyzed and every report is accepted as an obstacle.
- `GEMINI_MODEL` — Gemini model to use (default `gemini-flash-latest`).
