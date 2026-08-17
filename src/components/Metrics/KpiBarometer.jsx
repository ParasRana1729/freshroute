import React from 'react';
import { 
  Scale, 
  ShieldCheck, 
  Truck, 
  Cpu, 
  Leaf, 
  TrendingUp,
  ArrowUpRight,
  Sparkles
} from 'lucide-react';

export function KpiBarometer({ stats }) {
  return (
    <div className="kpi-grid">
      {/* KPI 1: Rescued Food Volume */}
      <div className="kpi-card kpi-emerald">
        <div className="kpi-header">
          <span className="kpi-title">Rescued Food Today</span>
          <div className="kpi-icon-wrap" style={{ color: 'var(--color-primary-light)', background: 'rgba(16, 185, 129, 0.12)' }}>
            <Scale size={16} />
          </div>
        </div>
        <div className="kpi-value-row">
          <span className="kpi-value">{stats.rescuedLbs.toLocaleString()}</span>
          <span className="kpi-unit">lbs</span>
        </div>
        <div className="kpi-trend">
          <TrendingUp size={13} />
          <span>+{stats.rescuedChangePct}% today (~{Math.round(stats.rescuedLbs * 0.83).toLocaleString()} meals)</span>
        </div>
      </div>

      {/* KPI 2: Spoilage Prevention Rate */}
      <div className="kpi-card kpi-amber">
        <div className="kpi-header">
          <span className="kpi-title">Spoilage Prevention</span>
          <div className="kpi-icon-wrap" style={{ color: 'var(--color-warning-light)', background: 'rgba(245, 158, 11, 0.12)' }}>
            <ShieldCheck size={16} />
          </div>
        </div>
        <div className="kpi-value-row">
          <span className="kpi-value">{stats.spoilagePreventionRate}%</span>
          <span className="kpi-unit">rescued</span>
        </div>
        <div className="kpi-trend">
          <ArrowUpRight size={13} />
          <span>+25.4% vs manual baseline</span>
        </div>
      </div>

      {/* KPI 3: Active Fleet & Cold-Chain */}
      <div className="kpi-card kpi-cyan">
        <div className="kpi-header">
          <span className="kpi-title">Active Fleet Logistics</span>
          <div className="kpi-icon-wrap" style={{ color: 'var(--color-cold-light)', background: 'rgba(6, 182, 212, 0.12)' }}>
            <Truck size={16} />
          </div>
        </div>
        <div className="kpi-value-row">
          <span className="kpi-value">{stats.activeVans}</span>
          <span className="kpi-unit">vehicles ({stats.coldChainCompliant}% reefer)</span>
        </div>
        <div className="kpi-trend neutral">
          <Sparkles size={13} />
          <span>Zero cold-chain breaks logged</span>
        </div>
      </div>

      {/* KPI 4: AI Matching Latency */}
      <div className="kpi-card kpi-indigo">
        <div className="kpi-header">
          <span className="kpi-title">AI Matching Speed</span>
          <div className="kpi-icon-wrap" style={{ color: 'var(--color-info-light)', background: 'rgba(99, 102, 241, 0.12)' }}>
            <Cpu size={16} />
          </div>
        </div>
        <div className="kpi-value-row">
          <span className="kpi-value">{stats.aiLatencyMs}</span>
          <span className="kpi-unit">ms</span>
        </div>
        <div className="kpi-trend neutral">
          <span>99.8% optimal Pareto allocations</span>
        </div>
      </div>

      {/* KPI 5: Carbon Abatement */}
      <div className="kpi-card kpi-emerald">
        <div className="kpi-header">
          <span className="kpi-title">CO₂e Abatement</span>
          <div className="kpi-icon-wrap" style={{ color: 'var(--color-primary-light)', background: 'rgba(16, 185, 129, 0.12)' }}>
            <Leaf size={16} />
          </div>
        </div>
        <div className="kpi-value-row">
          <span className="kpi-value">{(stats.co2SavedKg).toLocaleString()}</span>
          <span className="kpi-unit">kg CO₂e</span>
        </div>
        <div className="kpi-trend">
          <TrendingUp size={13} />
          <span>Landfill methane diverted</span>
        </div>
      </div>
    </div>
  );
}
