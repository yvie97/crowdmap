import React, { useState, useEffect, useRef, useCallback } from 'react';
import { MapContainer, ImageOverlay, Polygon, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './App.css';

// Map image dimensions: 1520 x 1442
const MAP_WIDTH = 1520;
const MAP_HEIGHT = 1442;
const MAP_BOUNDS = [[0, 0], [MAP_HEIGHT, MAP_WIDTH]];

// API configuration - change this when deploying
const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000';
const WS_BASE = process.env.REACT_APP_WS_BASE || 'ws://localhost:8000';

// Fallback mock data - used when backend is not available
const MOCK_DATA = {
  area_225_2f_1: { count: 12, capacity: 20, level: 'high', timestamp: Date.now() / 1000 },
  area_225_2f_2: { count: 3, capacity: 20, level: 'low', timestamp: Date.now() / 1000 },
  area_225_2f_3: { count: 7, capacity: 20, level: 'medium', timestamp: Date.now() / 1000 },
  area_225_2f_4: { count: 1, capacity: 20, level: 'low', timestamp: Date.now() / 1000 },
};

// Define 4 clickable zones as polygon coordinates [y, x] in image pixel space
// In Leaflet CRS.Simple: [0,0] = bottom-left, [1442,1520] = top-right
// So Leaflet y = MAP_HEIGHT - image_y
const AREAS = [
  {
    // Area 1: Upper-middle corridor with desks/tables
    id: 'area_225_2f_1',
    name: 'Upper Corridor Study Area',
    polygon: [
      [1030, 360], [1030, 730], [1175, 730], [1175, 360]
    ],
  },
  {
    // Area 2: Upper-right open area (with angled wall)
    id: 'area_225_2f_2',
    name: 'Northeast Open Area',
    polygon: [
      [1130, 770], [1400, 770], [1400, 1070], [1130, 920]
    ],
  },
  {
    // Area 3: Room 222 Collaboration (small green room on the map)
    id: 'area_225_2f_3',
    name: '222 Collaboration',
    polygon: [
      [670, 220], [670, 345], [760, 345], [760, 220]
    ],
  },
  {
    // Area 4: Room 202 Broadcast Room (gray room at bottom)
    id: 'area_225_2f_4',
    name: '202 Broadcast Room',
    polygon: [
      [480, 600], [480, 830], [575, 830], [575, 600]
    ],
  },
];

// Color based on backend's level field
function getColorFromLevel(level) {
  switch (level) {
    case 'low': return '#22c55e';
    case 'medium': return '#f59e0b';
    case 'high': return '#ef4444';
    default: return '#9ca3af';
  }
}

function capitalizeLevel(level) {
  if (!level) return 'Unknown';
  return level.charAt(0).toUpperCase() + level.slice(1);
}

function FitBounds() {
  const map = useMap();
  React.useEffect(() => {
    map.fitBounds(MAP_BOUNDS);
  }, [map]);
  return null;
}

function FindSeatBanner({ recommendations }) {
  if (!recommendations || recommendations.length === 0) return null;

  const best = recommendations[0]; // Already sorted by backend (least crowded first)
  const areaInfo = AREAS.find(a => a.id === best.area_id);
  const name = areaInfo?.name || best.area_id;
  const count = best.count ?? 0;

  return (
    <div className="find-seat-banner">
      <span className="find-seat-icon">💡</span>
      <span>
        <strong>Find me a seat:</strong> {name} — only <strong>{count}</strong> {count === 1 ? 'person' : 'people'} detected
      </span>
    </div>
  );
}

function App() {
  const [areaData, setAreaData] = useState(MOCK_DATA);
  const [recommendations, setRecommendations] = useState([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  // Fetch initial data from GET /api/areas
  const fetchAreas = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/areas`);
      if (!res.ok) throw new Error('API not available');
      const data = await res.json();
      const mapped = {};
      data.forEach((item) => {
        mapped[item.area_id] = {
          count: item.count,
          capacity: item.capacity,
          level: item.level,
          timestamp: item.timestamp,
        };
      });
      setAreaData(mapped);
    } catch (err) {
      console.warn('Backend not available, using mock data:', err.message);
    }
  }, []);

  // Fetch recommendations from GET /api/recommend
  const fetchRecommendations = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/recommend`);
      if (!res.ok) throw new Error('API not available');
      const data = await res.json();
      setRecommendations(data);
    } catch (err) {
      console.warn('Recommend API not available:', err.message);
      // Fallback: sort current areas by count
      const fallback = Object.entries(areaData)
        .map(([id, d]) => ({ area_id: id, count: d.count, capacity: d.capacity, level: d.level }))
        .sort((a, b) => a.count - b.count);
      setRecommendations(fallback);
    }
  }, [areaData]);

  // Connect WebSocket for real-time push updates
  useEffect(() => {
    function connectWS() {
      const ws = new WebSocket(`${WS_BASE}/ws/density`);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          setAreaData((prev) => {
            const updated = { ...prev };
            msg.areas.forEach((item) => {
              updated[item.area_id] = {
                ...updated[item.area_id],
                count: item.count,
                level: item.level,
                timestamp: msg.timestamp,
              };
            });
            return updated;
          });
        } catch (err) {
          console.warn('WebSocket message parse error:', err);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected, reconnecting in 3s...');
        setConnected(false);
        setTimeout(connectWS, 3000);
      };

      ws.onerror = (err) => {
        console.warn('WebSocket error:', err);
        ws.close();
      };

      wsRef.current = ws;
    }

    fetchAreas();
    fetchRecommendations();
    connectWS();

    // Refresh recommendations every 30 seconds
    const recInterval = setInterval(fetchRecommendations, 30000);

    return () => {
      clearInterval(recInterval);
      if (wsRef.current) wsRef.current.close();
    };
  }, [fetchAreas, fetchRecommendations]);

  return (
    <div className="App">
      <header className="app-header">
        <h1>NEU Seattle — 225 Second Floor</h1>
        <p className="subtitle">Real-time Study Space Occupancy</p>
        <span className={`connection-badge ${connected ? 'connected' : 'disconnected'}`}>
          {connected ? '● Live' : '○ Offline (mock data)'}
        </span>
      </header>

      <FindSeatBanner recommendations={recommendations} />

      <div className="map-wrapper">
        <MapContainer
          crs={L.CRS.Simple}
          bounds={MAP_BOUNDS}
          maxBounds={MAP_BOUNDS}
          maxBoundsViscosity={1.0}
          style={{ height: '70vh', width: '100%', background: '#e5e7eb' }}
          zoomSnap={0.25}
          minZoom={-1}
          maxZoom={2}
          attributionControl={false}
        >
          <FitBounds />
          <ImageOverlay url="/assets/floor_map.png" bounds={MAP_BOUNDS} />

          {AREAS.map((area) => {
            const info = areaData[area.id] || {};
            const count = info.count ?? 0;
            const level = info.level || 'low';
            const capacity = info.capacity;
            const color = getColorFromLevel(level);

            return (
              <Polygon
                key={area.id}
                positions={area.polygon}
                pathOptions={{
                  color: color,
                  fillColor: color,
                  fillOpacity: 0.25,
                  weight: 2,
                }}
                eventHandlers={{
                  mouseover: (e) => {
                    e.target.setStyle({ fillOpacity: 0.45 });
                  },
                  mouseout: (e) => {
                    e.target.setStyle({ fillOpacity: 0.25 });
                  },
                }}
              >
                <Popup>
                  <div className="popup-content">
                    <h3>{area.name}</h3>
                    <div className="popup-count" style={{ color }}>
                      {count} {count === 1 ? 'person' : 'people'}
                      {capacity && <span className="popup-capacity"> / {capacity} capacity</span>}
                    </div>
                    <div className="popup-label" style={{ background: color }}>
                      {capitalizeLevel(level)}
                    </div>
                    <div className="popup-id">ID: {area.id}</div>
                    <div className="popup-time">
                      Updated: {new Date((info.timestamp ?? 0) * 1000).toLocaleTimeString()}
                    </div>
                  </div>
                </Popup>
              </Polygon>
            );
          })}
        </MapContainer>
      </div>

      <div className="legend">
        <h3>Occupancy Legend</h3>
        <div className="legend-items">
          <span className="legend-item"><span className="dot" style={{ background: '#22c55e' }}></span> Low</span>
          <span className="legend-item"><span className="dot" style={{ background: '#f59e0b' }}></span> Medium</span>
          <span className="legend-item"><span className="dot" style={{ background: '#ef4444' }}></span> High</span>
        </div>
      </div>
    </div>
  );
}

export default App;
