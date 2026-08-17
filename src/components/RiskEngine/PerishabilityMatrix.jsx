import React, { useState } from 'react';
import { SunMedium, Droplets, Flame, Clock, Info, ShieldAlert, Sliders, RotateCcw, AlertTriangle } from 'lucide-react';

export function PerishabilityMatrix({ weather, categories, onSimulateHeatwave }) {
  const [sliderTemp, setSliderTemp] = useState(weather.tempF);

  // Dynamic Arrhenius decay factor: k = exp(0.045 * (T - 68))
  const decayMultiplier = Number((Math.exp(0.045 * (sliderTemp - 68))).toFixed(2));

  const getHazardClass = (remHours) => {
    if (remHours <= 6) return { label: 'CRITICAL HAZARD', color: '#EF4444', bg: 'var(--red-tint)', border: 'var(--red-border)' };
    if (remHours <= 14) return { label: 'HIGH SPOILAGE RISK', color: '#F59E0B', bg: 'var(--amber-tint)', border: 'var(--amber-border)' };
    return { label: 'NOMINAL TRANSIT', color: '#10B981', bg: 'var(--brand-tint)', border: 'var(--brand-border)' };
  };

  return (
    <div className="risk-grid">
      {/* Left Panel: Thermal Kinetics Controller */}
      <div className="risk-panel">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '12px', borderBottom: '1px solid var(--console-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '13.5px', fontWeight: 700, color: '#FFFFFF' }}>
            <SunMedium size={16} color="#F59E0B" />
            Arrhenius Thermal Kinetics Engine
          </div>
          <span style={{
            fontSize: '11px',
            background: sliderTemp > 85 ? 'var(--red-tint)' : sliderTemp > 75 ? 'var(--amber-tint)' : 'var(--brand-tint)',
            color: sliderTemp > 85 ? '#FCA5A5' : sliderTemp > 75 ? '#FCD34D' : '#86EFAC',
            padding: '2px 8px',
            borderRadius: 'var(--radius-full)',
            fontWeight: 700,
            border: `1px solid ${sliderTemp > 85 ? 'var(--red-border)' : sliderTemp > 75 ? 'var(--amber-border)' : 'var(--brand-border)'}`,
            fontFamily: 'var(--font-mono)'
          }}>
            {sliderTemp}°F · x{decayMultiplier} Decay
          </span>
        </div>

        {/* Live Interactive Ambient Slider */}
        <div style={{ background: '#0B1019', borderRadius: 'var(--radius-xs)', padding: '14px', border: '1px solid var(--console-border-subtle)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#E2E8F0', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Sliders size={13} color="#38BDF8" />
              Ambient Loading Dock Temperature:
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 700, color: sliderTemp > 80 ? '#F87171' : '#34D399' }}>
              {sliderTemp}°F
            </span>
          </div>

          <input
            type="range"
            min="60"
            max="105"
            step="1"
            value={sliderTemp}
            onChange={e => setSliderTemp(Number(e.target.value))}
            style={{ width: '100%', accentColor: sliderTemp > 85 ? '#EF4444' : '#059669', cursor: 'pointer' }}
          />

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10.5px', color: '#64748B', fontFamily: 'var(--font-mono)' }}>
            <span>60°F (Mild Autumn)</span>
            <span>75°F (Standard Summer)</span>
            <span>95°F+ (Severe Heatwave)</span>
          </div>
        </div>

        {/* Telemetry Cells */}
        <div className="weather-grid">
          <div>
            <div className="wx-cell-label">Ambient Temp</div>
            <div className="wx-cell-val" style={{ color: sliderTemp > 80 ? '#F87171' : '#FFFFFF' }}>
              {sliderTemp}°F
            </div>
            <div style={{ fontSize: '10.5px', color: '#94A3B8', marginTop: '2px' }}>
              {sliderTemp > 75 ? `+${sliderTemp - 70}°F thermal strain` : 'Normal baseline'}
            </div>
          </div>
          <div>
            <div className="wx-cell-label">Relative Humidity</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span className="wx-cell-val">{weather.humidity}%</span>
              <Droplets size={14} color="#38BDF8" />
            </div>
            <div style={{ fontSize: '10.5px', color: '#94A3B8', marginTop: '2px' }}>Condensation vector risk</div>
          </div>
          <div>
            <div className="wx-cell-label">Decay Multiplier</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span className="wx-cell-val" style={{ color: decayMultiplier > 1.3 ? '#F87171' : '#FBBF24' }}>
                x{decayMultiplier}
              </span>
              <Flame size={14} color="#F59E0B" />
            </div>
            <div style={{ fontSize: '10.5px', color: '#94A3B8', marginTop: '2px' }}>
              Decay rate +{Math.round((decayMultiplier - 1) * 100)}%
            </div>
          </div>
        </div>

        <div style={{ background: '#0B1019', borderRadius: 'var(--radius-xs)', padding: '12px 14px', border: '1px solid var(--console-border-subtle)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: '12px', fontWeight: 700, color: '#FFFFFF' }}>
            <Info size={13} color="#38BDF8" /> Real-Time Arrhenius Kinetics Equation
          </div>
          <p style={{ fontSize: '11.5px', color: '#94A3B8', lineHeight: 1.5, margin: 0 }}>
            FreshRoute calculates <code style={{ color: '#7DD3FC', fontFamily: 'var(--font-mono)' }}>k(T) = A · e^(-Ea/RT)</code>. When temperatures exceed 75°F at loading bays, safe shelf-life hours for high-risk proteins and dairy are automatically compressed to ensure zero spoilage.
          </p>
        </div>
      </div>

      {/* Right Panel: Dynamic Category Matrix */}
      <div className="risk-panel">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '12px', borderBottom: '1px solid var(--console-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '13.5px', fontWeight: 700, color: '#FFFFFF' }}>
            <Clock size={16} color="#34D399" />
            Dynamic Category Safe-Transit Matrix
          </div>
          <span style={{ fontSize: '11px', color: '#94A3B8', fontFamily: 'var(--font-mono)' }}>RECALCULATING LIVE</span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="perish-table">
            <thead>
              <tr>
                <th>Category</th>
                <th>Base Life</th>
                <th>Safe Window</th>
                <th>Status Risk</th>
                <th>In-Transit</th>
              </tr>
            </thead>
            <tbody>
              {categories.map((c, i) => {
                // Dynamically compute adjusted shelf hours using decay multiplier
                const dynHours = Math.max(3, Math.round(c.baseShelfLifeHours / decayMultiplier));
                const hazard = getHazardClass(dynHours);
                const pct = Math.min(100, Math.round((dynHours / c.baseShelfLifeHours) * 100));

                return (
                  <tr key={i}>
                    <td>
                      <strong style={{ color: '#FFFFFF', display: 'block' }}>{c.category}</strong>
                      <span style={{ fontSize: '10.5px', color: '#94A3B8' }}>{c.ambientTempSensitivity}</span>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{c.baseShelfLifeHours}h</td>
                    <td>
                      <span className="shelf-meter">
                        <span style={{
                          display: 'block',
                          height: '100%',
                          width: `${pct}%`,
                          background: hazard.color
                        }} />
                      </span>
                      <strong style={{ color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>{dynHours}h</strong>
                    </td>
                    <td>
                      <span style={{
                        fontSize: '9.5px',
                        fontWeight: 700,
                        fontFamily: 'var(--font-mono)',
                        padding: '2px 6px',
                        borderRadius: '3px',
                        background: hazard.bg,
                        color: hazard.color,
                        border: `1px solid ${hazard.border}`
                      }}>
                        {hazard.label}
                      </span>
                    </td>
                    <td>
                      <strong style={{ color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
                        {c.activePoundsInTransit.toLocaleString()}
                      </strong> lbs
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {sliderTemp >= 88 && (
          <div style={{ background: 'var(--red-tint)', border: '1px solid var(--red-border)', borderRadius: 'var(--radius-xs)', padding: '10px 12px', display: 'flex', alignItems: 'center', gap: 8, marginTop: 'auto' }}>
            <AlertTriangle size={15} color="#EF4444" style={{ flexShrink: 0 }} />
            <span style={{ fontSize: '11.5px', color: '#FCA5A5' }}>
              <strong>Extreme Thermal Hazard:</strong> Dairy and prepared food routes compressed under 6 hours. Automatic Reefer van override triggered.
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
