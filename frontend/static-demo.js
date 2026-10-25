// Browser-only version of the backend, used when the app is hosted as a
// static site (GitHub Pages), where the Python server can't run.
// StaticNavigator is a direct port of navigation/navigation_service.py so
// both versions return the same routes.

// On GitHub Pages, or locally with ?static in the URL
const STATIC_MODE =
  typeof location !== "undefined" &&
  (location.hostname.endsWith("github.io") || new URLSearchParams(location.search).has("static"));

class StaticNavigator {
  constructor(nodeDocs, edgeDocs) {
    this.nodes = new Map(); // nodeId -> {id, coords: [lat, lng], name, type, neighbors}
    this.buildingNodes = new Map(); // lowercase building name -> nodeId
    this.obstacles = []; // {coords: {lat, lng}, active, ai_verified}

    for (const doc of nodeDocs) {
      if (doc.active !== true) continue;
      const name = doc.name;
      const type = doc.type ?? "waypoint";
      this.nodes.set(doc.nodeId, {
        id: doc.nodeId,
        coords: [doc.coordinates.lat, doc.coordinates.lng],
        name,
        type,
        neighbors: [],
      });
      if (type === "building" || name.toLowerCase().includes("entrance")) {
        this.buildingNodes.set(name.toLowerCase().trim(), doc.nodeId);
      }
    }

    for (const doc of edgeDocs) {
      if (doc.active !== true) continue;
      if (this.nodes.has(doc.from)) this.nodes.get(doc.from).neighbors.push(doc.to);
      if (this.nodes.has(doc.to)) this.nodes.get(doc.to).neighbors.push(doc.from);
    }
  }

  getAvailableBuildings() {
    return [...this.buildingNodes.keys()];
  }

  getBuildingNode(name) {
    return this.buildingNodes.get(name.toLowerCase().trim());
  }

  // Same metric as the Python KDTree query: straight-line distance in lat/lng degrees
  findNearestNode(lat, lng) {
    let best = null;
    let bestDist = Infinity;
    for (const node of this.nodes.values()) {
      const d = (node.coords[0] - lat) ** 2 + (node.coords[1] - lng) ** 2;
      if (d < bestDist) {
        bestDist = d;
        best = node.id;
      }
    }
    return best;
  }

  static haversineDistance([lat1, lng1], [lat2, lng2]) {
    const rad = (x) => (x * Math.PI) / 180;
    const dlat = rad(lat2) - rad(lat1);
    const dlng = rad(lng2) - rad(lng1);
    const a =
      Math.sin(dlat / 2) ** 2 +
      Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(dlng / 2) ** 2;
    return 2 * Math.asin(Math.sqrt(a)) * 6371000;
  }

  getBlockedNodes() {
    const blocked = new Set();
    for (const obstacle of this.obstacles) {
      if (!obstacle.active || !obstacle.ai_verified) continue;
      const { lat, lng } = obstacle.coords;
      const nearest = this.findNearestNode(lat, lng);
      if (nearest !== null) {
        const distance = StaticNavigator.haversineDistance([lat, lng], this.nodes.get(nearest).coords);
        if (distance <= 10) blocked.add(nearest); // 10 meter threshold, as in Python
      }
    }
    return blocked;
  }

  // Dijkstra's algorithm, matching the Python version (heap ordered by distance, then node id)
  findPath(startBuilding, endBuilding) {
    const startId = this.getBuildingNode(startBuilding);
    const endId = this.getBuildingNode(endBuilding);
    if (!startId || !endId) return null;

    const blocked = this.getBlockedNodes();
    const distances = new Map([...this.nodes.keys()].map((id) => [id, Infinity]));
    distances.set(startId, 0);
    const previous = new Map();
    const visited = new Set();
    const heap = new MinHeap();
    heap.push([0, startId]);

    while (heap.size > 0) {
      let [, current] = heap.pop();
      if (visited.has(current) || blocked.has(current)) continue;
      visited.add(current);

      if (current === endId) {
        const path = [];
        while (current !== undefined) {
          path.push(current);
          current = previous.get(current);
        }
        path.reverse();
        return {
          path_nodes: path,
          coordinates: path.map((id) => {
            const [lat, lng] = this.nodes.get(id).coords;
            return [lng, lat]; // GeoJSON order
          }),
          blocked_nodes: [...blocked],
        };
      }

      for (const neighbor of this.nodes.get(current).neighbors) {
        if (visited.has(neighbor) || blocked.has(neighbor)) continue;
        if (!this.nodes.has(neighbor)) continue;
        const weight = StaticNavigator.haversineDistance(
          this.nodes.get(current).coords,
          this.nodes.get(neighbor).coords
        );
        const newDistance = distances.get(current) + weight;
        if (newDistance < distances.get(neighbor)) {
          distances.set(neighbor, newDistance);
          previous.set(neighbor, current);
          heap.push([newDistance, neighbor]);
        }
      }
    }
    return null;
  }
}

// Binary min-heap of [distance, nodeId], ordered like Python's heapq on tuples
class MinHeap {
  constructor() {
    this.items = [];
  }
  get size() {
    return this.items.length;
  }
  static less(a, b) {
    return a[0] < b[0] || (a[0] === b[0] && a[1] < b[1]);
  }
  push(item) {
    const items = this.items;
    items.push(item);
    let i = items.length - 1;
    while (i > 0) {
      const parent = (i - 1) >> 1;
      if (!MinHeap.less(items[i], items[parent])) break;
      [items[i], items[parent]] = [items[parent], items[i]];
      i = parent;
    }
  }
  pop() {
    const items = this.items;
    const top = items[0];
    const last = items.pop();
    if (items.length > 0) {
      items[0] = last;
      let i = 0;
      for (;;) {
        const left = 2 * i + 1;
        const right = left + 1;
        let smallest = i;
        if (left < items.length && MinHeap.less(items[left], items[smallest])) smallest = left;
        if (right < items.length && MinHeap.less(items[right], items[smallest])) smallest = right;
        if (smallest === i) break;
        [items[i], items[smallest]] = [items[smallest], items[i]];
        i = smallest;
      }
    }
    return top;
  }
}

// Stand-in for the backend API calls the frontend makes, in static mode
const StaticApi = {
  _navigator: null,

  async _load() {
    if (!this._navigator) {
      const [nodes, edges] = await Promise.all([
        fetch("../data/graph_nodes.json").then((r) => r.json()),
        fetch("../data/graph_edges.json").then((r) => r.json()),
      ]);
      this._navigator = new StaticNavigator(nodes, edges);
    }
    return this._navigator;
  },

  // Like GET /buildings
  async buildings() {
    return (await this._load()).getAvailableBuildings();
  },

  // Like GET /directions; throws with the same message the API returns on 404
  async directions(start, end) {
    const navigator = await this._load();
    const result = navigator.findPath(start.toLowerCase().trim(), end.toLowerCase().trim());
    if (!result) {
      throw new Error(
        `No path found between '${start}' and '${end}'. Available buildings: ${navigator.getAvailableBuildings().join(", ")}`
      );
    }
    return {
      start,
      end,
      path_found: true,
      route_coordinates: result.coordinates,
      path_nodes: result.path_nodes,
      blocked_nodes: result.blocked_nodes,
      message: `Route found from ${start} to ${end}`,
    };
  },
};

// Export for testing under Node; no effect in the browser
if (typeof module !== "undefined") module.exports = { StaticNavigator, MinHeap };
