import React from 'react';
import { X, Check } from 'lucide-react';

export function ComparisonSection() {
  return (
    <section id="comparison" className="section">
      <div className="container">
        <div className="section-head">
          <div className="overline">Operational Paradigm</div>
          <h2>Manual Coordination vs Autonomous Cold-Chain</h2>
          <p>Traditional food banks lose up to 29% of high-value perishable donations to expiration while volunteers scramble over spreadsheets.</p>
        </div>

        <div className="compare-grid">
          <div className="compare-box old">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, paddingBottom: '14px', borderBottom: '1px solid #FECACA' }}>
              <div style={{ width: 26, height: 26, borderRadius: '50%', background: '#FEE2E2', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <X size={16} color="#DC2626" />
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#991B1B', margin: 0, letterSpacing: '-0.01em' }}>
                Manual Phone Trees & Spreadsheets
              </h3>
            </div>

            {[
              { t: 'Multi-Hour Phone Tag:', d: 'Dispatchers spend 3–4 hours calling pantries while dairy sits on ambient loading docks.' },
              { t: 'Blind to Weather Spikes:', d: 'Summer heatwaves cause unmonitored spoilage before trucks arrive.' },
              { t: 'Static Fixed Routes:', d: 'Vans run fixed weekly loops regardless of traffic bottlenecks or actual pantry stock.' },
              { t: 'Inequitable Concentration:', d: 'Well-known central hubs receive surplus, while peripheral hunger zones remain starved.' },
            ].map((item, i) => (
              <div key={i} className="compare-item">
                <div style={{ color: '#DC2626', fontWeight: 'bold', marginTop: '2px', flexShrink: 0 }}>
                  <X size={15} />
                </div>
                <span><strong style={{ color: 'var(--ink-primary)' }}>{item.t}</strong> {item.d}</span>
              </div>
            ))}
          </div>

          <div className="compare-box new">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, paddingBottom: '14px', borderBottom: '1px solid #BBF7D0' }}>
              <div style={{ width: 26, height: 26, borderRadius: '50%', background: '#DCFCE7', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Check size={16} color="#059669" />
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#065F46', margin: 0, letterSpacing: '-0.01em' }}>
                FreshRoute Autonomous Dispatch
              </h3>
            </div>

            {[
              { t: 'Sub-95ms Pareto Allocation:', d: 'Automated manifests instantly pair with highest-need pantries before products degrade.' },
              { t: 'Dynamic Arrhenius Kinetics:', d: 'IoT probes & NOAA feeds auto-accelerate transit urgency during heatwave surges.' },
              { t: 'Traffic-Aware VRPTW Routing:', d: 'Live multi-stop routing re-orders deliveries around urban congestion in real time.' },
              { t: 'Algorithmic Equity Guarantee:', d: 'Mathematical objective constraints ensure balanced nutritional access across all zip codes.' },
            ].map((item, i) => (
              <div key={i} className="compare-item">
                <div style={{ color: '#059669', fontWeight: 'bold', marginTop: '2px', flexShrink: 0 }}>
                  <Check size={15} />
                </div>
                <span><strong style={{ color: 'var(--ink-primary)' }}>{item.t}</strong> {item.d}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
