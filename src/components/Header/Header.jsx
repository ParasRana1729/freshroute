import React from 'react';
import { 
  Zap, 
  SunMedium, 
  ThermometerSnowflake, 
  PlusCircle, 
  CalendarCheck, 
  ShieldCheck,
  TrendingUp
} from 'lucide-react';

export function Header({ 
  weather, 
  onRequestDemo, 
  onLogSurplus, 
  onSimulateScenario,
  activeScenario 
}) {
  return (
    <header className="top-header">
      {/* Brand Identity */}
      <div className="brand-section">
        <div className="brand-logo-wrap">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="28" height="28" fill="none">
            <path d="M12 24C12 17.3726 17.3726 12 24 12C30.6274 12 36 17.3726 36 24C36 30.6274 30.6274 36 24 36C17.3726 36 12 24Z" stroke="#34D399" strokeWidth="2.5" strokeDasharray="4 2"/>
            <path d="M16 26C18 20 22 17 28 16C28 22 25 26 19 28" fill="#10B981" stroke="#A7F3D0" strokeWidth="1.5" strokeLinejoin="round"/>
            <path d="M20 25L24 29L32 19" stroke="#FFFFFF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <div className="brand-text-wrap">
          <div className="brand-name">
            FreshRoute
            <span className="brand-tag">AI Operations</span>
          </div>
          <span className="brand-subtitle">
            Smart Cold-Chain & Perishability Redistribution Platform
          </span>
        </div>
      </div>

      {/* Operational Telemetry Indicators */}
      <div className="header-telemetry-group">
        <div className="telemetry-pill live-status" title="Real-time Dispatch Engine Online">
          <div className="status-dot"></div>
          <span>Engine Online</span>
          <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>| v4.2-opt</span>
        </div>

        <div className="telemetry-pill weather-alert" title="Live Ambient Weather & Decay Factor">
          <SunMedium size={15} color="#F59E0B" />
          <span>{weather.tempF}°F Ambient</span>
          <span style={{ fontSize: '11px', opacity: 0.85 }}>({weather.humidity}% Hum)</span>
          <span style={{ 
            background: 'rgba(245, 158, 11, 0.25)', 
            padding: '1px 5px', 
            borderRadius: '4px',
            fontSize: '10.5px',
            fontWeight: '700' 
          }}>
            Decay x{weather.perishabilityMultiplier}
          </span>
        </div>

        <div className="telemetry-pill" style={{ borderColor: 'rgba(6, 182, 212, 0.3)', background: 'rgba(6, 182, 212, 0.08)', color: '#CFFAFE' }}>
          <ThermometerSnowflake size={15} color="#06B6D4" />
          <span>Cold-Chain Fleet: 100% Compliant</span>
        </div>
      </div>

      {/* Actions & Demo CTA */}
      <div className="header-actions">
        <button 
          className="btn btn-secondary" 
          onClick={onLogSurplus}
          title="Add a new surplus donation batch into the matching queue"
        >
          <PlusCircle size={15} color="var(--color-primary-light)" />
          Log Surplus
        </button>

        <button 
          className="btn btn-primary" 
          onClick={onRequestDemo}
          title="Schedule an interactive live demonstration with ROI calculator"
        >
          <CalendarCheck size={16} />
          Request a Demo
        </button>
      </div>
    </header>
  );
}
