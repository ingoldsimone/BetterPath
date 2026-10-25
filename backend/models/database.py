import os

# Set MONGO_URI to use a MongoDB database. Without it, the app runs in demo
# mode on the graph data in data/, with obstacle reports kept in memory.
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB_NAME", "hackathon")

if MONGO_URI:
    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]

    obstacles_collection = db["obstacles"]
    nodes_collection = db["graph_nodes"]
    edges_collection = db["graph_edges"]
    print("Using MongoDB database")
else:
    from backend.models.memory_store import load_demo_collections

    obstacles_collection, nodes_collection, edges_collection = load_demo_collections()
    print("MONGO_URI not set: using demo data from data/ (obstacle reports reset on restart)")
