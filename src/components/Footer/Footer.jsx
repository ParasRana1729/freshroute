import React from 'react';
import { Calendar, Heart } from 'lucide-react';

export function Footer({ onRequestDemo }) {
  return (
    <footer className="footer">
      <div className="container">
        <div className="footer-grid">
          <div style={{ maxWidth: 360 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
              <img src="/logo-icon.svg" alt="FreshRoute" style={{ width: 26, height: 26, borderRadius: 6 }} />
              <span style={{ fontFamily: 'var(--font-sans)', fontSize: '17px', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
                FreshRoute
              </span>
            </div>
            <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              The autonomous operating system for cold-chain food bank redistribution. Uniting grocery donors, refrigerated fleets, and community pantries to eradicate preventable food waste.
            </p>
          </div>

          <div className="footer-links">
            <div className="footer-col">
              <span className="footer-col-title">Platform</span>
              <a href="#console">Live Dispatch Console</a>
              <a href="#how-it-works">Arrhenius Model Architecture</a>
              <a href="#impact">ROI & Yield Estimator</a>
              <a href="#comparison">Operational Comparison</a>
            </div>

            <div className="footer-col">
              <span className="footer-col-title">Developer & APIs</span>
              <a href="#console">REST API v1 Telemetry</a>
              <a href="#console">NOAA Weather Microclimate Feeds</a>
              <a href="#console">IoT Ble Reefer Sensor SDK</a>
              <a href="#console">MILP Pareto Optimizer</a>
            </div>

            <div className="footer-col">
              <span className="footer-col-title">Evaluation</span>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: 8 }}>
                Pilot deployments for food banks handling &gt;10,000 lbs/week.
              </p>
              <button className="btn btn-primary btn-sm" onClick={onRequestDemo}>
                <Calendar size={13} /> Request Partner Pilot
              </button>
            </div>
          </div>
        </div>

        <div className="footer-bottom">
          <span>© {new Date().getFullYear()} FreshRoute Operations, Inc. All rights reserved.</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            Engineered for zero-waste cold-chain logistics <Heart size={12} color="var(--brand-700)" />
          </span>
        </div>
      </div>
    </footer>
  );
}
