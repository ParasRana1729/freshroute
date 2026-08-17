import React from 'react';
import { Database, Network, Truck, ArrowUpRight } from 'lucide-react';

export function HowItWorks() {
  return (
    <section id="how-it-works" className="section">
      <div className="container">
        <div className="section-head">
          <div className="overline">System Architecture</div>
          <h2>How FreshRoute Closes the Spoilage Gap</h2>
          <p>An autonomous cold-chain coordination loop connecting commercial food donors, live climate sensors, and community pantries.</p>
        </div>

        <div className="steps-row">
          <div className="step">
            <div className="step-num">01.</div>
            <h3>Surplus Ingestion & Thermal Telemetry</h3>
            <p>Supermarkets, bakeries, and distribution hubs push automated surplus manifests via EDI or mobile app. FreshRoute immediately matches ambient NOAA weather feeds to compute baseline decay rates.</p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: '13px', color: 'var(--green-700)', fontWeight: 600, marginTop: 'auto', paddingTop: '16px' }}>
              <Database size={15} /> Real-time barcode & EDI sync
            </div>
          </div>

          <div className="step">
            <div className="step-num">02.</div>
            <h3>Arrhenius Kinetics & Pareto Allocation</h3>
            <p>The decay engine calculates safe transit horizons across all temperature zones. A multi-objective Pareto solver pairs each pallet with the highest-need pantry based on dietary rules and intake capacity.</p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: '13px', color: 'var(--green-700)', fontWeight: 600, marginTop: 'auto', paddingTop: '16px' }}>
              <Network size={15} /> Sub-95ms MILP matching
            </div>
          </div>

          <div className="step">
            <div className="step-num">03.</div>
            <h3>Refrigerated Fleet Dispatch & Live Rerouting</h3>
            <p>Drivers receive dynamic multi-stop itineraries with cold-chain checkpoints. If traffic delays or ambient temperature spikes threaten shelf-life, routes automatically re-balance mid-transit.</p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: '13px', color: 'var(--green-700)', fontWeight: 600, marginTop: 'auto', paddingTop: '16px' }}>
              <Truck size={15} /> 100% cold-chain compliance
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
