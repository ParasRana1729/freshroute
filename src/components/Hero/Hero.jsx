import React from 'react';
import { ArrowRight, Calendar } from 'lucide-react';

export function Hero({ onRequestDemo, onExploreConsole }) {
  return (
    <section className="hero">
      <div className="container">
        <div className="hero-grid">
          <div>
            <div className="hero-tag">
              <span className="hero-tag-dot" />
              Dynamic Cold-Chain Redistribution
            </div>

            <h1>
              Rescue perishable food <em>before</em> it spoils.
            </h1>

            <p className="hero-sub">
              FreshRoute synthesizes real-time NOAA weather telemetry, Arrhenius decay kinetics, and neighborhood hunger demand to route surplus groceries directly to pantries in under 95 milliseconds.
            </p>

            <div className="hero-actions">
              <button className="btn btn-primary btn-lg" onClick={onRequestDemo}>
                <Calendar size={16} />
                Schedule Private Demo
              </button>
              <button className="btn btn-ghost btn-lg" onClick={onExploreConsole}>
                Launch Operations App
                <ArrowRight size={16} />
              </button>
            </div>

            <div className="hero-telemetry-row">
              <div>
                <div className="hero-metric-val">96.4<span>%</span></div>
                <div className="hero-metric-label">Spoilage Prevention</div>
              </div>
              <div>
                <div className="hero-metric-val">&lt;95<span>ms</span></div>
                <div className="hero-metric-label">Match Allocation</div>
              </div>
              <div>
                <div className="hero-metric-val">100<span>%</span></div>
                <div className="hero-metric-label">Cold-Chain Compliance</div>
              </div>
              <div>
                <div className="hero-metric-val">250k<span>+</span></div>
                <div className="hero-metric-label">Lbs Saved / Mo</div>
              </div>
            </div>
          </div>

          <div className="hero-visual-card" onClick={onExploreConsole} style={{ cursor: 'pointer' }} title="Click to launch Operations Console">
            <img src="/hero-bg.jpg" alt="FreshRoute Fleet Redistribution Grid" />
            <div className="hero-visual-overlay">
              <div>
                <div style={{ fontSize: '13px', fontWeight: '700', letterSpacing: '-0.01em' }}>Metro Dispatch Active</div>
                <div style={{ fontSize: '11.5px', color: '#CBD5E1' }}>4 Reefer Sprinters En Route</div>
              </div>
              <div className="hero-overlay-tag">
                LAUNCH CONSOLE ↗
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
