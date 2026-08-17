import React from 'react';
import { ArrowRight, MapPin, Sparkles, Clock, BarChart3, Radio, ShieldCheck, Terminal } from 'lucide-react';

export function DashboardTeaser({ stats, weather, onLaunchConsole, onRequestDemo }) {
  return (
    <section id="console-teaser" className="section" style={{ background: '#080C14', color: 'white', borderTop: '1px solid #1E293B', borderBottom: '1px solid #1E293B' }}>
      <div className="container">
        <div className="section-head" style={{ marginBottom: '40px' }}>
          <div className="overline" style={{ color: 'var(--brand-400)' }}>Autonomous Logistics Platform</div>
          <h2 style={{ color: '#FFFFFF' }}>The Operations Console</h2>
          <p style={{ color: '#94A3B8' }}>
            Built for food bank directors, cold-chain fleet dispatchers, and grocery rescue networks. Experience real-time Arrhenius decay modeling and Pareto vehicle routing.
          </p>
        </div>

        {/* Teaser Interactive Card */}
        <div className="teaser-frame" onClick={onLaunchConsole}>
          {/* Header Preview Bar */}
          <div className="teaser-topbar">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ display: 'flex', gap: 5 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#EF4444' }} />
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#F59E0B' }} />
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10B981' }} />
              </div>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: '#94A3B8' }}>
                freshroute.ops / autonomous-fleet-dispatch
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: '11px', color: '#34D399', background: 'rgba(5, 150, 105, 0.15)', padding: '2px 8px', borderRadius: '99px' }}>
                <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#34D399' }} />
                Live Telemetry Active
              </div>
            </div>
          </div>

          {/* Teaser Body Preview */}
          <div className="teaser-body">
            <div className="teaser-kpi-row">
              <div className="teaser-kpi">
                <div className="tk-label">Rescued Today</div>
                <div className="tk-val">{stats.rescuedLbs.toLocaleString()} <span>lbs</span></div>
                <div className="tk-delta">+{stats.rescuedChangePct}% vs baseline</div>
              </div>
              <div className="teaser-kpi">
                <div className="tk-label">Spoilage Prevented</div>
                <div className="tk-val">{stats.spoilagePreventionRate}%</div>
                <div className="tk-delta" style={{ color: '#F59E0B' }}>+25.4% efficiency</div>
              </div>
              <div className="teaser-kpi">
                <div className="tk-label">Reefer Vehicles</div>
                <div className="tk-val">{stats.activeVans} <span>active</span></div>
                <div className="tk-delta" style={{ color: '#38BDF8' }}>100% Synced</div>
              </div>
              <div className="teaser-kpi">
                <div className="tk-label">Match Allocation</div>
                <div className="tk-val">{stats.aiLatencyMs} <span>ms</span></div>
                <div className="tk-delta" style={{ color: '#A78BFA' }}>MILP Pareto</div>
              </div>
            </div>

            <div className="teaser-cta-overlay">
              <div className="teaser-cta-box">
                <div style={{ width: 44, height: 44, borderRadius: '50%', background: 'rgba(5, 150, 105, 0.2)', border: '1px solid rgba(52, 211, 153, 0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 12px' }}>
                  <Terminal size={20} color="#34D399" />
                </div>
                <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#FFFFFF', marginBottom: '6px' }}>
                  Launch Dedicated Operations Console
                </h3>
                <p style={{ fontSize: '13px', color: '#CBD5E1', maxWidth: '380px', margin: '0 auto 16px' }}>
                  Interact with real-time GPS fleet maps, Pareto dispatch queues, Arrhenius thermal decay sliders, and REST API telemetry in full screen.
                </p>
                <div style={{ display: 'flex', justifyContent: 'center', gap: 10 }}>
                  <button className="btn btn-primary" onClick={(e) => { e.stopPropagation(); onLaunchConsole(); }}>
                    Open Operations Console <ArrowRight size={14} />
                  </button>
                  <button className="btn btn-ghost" onClick={(e) => { e.stopPropagation(); onRequestDemo(); }} style={{ background: '#151F32', color: '#CBD5E1', borderColor: '#1E293B' }}>
                    Request Demo
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
