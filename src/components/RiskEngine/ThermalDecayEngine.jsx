import React, { useState } from 'react';
import { 
  SunMedium, Droplets, Flame, Clock, Info, ShieldAlert, Sliders, 
  RotateCcw, AlertTriangle, ShieldCheck, Zap, Thermometer, ArrowRight
} from 'lucide-react';

export function ThermalDecayEngine({ weather, categories, onSimulateHeatwave }) {
  // Ambient temperature in Celsius (default from weather or 37°C)
  const [tempC, setTempC] = useState(weather.tempC || 37);
  const [unit, setUnit] = useState('C'); // 'C' | 'F'

  // Temperature conversions
  const currentTempF = Math.round(tempC * 1.8 + 32);
  const displayTemp = unit === 'C' ? `${tempC}°C` : `${currentTempF}°F`;

  // Arrhenius Kinetics Calculation: k(T) = exp(0.048 * (T_c - 20))
  // Baseline is 20°C (decay factor 1.0x). At 37°C, decay factor is ~2.26x. At 45°C, decay factor is ~3.3x.
  const decayMultiplier = Number((Math.exp(0.048 * (tempC - 20))).toFixed(2));

  // Determine thermal hazard status
  const isLooHeatwave = tempC >= 42;
  const isHighHeat = tempC >= 35;

  const getCategoryHazard = (safeHours, baseHours) => {
    const ratio = safeHours / baseHours;
    if (ratio <= 0.35 || safeHours <= 6) {
      return { label: 'CRITICAL HAZARD', color: '#DC2626', bg: '#FEE2E2', border: '#FECACA' };
    }
    if (ratio <= 0.65 || safeHours <= 14) {
      return { label: 'ELEVATED RISK', color: '#D97706', bg: '#FEF3C7', border: '#FDE68A' };
    }
    return { label: 'SAFE TRANSIT', color: '#059669', bg: '#ECFDF5', border: '#A7F3D0' };
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1.3fr', gap: '20px', alignItems: 'start' }}>
      {/* ── LEFT PANEL: LIVE ARRHENIUS THERMAL SCRUBBER ── */}
      <div className="panel-card-clean" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Panel Header with Unit Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '12px', borderBottom: '1px solid #E2E8F0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '14px', fontWeight: 700, color: '#0F172A' }}>
            <SunMedium size={17} color="#D97706" />
            Arrhenius Thermal Kinetics Engine
          </div>

          <div style={{ display: 'inline-flex', background: '#F1F5F9', padding: '2px', borderRadius: '5px', border: '1px solid #E2E8F0' }}>
            <button
              onClick={() => setUnit('C')}
              style={{
                padding: '3px 8px',
                fontSize: '11px',
                fontWeight: unit === 'C' ? 700 : 500,
                background: unit === 'C' ? '#FFFFFF' : 'transparent',
                color: unit === 'C' ? '#0F172A' : '#64748B',
                border: 'none',
                borderRadius: '3px',
                cursor: 'pointer',
                boxShadow: unit === 'C' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none'
              }}
            >
              °C
            </button>
            <button
              onClick={() => setUnit('F')}
              style={{
                padding: '3px 8px',
                fontSize: '11px',
                fontWeight: unit === 'F' ? 700 : 500,
                background: unit === 'F' ? '#FFFFFF' : 'transparent',
                color: unit === 'F' ? '#0F172A' : '#64748B',
                border: 'none',
                borderRadius: '3px',
                cursor: 'pointer',
                boxShadow: unit === 'F' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none'
              }}
            >
              °F
            </button>
          </div>
        </div>

        {/* Interactive Ambient Temperature Slider */}
        <div style={{ background: '#F8FAFC', borderRadius: '8px', padding: '16px', border: '1px solid #E2E8F0', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '13px', fontWeight: 650, color: '#334155', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Thermometer size={15} color="#0284C7" />
              Punjab Ambient Temperature:
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 800, color: isLooHeatwave ? '#DC2626' : isHighHeat ? '#D97706' : '#059669' }}>
              {displayTemp} ({unit === 'C' ? `${currentTempF}°F` : `${tempC}°C`})
            </span>
          </div>

          <input
            type="range"
            min="15"
            max="48"
            step="1"
            value={tempC}
            onChange={e => setTempC(Number(e.target.value))}
            style={{ width: '100%', accentColor: isLooHeatwave ? '#DC2626' : isHighHeat ? '#D97706' : '#059669', cursor: 'pointer', height: '6px' }}
          />

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#64748B', fontFamily: 'var(--font-mono)', fontWeight: 550 }}>
            <span>15°C (Winter / Chilled)</span>
            <span>30°C (Spring)</span>
            <span>48°C (Peak Punjab Loo)</span>
          </div>
        </div>

        {/* Quick Scenario Preset Pills */}
        <div>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', marginBottom: '8px', fontFamily: 'var(--font-mono)' }}>
            Quick Climate Presets
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px' }}>
            {[
              { label: '❄️ Cold 4°C', val: 4 },
              { label: '🌱 Spring 24°C', val: 24 },
              { label: '☀️ Summer 37°C', val: 37 },
              { label: '🔥 Loo 45°C', val: 45 },
            ].map(p => (
              <button
                key={p.val}
                onClick={() => setTempC(p.val)}
                style={{
                  padding: '6px 4px',
                  borderRadius: '5px',
                  border: tempC === p.val ? '1px solid #059669' : '1px solid #E2E8F0',
                  background: tempC === p.val ? '#ECFDF5' : '#FFFFFF',
                  color: tempC === p.val ? '#065F46' : '#334155',
                  fontSize: '11.5px',
                  fontWeight: tempC === p.val ? 700 : 550,
                  cursor: 'pointer',
                  textAlign: 'center',
                  transition: 'all 120ms ease'
                }}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Dynamic Telemetry Metrics Strip */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', background: '#F8FAFC', padding: '14px', borderRadius: '8px', border: '1px solid #E2E8F0' }}>
          <div>
            <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: '#64748B', textTransform: 'uppercase', fontWeight: 650 }}>Ambient Temp</div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: '#0F172A', marginTop: '2px' }}>
              {displayTemp}
            </div>
            <div style={{ fontSize: '11px', color: isLooHeatwave ? '#DC2626' : '#64748B', fontWeight: 550 }}>
              {tempC > 30 ? `+${tempC - 25}°C thermal strain` : 'Optimal ambient'}
            </div>
          </div>

          <div>
            <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: '#64748B', textTransform: 'uppercase', fontWeight: 650 }}>Humidity</div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: '#0F172A', marginTop: '2px', display: 'flex', alignItems: 'center', gap: 4 }}>
              {weather.humidity || 72}%
              <Droplets size={14} color="#0284C7" />
            </div>
            <div style={{ fontSize: '11px', color: '#64748B' }}>Monsoon condensation</div>
          </div>

          <div>
            <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: '#64748B', textTransform: 'uppercase', fontWeight: 650 }}>Decay Multiplier</div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: decayMultiplier > 2.0 ? '#DC2626' : '#D97706', marginTop: '2px', display: 'flex', alignItems: 'center', gap: 4 }}>
              x{decayMultiplier}
              <Flame size={15} color="#D97706" />
            </div>
            <div style={{ fontSize: '11px', color: '#059669', fontWeight: 600 }}>
              +{Math.round((decayMultiplier - 1) * 100)}% bacterial rate
            </div>
          </div>
        </div>

        {/* Scientific Formulation Explainer */}
        <div style={{ background: '#F8FAFC', borderRadius: '6px', padding: '12px 14px', border: '1px solid #E2E8F0', fontSize: '12px', color: '#475569', lineHeight: 1.55 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 700, color: '#0F172A', marginBottom: 3 }}>
            <Info size={14} color="#0284C7" />
            Arrhenius Biochemical Kinetics Equation
          </div>
          FreshRoute dynamically solves <code style={{ background: '#FFFFFF', padding: '1px 5px', borderRadius: 3, border: '1px solid #CBD5E1', color: '#0284C7', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>k(T) = A · e^(-Ea / RT)</code>. Under Punjab summer temperatures exceeding 38°C, milk souring and microbial respiration exponentially surge, automatically compressing route transit deadlines.
        </div>
      </div>

      {/* ── RIGHT PANEL: DYNAMIC SHELF-LIFE DEPLETION TABLE ── */}
      <div className="panel-card-clean" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '12px', borderBottom: '1px solid #E2E8F0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '14px', fontWeight: 700, color: '#0F172A' }}>
            <Clock size={16} color="#059669" />
            Punjab Food Category Safe-Transit Matrix
          </div>
          <span style={{ fontSize: '11px', color: '#059669', fontFamily: 'var(--font-mono)', fontWeight: 750, background: '#ECFDF5', padding: '2px 7px', borderRadius: 4, border: '1px solid #A7F3D0' }}>
            LIVE RECALCULATION
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="table-clean">
            <thead>
              <tr>
                <th>Food Category</th>
                <th>Base Shelf-Life</th>
                <th>Safe Window @ {displayTemp}</th>
                <th>Risk State</th>
                <th>Active Transit</th>
              </tr>
            </thead>
            <tbody>
              {categories.map((c, i) => {
                // Compute dynamic remaining safe hours based on current temperature slider
                const dynHours = Math.max(2, Math.round(c.baseShelfLifeHours / decayMultiplier));
                const hazard = getCategoryHazard(dynHours, c.baseShelfLifeHours);
                const pct = Math.min(100, Math.max(8, Math.round((dynHours / c.baseShelfLifeHours) * 100)));

                return (
                  <tr key={i}>
                    <td>
                      <strong style={{ color: '#0F172A', display: 'block', fontSize: '13px' }}>{c.category}</strong>
                      <span style={{ fontSize: '11px', color: '#64748B' }}>{c.ambientTempSensitivity}</span>
                    </td>

                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#64748B' }}>
                      {c.baseShelfLifeHours} hrs
                    </td>

                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ width: '60px', height: '6px', background: '#E2E8F0', borderRadius: '99px', overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${pct}%`, background: hazard.color, borderRadius: '99px', transition: 'width 200ms ease' }} />
                        </div>
                        <strong style={{ color: '#0F172A', fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
                          {dynHours} hrs
                        </strong>
                      </div>
                    </td>

                    <td>
                      <span style={{
                        fontSize: '10px',
                        fontWeight: 750,
                        fontFamily: 'var(--font-mono)',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        background: hazard.bg,
                        color: hazard.color,
                        border: `1px solid ${hazard.border}`
                      }}>
                        {hazard.label}
                      </span>
                    </td>

                    <td>
                      <strong style={{ color: '#0F172A', fontFamily: 'var(--font-mono)' }}>
                        {c.activePoundsInTransit.toLocaleString()}
                      </strong> <span style={{ fontSize: '11px', color: '#64748B' }}>lbs</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Dynamic Heatwave Hazard Warning Banner */}
        {tempC >= 40 && (
          <div style={{ background: '#FEE2E2', border: '1px solid #FECACA', borderRadius: '8px', padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 10, marginTop: 'auto' }}>
            <AlertTriangle size={18} color="#DC2626" style={{ flexShrink: 0 }} />
            <div style={{ fontSize: '12px', color: '#991B1B', lineHeight: 1.4 }}>
              <strong>Extreme Punjab Loo Alert ({displayTemp}):</strong> Safe transit window for fresh Verka dairy & cooked Langar meals compressed under 6 hours. System automatically forces Tata Ace EV & Ashok Leyland reefer carriers locked to 2°C - 4°C.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
