import React, { useState } from 'react';
import { Calendar, ArrowRight } from 'lucide-react';

export function ImpactCalculatorSection({ onRequestDemoWithVolume }) {
  const [lbs, setLbs] = useState(35000);

  const rescued = Math.round(lbs * 52 * 0.94);
  const meals = Math.round(rescued * 0.83);
  const co2 = Math.round(rescued * 2.5);
  const hours = Math.round((lbs / 1000) * 8.5 * 52);
  const value = Math.round(rescued * 1.85);

  return (
    <section id="impact" className="section">
      <div className="container">
        <div className="section-head">
          <div className="overline">Impact & ROI Model</div>
          <h2>Quantify Your Network's Rescue Yield</h2>
          <p>Estimate the annual food diversion, hunger relief, and operational savings achievable across your regional redistribution radius.</p>
        </div>

        <div className="calc-card">
          <div className="calc-left">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--ink-primary)' }}>Estimated Weekly Surplus:</span>
              <span style={{ fontFamily: 'var(--font-serif)', fontSize: '28px', fontWeight: 400, color: 'var(--green-800)' }}>
                {lbs.toLocaleString()} lbs / wk
              </span>
            </div>

            <input
              type="range"
              min="5000"
              max="150000"
              step="5000"
              value={lbs}
              onChange={e => setLbs(Number(e.target.value))}
              className="calc-slider"
            />

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11.5px', color: 'var(--ink-muted)', fontFamily: 'var(--font-mono)' }}>
              <span>Single Hub (5k)</span>
              <span>Regional Network (75k)</span>
              <span>Metro Grid (150k)</span>
            </div>

            <p style={{ fontSize: '14px', color: 'var(--ink-secondary)', lineHeight: 1.6 }}>
              Benchmarked on pilot food bank deployments: FreshRoute cuts dispatch administrative overhead by 42% while minimizing ambient spoilage during high-risk summer peaks.
            </p>

            <div>
              <button className="btn btn-primary" onClick={() => onRequestDemoWithVolume(lbs)}>
                <Calendar size={15} />
                Schedule Pilot for {lbs.toLocaleString()} lbs/wk
                <ArrowRight size={14} />
              </button>
            </div>
          </div>

          <div className="calc-results">
            <div>
              <div className="calc-stat-num">~{(meals / 1000).toFixed(0)}k</div>
              <div className="calc-stat-label">Meals Provided / Year</div>
            </div>
            <div>
              <div className="calc-stat-num">{(co2 / 1000).toFixed(0)}t</div>
              <div className="calc-stat-label">CO₂e Emissions Diverted</div>
            </div>
            <div>
              <div className="calc-stat-num">{hours.toLocaleString()}h</div>
              <div className="calc-stat-label">Dispatch Hours Saved</div>
            </div>
            <div>
              <div className="calc-stat-num">${(value / 1000).toFixed(0)}k</div>
              <div className="calc-stat-label">Retail Food Value Saved</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
