import React, { useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import L from 'leaflet';
import { 
  Truck, Thermometer, Clock, Layers, Navigation, ShieldCheck, 
  BatteryCharging, AlertCircle, CheckCircle2, ChevronRight, Fuel, MapPin,
  CircleDot, Gauge
} from 'lucide-react';

const createMapMarkerIcon = (type) => {
  const configs = {
    donor: { bg: '#059669', border: '#10B981', letter: 'D', title: 'Food Donor' },
    hub: { bg: '#0284C7', border: '#38BDF8', letter: 'H', title: 'Central Hub' },
    recipient: { bg: '#4F46E5', border: '#818CF8', letter: 'L', title: 'Langar / Kitchen' },
    vehicle: { bg: '#D97706', border: '#FBBF24', letter: 'V', title: 'Reefer Truck' },
  }[type] || { bg: '#059669', border: '#10B981', letter: '•' };

  return L.divIcon({
    className: 'custom-map-pin',
    html: `<div style="background:${configs.bg};border:2px solid #FFFFFF;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-family:var(--font-mono, monospace);font-weight:800;font-size:11px;color:#FFFFFF;box-shadow:0 3px 10px rgba(0,0,0,0.22);">${configs.letter}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -16],
  });
};

export function OperationsMap({ donors, hubs, recipients, fleet }) {
  const [filter, setFilter] = useState('all');
  const [selectedVehicle, setSelectedVehicle] = useState(fleet[0]?.id || null);

  // Real Punjab Highway Routes (NH44 GT Road & Regional Connectors)
  const punjabRoutes = [
    // Route 1: Ludhiana Verka Dairy to Dhandari Industrial Kitchen
    { 
      id: 1, 
      pts: [[30.9325, 75.8350], [30.9010, 75.8573], [30.8750, 75.8850]], 
      color: '#059669', 
      dash: '6,6',
      name: 'Verka Ludhiana -> Dhandari Slum Corridor'
    },
    // Route 2: Jalandhar Cold Depot to Golden Temple Langar Amritsar via NH44
    { 
      id: 2, 
      pts: [[31.3320, 75.5840], [31.4200, 75.3800], [31.5200, 75.2500], [31.6200, 74.8765]], 
      color: '#0284C7', 
      dash: '4,4',
      name: 'NH44 GT Road: Jalandhar -> Amritsar Langar'
    },
    // Route 3: Khanna Grain Silos to Patiala Welfare Kitchen
    { 
      id: 3, 
      pts: [[30.6350, 76.2200], [30.5200, 76.3200], [30.3400, 76.3900]], 
      color: '#D97706', 
      dash: '3,4',
      name: 'Sirhind Bypass: Khanna -> Patiala Sanstha'
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', position: 'relative' }}>
      {/* Sleek Top Layer Control Bar */}
      <div style={{ background: '#FFFFFF', borderBottom: '1px solid #E2E8F0', padding: '10px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', zIndex: 10, flexWrap: 'wrap', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '12.5px', color: '#475569', fontWeight: 550 }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, color: '#0F172A', fontWeight: 700 }}>
            <MapPin size={14} color="#059669" />
            Punjab State Grid
          </span>
          <span style={{ color: '#CBD5E1' }}>|</span>
          <span>4 Mandis</span>
          <span>· 4 Langars</span>
          <span>· 4 Cold Fleet</span>
        </div>

        {/* Clean Segmented Button Group */}
        <div style={{ display: 'inline-flex', background: '#F1F5F9', padding: '2px', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
          {[
            { id: 'all', label: 'All Units' },
            { id: 'donors', label: 'Dairies & Mandis' },
            { id: 'recipients', label: 'Langars' },
            { id: 'fleet', label: 'Fleet' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setFilter(tab.id)}
              style={{
                padding: '4px 10px',
                fontSize: '11.5px',
                fontWeight: filter === tab.id ? 700 : 550,
                color: filter === tab.id ? '#0F172A' : '#64748B',
                background: filter === tab.id ? '#FFFFFF' : 'transparent',
                border: 'none',
                borderRadius: '4px',
                boxShadow: filter === tab.id ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
                cursor: 'pointer',
                transition: 'all 120ms ease'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Map Viewport Container */}
      <div style={{ flex: 1, minHeight: 0, position: 'relative', width: '100%' }}>
        <MapContainer
          center={[30.9500, 75.7000]} // Perfectly centered on central Punjab (Ludhiana / Jalandhar / Amritsar corridor)
          zoom={8}
          scrollWheelZoom={true}
          style={{ width: '100%', height: '100%', background: '#F8FAFC' }}
        >
          {/* Crisp CartoDB Positron Light Tiles */}
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
          />

          {punjabRoutes.map(r => (
            <Polyline key={r.id} positions={r.pts} color={r.color} weight={3.5} dashArray={r.dash} opacity={0.9} />
          ))}

          {hubs.map(h => (
            <Marker key={h.id} position={h.coordinates} icon={createMapMarkerIcon('hub')}>
              <Popup>
                <div style={{ color: '#0F172A', maxWidth: 240, fontFamily: 'var(--font-sans)' }}>
                  <div style={{ fontSize: '10px', textTransform: 'uppercase', color: '#0284C7', fontWeight: 700 }}>Central Logistics Hub</div>
                  <strong style={{ fontSize: '13.5px', display: 'block', margin: '2px 0 4px', color: '#0F172A' }}>{h.name}</strong>
                  <p style={{ fontSize: '11.5px', color: '#475569', margin: '0 0 6px' }}>{h.address}</p>
                  <div style={{ fontSize: '11px', background: '#F1F5F9', padding: '6px 8px', borderRadius: '4px' }}>
                    Cold Storage: <strong>{h.coldStorageUsedPercent}% Used</strong> · {h.currentInventoryLbs.toLocaleString()} lbs
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}

          {(filter === 'all' || filter === 'donors') && donors.map(d => (
            <Marker key={d.id} position={d.coordinates} icon={createMapMarkerIcon('donor')}>
              <Popup>
                <div style={{ color: '#0F172A', maxWidth: 240, fontFamily: 'var(--font-sans)' }}>
                  <span style={{ fontSize: '10px', background: '#ECFDF5', color: '#065F46', padding: '2px 6px', borderRadius: '3px', fontWeight: 700 }}>
                    Donor · {d.category}
                  </span>
                  <strong style={{ fontSize: '13px', display: 'block', margin: '4px 0 2px', color: '#0F172A' }}>{d.name}</strong>
                  <p style={{ fontSize: '11px', color: '#475569', margin: '0 0 6px' }}>{d.address}</p>
                  <div style={{ fontSize: '11px', background: '#F8FAFC', border: '1px solid #E2E8F0', padding: '6px 8px', borderRadius: '4px' }}>
                    Surplus: <strong>{d.activeSurplusLbs.toLocaleString()} lbs</strong><br/>
                    Pickup Window: <strong>{d.pickupWindow}</strong>
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}

          {(filter === 'all' || filter === 'recipients') && recipients.map(r => (
            <Marker key={r.id} position={r.coordinates} icon={createMapMarkerIcon('recipient')}>
              <Popup>
                <div style={{ color: '#0F172A', maxWidth: 240, fontFamily: 'var(--font-sans)' }}>
                  <span style={{ fontSize: '10px', background: '#EEF2FF', color: '#3730A3', padding: '2px 6px', borderRadius: '3px', fontWeight: 700 }}>
                    Urgency Score: {r.urgencyScore}/100
                  </span>
                  <strong style={{ fontSize: '13px', display: 'block', margin: '4px 0 2px', color: '#0F172A' }}>{r.name}</strong>
                  <p style={{ fontSize: '11px', color: '#475569', margin: '0 0 4px' }}>{r.address}</p>
                  <div style={{ fontSize: '11px', color: '#334155', background: '#F8FAFC', padding: '6px 8px', borderRadius: '4px' }}>
                    Daily Meals: <strong>{r.dailyDemandMeals.toLocaleString()}+ meals</strong><br/>
                    Buffer Stock: <strong>~{r.currentStockHours}h remaining</strong>
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}

          {(filter === 'all' || filter === 'fleet') && fleet.map(v => (
            <Marker key={v.id} position={v.currentLocation} icon={createMapMarkerIcon('vehicle')}>
              <Popup>
                <div style={{ color: '#0F172A', maxWidth: 240, fontFamily: 'var(--font-sans)' }}>
                  <span style={{ fontSize: '10px', background: '#FEF3C7', color: '#92400E', padding: '2px 6px', borderRadius: '3px', fontWeight: 700 }}>
                    {v.type}
                  </span>
                  <strong style={{ fontSize: '13px', display: 'block', margin: '4px 0 2px', color: '#0F172A' }}>{v.name}</strong>
                  <div style={{ fontSize: '11px', lineHeight: 1.5, color: '#334155', background: '#F8FAFC', padding: '6px', borderRadius: '4px' }}>
                    Route: <strong>{v.assignedRoute}</strong><br/>
                    Temp: <strong>{v.tempSensorC}°C ({v.tempSensorF}°F)</strong> ({v.tempStatus})<br/>
                    Payload: <strong>{v.currentPayloadLbs}/{v.capacityLbs} lbs</strong> · Driver: <strong>{v.driver}</strong>
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
