import React, { useState, useEffect, useRef, useCallback } from 'react';
import { MapContainer, ImageOverlay, Polygon, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './App.css';

const MAP_WIDTH = 1520;
const MAP_HEIGHT = 1442;
const MAP_BOUNDS = [[0, 0], [MAP_HEIGHT, MAP_WIDTH]];
const MAP_MAX_BOUNDS = [[-300, -200], [MAP_HEIGHT + 1200, MAP_WIDTH + 200]];
const MAP_BG = 'rgb(208, 213, 219)';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000';
const WS_BASE  = process.env.REACT_APP_WS_BASE  || 'ws://localhost:8000';

const MOCK_DATA = {
  area_225_2f_1: { count: 8,  capacity: 10, level: 'high',   timestamp: Date.now() / 1000 },
  area_225_2f_2: { count: 3,  capacity: 20, level: 'low',    timestamp: Date.now() / 1000 },
  area_225_2f_3: { count: 7,  capacity: 20, level: 'medium', timestamp: Date.now() / 1000 },
  area_225_2f_4: { count: 3,  capacity: 10, level: 'medium', timestamp: Date.now() / 1000 },
};

const AREAS = [
  { id: 'area_225_2f_1', name: 'North Corridor',      shortName: 'ZONE A', polygon: [[1045, 545],[1045, 1000],[1107, 1000],[1107, 545]] },
  { id: 'area_225_2f_2', name: 'Northeast Open Area', shortName: 'ZONE B', polygon: [[1130,980],[1435,980],[1435,1190],[1130,1317]] },
  { id: 'area_225_2f_3', name: 'Northwest Open Area', shortName: 'ZONE C', polygon: [[1180,157],[1180,563],[1435,563],[1435,157]] },
  { id: 'area_225_2f_4', name: 'East Corridor',       shortName: 'ZONE D', polygon: [[480,1075],[480,1133],[825,1133],[825,1075]] },
];

const HISTORY_LEN = 14;

function getColorFromLevel(level) {
  switch (level) {
    case 'low':    return '#22c55e';
    case 'medium': return '#f59e0b';
    case 'high':   return '#ef4444';
    default:       return '#64748b';
  }
}

/** Shoelace formula — polygon points are [lat, lng] */
function polygonArea(pts) {
  let area = 0;
  for (let i = 0; i < pts.length; i++) {
    const [y1, x1] = pts[i];
    const [y2, x2] = pts[(i + 1) % pts.length];
    area += x1 * y2 - x2 * y1;
  }
  return Math.abs(area) / 2;
}

// Pre-compute each zone's area in map units²
const AREA_SQUNITS = Object.fromEntries(
  AREAS.map(a => [a.id, polygonArea(a.polygon)])
);

// Thresholds in people per 10 000 map-unit²
// Max full-capacity density across zones ≈ 5.0 (East Corridor 10p / ~20k u²)
const D_LOW = 1.65;   // < 33 % of max
const D_HIGH = 3.3;   // > 66 % of max
const D_MAX  = 5.0;

function getDensityInfo(count, areaId) {
  const sq  = AREA_SQUNITS[areaId] || 1;
  const d   = (count / sq) * 10000;               // people per 10k u²
  const pct = Math.min((d / D_MAX) * 100, 100);
  const level = d < D_LOW ? 'low' : d < D_HIGH ? 'medium' : 'high';
  return { pct, level };
}

function capitalizeLevel(level) {
  if (!level) return 'Unknown';
  return level.charAt(0).toUpperCase() + level.slice(1);
}

/** Seed realistic-looking history from a base count */
function seedHistory(baseCount, capacity) {
  const arr = [];
  let cur = baseCount;
  for (let i = 0; i < HISTORY_LEN; i++) {
    cur = Math.max(0, Math.min(capacity, cur + Math.round((Math.random() - 0.45) * 3)));
    arr.push(cur);
  }
  return arr;
}

function initHistory() {
  const h = {};
  AREAS.forEach(a => {
    h[a.id] = seedHistory(MOCK_DATA[a.id]?.count ?? 0, MOCK_DATA[a.id]?.capacity ?? 20);
  });
  return h;
}

function FitBounds() {
  const map = useMap();
  React.useEffect(() => {
    map.fitBounds(MAP_BOUNDS, { padding: [0, 0] });
  }, [map]);
  return null;
}

/* ── Occupancy history sparkline chart ───────── */
function OccupancyChart({ historyData, areaData }) {
  const W = 260, H = 90;
  const pL = 26, pR = 8, pT = 8, pB = 14;
  const cW = W - pL - pR, cH = H - pT - pB;

  const allVals = Object.values(historyData).flat();
  const maxVal = Math.max(...allVals, 5);

  function toPolyline(pts) {
    return pts.map((v, i) => {
      const x = pL + (i / (pts.length - 1)) * cW;
      const y = pT + cH - (v / maxVal) * cH;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
  }

  const gridYs = [0, 0.5, 1].map(t => ({ y: pT + cH * (1 - t), label: Math.round(maxVal * t) }));

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
      {/* Grid lines */}
      {gridYs.map((g, i) => (
        <g key={i}>
          <line x1={pL} y1={g.y} x2={pL + cW} y2={g.y} stroke="#e2e8f0" strokeWidth="1" />
          <text x={pL - 3} y={g.y + 3.5} fontSize="8" fill="#94a3b8" textAnchor="end">{g.label}</text>
        </g>
      ))}
      {/* Zone lines */}
      {AREAS.map(area => {
        const data = historyData[area.id];
        if (!data || data.length < 2) return null;
        const info = areaData[area.id] || {};
        const color = getColorFromLevel(info.level || 'low');
        const pts = toPolyline(data);
        const last = pts.split(' ').pop().split(',');
        return (
          <g key={area.id}>
            <polyline points={pts} fill="none" stroke={color} strokeWidth="1.8"
              strokeLinecap="round" strokeLinejoin="round" />
            <circle cx={parseFloat(last[0])} cy={parseFloat(last[1])} r="3" fill={color} />
          </g>
        );
      })}
      {/* X axis labels */}
      <text x={pL}      y={H - 4} fontSize="8" fill="#94a3b8">−1h</text>
      <text x={pL + cW} y={H - 4} fontSize="8" fill="#94a3b8" textAnchor="end">Now</text>
    </svg>
  );
}

/* ── Find Seat Banner ────────────────────────── */
function FindSeatBanner({ recommendations }) {
  if (!recommendations || recommendations.length === 0) return null;
  const best = recommendations[0];
  const areaInfo = AREAS.find(a => a.id === best.area_id);
  const name  = areaInfo?.name || best.area_id;
  const count = best.count ?? 0;
  return (
    <div className="find-seat-banner">
      <span className="find-seat-icon">🔍</span>
      <span className="find-seat-text">
        <strong>Find me a seat</strong>
        <span className="find-seat-sub">{name} — only {count} {count === 1 ? 'person' : 'people'} detected</span>
      </span>
      <span className="find-seat-arrow">→</span>
    </div>
  );
}

/* ── Left panel ──────────────────────────────── */
function LeftPanel({ areaData }) {
  const total = Object.values(areaData).reduce((s, d) => s + (d.count ?? 0), 0);
  return (
    <div className="side-panel left-panel">
      <div className="panel-card stat-summary">
        <div className="summary-number">{total}</div>
        <div className="summary-label">People Detected</div>
      </div>
      <div className="panel-card">
        <div className="panel-title">ZONES</div>
        {AREAS.map(area => {
          const info = areaData[area.id] || {};
          const count    = info.count    ?? 0;
          const capacity = info.capacity ?? 20;
          const level    = info.level    || 'low';
          const color    = getColorFromLevel(level);
          const pct      = Math.min(Math.round((count / capacity) * 100), 100);
          return (
            <div key={area.id} className="zone-card">
              <div className="zone-card-top">
                <span className="zone-short-name">{area.shortName}</span>
                <span className="zone-level-tag" style={{ color, borderColor: color + '50', background: color + '18' }}>
                  {capitalizeLevel(level)}
                </span>
              </div>
              <div className="zone-full-name">{area.name}</div>
              <div className="zone-bar-track">
                <div className="zone-bar-fill" style={{ width: `${pct}%`, background: color }} />
              </div>
              <div className="zone-count-row">
                <span className="zone-count" style={{ color }}>{count}</span>
                <span className="zone-cap"> / {capacity} capacity</span>
              </div>
            </div>
          );
        })}
      </div>
      <div className="panel-card">
        <div className="panel-title">OCCUPANCY LEVEL</div>
        {[
          { label: 'LOW',    sub: '< 33% occupied',  grad: 'linear-gradient(90deg,#22c55e,#86efac)' },
          { label: 'MEDIUM', sub: '33–66% occupied',  grad: 'linear-gradient(90deg,#f59e0b,#fcd34d)' },
          { label: 'HIGH',   sub: '> 66% occupied',   grad: 'linear-gradient(90deg,#ef4444,#fca5a5)' },
        ].map(e => (
          <div key={e.label} className="legend-entry">
            <div className="legend-bar" style={{ background: e.grad }} />
            <div className="legend-entry-text">
              <span className="legend-entry-label">{e.label}</span>
              <span className="legend-entry-sub">{e.sub}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Right panel ─────────────────────────────── */
function RightPanel({ areaData, connected, historyData }) {
  const lastUpdated = Math.max(...Object.values(areaData).map(d => d.timestamp ?? 0));
  const lowAreas  = Object.values(areaData).filter(d => d.level === 'low').length;
  const highAreas = Object.values(areaData).filter(d => d.level === 'high').length;
  return (
    <div className="side-panel right-panel">
      <div className="panel-card">
        <div className="panel-title">QUICK STATS</div>
        {[
          { label: 'Areas Monitored', value: AREAS.length, color: null },
          { label: 'Available',  value: lowAreas,  color: '#22c55e' },
          { label: 'Crowded',    value: highAreas, color: highAreas > 0 ? '#ef4444' : '#22c55e' },
        ].map(s => (
          <div key={s.label} className="stat-row-item">
            <span className="stat-row-label">{s.label}</span>
            <span className="stat-row-value" style={s.color ? { color: s.color } : {}}>{s.value}</span>
          </div>
        ))}
      </div>

      <div className="panel-card">
        <div className="panel-title">OCCUPANCY HISTORY</div>
        <OccupancyChart historyData={historyData} areaData={areaData} />
        <div className="chart-legend-row">
          {AREAS.map(area => {
            const color = getColorFromLevel((areaData[area.id] || {}).level || 'low');
            return (
              <span key={area.id} className="chart-legend-item">
                <span className="chart-legend-dot" style={{ background: color }} />
                {area.shortName}
              </span>
            );
          })}
        </div>
      </div>

      <div className="panel-card">
        <div className="panel-title">SPACE DENSITY</div>
        <div className="density-subtitle">People per unit area · cross-zone comparison</div>
        {AREAS.map(area => {
          const count = (areaData[area.id] || {}).count ?? 0;
          const { pct, level } = getDensityInfo(count, area.id);
          const color = getColorFromLevel(level);
          const tag   = level === 'low' ? 'Low' : level === 'medium' ? 'Med' : 'High';
          return (
            <div key={area.id} className="density-row">
              <span className="density-zone">{area.shortName}</span>
              <div className="density-bar-track">
                <div className="density-bar-fill" style={{ width: `${pct}%`, background: color }} />
              </div>
              <span className="density-tag" style={{
                color, border: `1px solid ${color}55`, background: `${color}18`
              }}>{tag}</span>
            </div>
          );
        })}
      </div>

      <div className="panel-card">
        <div className="panel-title">SYSTEM STATUS</div>
        <div className="status-item">
          <span className={`status-dot ${connected ? 'online' : 'offline'}`} />
          <span className="status-label">{connected ? 'Live Data Stream' : 'Mock Data Mode'}</span>
        </div>
        <div className="status-item">
          <span className="status-dot online" />
          <span className="status-label">Sensor Network</span>
        </div>
        <div className="status-time">
          Last updated: {lastUpdated ? new Date(lastUpdated * 1000).toLocaleTimeString() : '—'}
        </div>
      </div>
    </div>
  );
}

/* ── App ─────────────────────────────────────── */
function App() {
  const [areaData,       setAreaData]       = useState(MOCK_DATA);
  const [historyData,    setHistoryData]    = useState(initHistory);
  const [recommendations,setRecommendations]= useState(() =>
    Object.entries(MOCK_DATA)
      .map(([id, d]) => ({ area_id: id, count: d.count, capacity: d.capacity, level: d.level }))
      .sort((a, b) => a.count - b.count)
  );
  const [connected,      setConnected]      = useState(false);
  const wsRef = useRef(null);

  const fetchAreas = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/areas`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      // Only apply real data if CV is actually running (at least one area has count > 0)
      const hasRealData = data.some(item => item.count > 0);
      if (!hasRealData) return;
      const mapped = {};
      data.forEach(item => { mapped[item.area_id] = { count: item.count, capacity: item.capacity, level: item.level, timestamp: item.timestamp }; });
      setAreaData(mapped);
    } catch { /* use mock */ }
  }, []);

  // Fetch real history from SQLite via /api/areas/{id}/history, downsample to HISTORY_LEN points
  const fetchHistory = useCallback(async () => {
    try {
      const results = await Promise.all(
        AREAS.map(area =>
          fetch(`${API_BASE}/api/areas/${area.id}/history?hours=1`)
            .then(r => { if (!r.ok) throw new Error(); return r.json(); })
            .then(rows => ({ id: area.id, rows }))
        )
      );
      const next = {};
      results.forEach(({ id, rows }) => {
        if (!rows || rows.length === 0) {
          // No data yet for this area — keep existing history
          return;
        }
        // Downsample: pick HISTORY_LEN evenly-spaced points
        const counts = rows.map(r => r.count);
        if (counts.length <= HISTORY_LEN) {
          next[id] = counts;
        } else {
          const step = (counts.length - 1) / (HISTORY_LEN - 1);
          next[id] = Array.from({ length: HISTORY_LEN }, (_, i) =>
            counts[Math.round(i * step)]
          );
        }
      });
      // Only update if we got at least one real area's data
      if (Object.keys(next).length > 0) {
        setHistoryData(prev => ({ ...prev, ...next }));
      }
    } catch {
      // Backend unavailable — keep seeded mock data as fallback
    }
  }, []);

  const fetchRecommendations = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/recommend`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      // Only use backend data if CV is running (at least one area has count > 0)
      if (!data.length || !data.some(item => item.count > 0)) return;
      setRecommendations(data);
    } catch {
      const fallback = Object.entries(areaData)
        .map(([id, d]) => ({ area_id: id, count: d.count, capacity: d.capacity, level: d.level }))
        .sort((a, b) => a.count - b.count);
      setRecommendations(fallback);
    }
  }, [areaData]);

  useEffect(() => {
    function connectWS() {
      const ws = new WebSocket(`${WS_BASE}/ws/density`);
      ws.onopen  = () => setConnected(true);
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          const hasRealData = msg.areas.some(item => item.count > 0);
          if (!hasRealData) return;
          setAreaData(prev => {
            const updated = { ...prev };
            msg.areas.forEach(item => {
              updated[item.area_id] = { ...updated[item.area_id], count: item.count, level: item.level, timestamp: msg.timestamp };
            });
            return updated;
          });
          // Append new counts to history
          setHistoryData(prev => {
            const next = { ...prev };
            msg.areas.forEach(item => {
              const arr = [...(prev[item.area_id] || []), item.count];
              next[item.area_id] = arr.slice(-HISTORY_LEN);
            });
            return next;
          });
        } catch { /* ignore */ }
      };
      ws.onclose = () => { setConnected(false); setTimeout(connectWS, 3000); };
      ws.onerror = () => ws.close();
      wsRef.current = ws;
    }
    fetchAreas();
    fetchRecommendations();
    fetchHistory();
    connectWS();
    const rec  = setInterval(fetchRecommendations, 30000);
    const hist = setInterval(fetchHistory, 60000);   // refresh history every minute
    return () => { clearInterval(rec); clearInterval(hist); wsRef.current?.close(); };
  }, [fetchAreas, fetchRecommendations, fetchHistory]);

  return (
    <div className="App">
      <header className="app-header">
        <div className="header-left">
          <div className="header-logo">N</div>
          <div className="header-text">
            <h1>Northeastern University - Seattle</h1>
            <p className="subtitle">225 Second Floor · Real-time Occupancy</p>
          </div>
        </div>
        <span className={`connection-badge ${connected ? 'connected' : 'disconnected'}`}>
          {connected ? '((·)) LIVE' : '○ OFFLINE'}
        </span>
      </header>

      <div className="content-wrapper">
        <FindSeatBanner recommendations={recommendations} />

        <div className="dashboard-layout">
          <LeftPanel areaData={areaData} />

          <div className="map-wrapper">
            <div className="map-label">
              <span className="map-label-title">Floor Plan — Level 2</span>
              <span className="map-label-hint">Click a highlighted zone for details</span>
            </div>
            {/* map-canvas uses aspect-ratio to constrain width to map image */}
            <div className="map-canvas">
              <MapContainer
                crs={L.CRS.Simple}
                bounds={MAP_BOUNDS}
                maxBounds={MAP_MAX_BOUNDS}
                maxBoundsViscosity={0.85}
                style={{ background: MAP_BG }}
                zoomSnap={0.25}
                minZoom={-1}
                maxZoom={2}
                attributionControl={false}
              >
                <FitBounds />
                <ImageOverlay url="/assets/floor_map.png" bounds={MAP_BOUNDS} />
                {AREAS.map(area => {
                  const info  = areaData[area.id] || {};
                  const count = info.count ?? 0;
                  const level = info.level || 'low';
                  const color = getColorFromLevel(level);
                  return (
                    <Polygon
                      key={area.id}
                      positions={area.polygon}
                      pathOptions={{ color, fillColor: color, fillOpacity: 0.28, weight: 2 }}
                      eventHandlers={{
                        mouseover: e => e.target.setStyle({ fillOpacity: 0.5 }),
                        mouseout:  e => e.target.setStyle({ fillOpacity: 0.28 }),
                      }}
                    >
                      <Popup autoPanPaddingTopLeft={[10, 120]} autoPanPaddingBottomRight={[10, 20]}>
                        <div className="popup-content">
                          <div className="popup-short">{area.shortName}</div>
                          <h3>{area.name}</h3>
                          <div className="popup-count" style={{ color }}>
                            {count}
                            {info.capacity && <span className="popup-capacity"> / {info.capacity}</span>}
                          </div>
                          <div className="popup-count-sub">{count === 1 ? 'person' : 'people'} detected</div>
                          <div className="popup-label" style={{ background: color }}>{capitalizeLevel(level)}</div>
                          <div className="popup-time">{new Date((info.timestamp ?? 0) * 1000).toLocaleTimeString()}</div>
                        </div>
                      </Popup>
                    </Polygon>
                  );
                })}
              </MapContainer>
            </div>
          </div>

          <RightPanel areaData={areaData} connected={connected} historyData={historyData} />
        </div>
      </div>
    </div>
  );
}

export default App;
