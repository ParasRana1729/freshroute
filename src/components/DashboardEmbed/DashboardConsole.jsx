import React, { useState } from 'react';
import { 
  MapPin, Sparkles, Clock, BarChart3, Cpu, PlusCircle,
  Flame, Truck, AlertTriangle, Users, RotateCcw, SunMedium,
  Activity, ShieldCheck, Zap, Radio, Search
} from 'lucide-react';
import { OperationsMap } from '../Map/OperationsMap';
import { SmartMatchQueue } from '../Matching/SmartMatchQueue';
import { PerishabilityMatrix } from '../RiskEngine/PerishabilityMatrix';
import { DemandForecast } from '../Forecast/DemandForecast';
import { ModelTelemetry } from '../Architecture/ModelTelemetry';

export function DashboardConsole({
  weather, donors, hubs, recipients, fleet, matches, categories,
  districts, endpoints, stats, activeScenario,
  onSelectScenario, onResetScenario, onDispatchMatch, onLogSurplus
}) {
  const [activeTab, setActiveTab] = useState('map');
  const pendingCount = matches.filter(m => m.status === 'Pending Dispatch').length;

  const scenarioDescriptions = {
    baseline: 'Normal cold-chain operations. Routine scheduled sweeping across 4 metro hubs.',
    heatwave: '⚠️ Heatwave Alert (94°F): Ambient decay multiplier elevated to x1.62. Accelerated Reefer Sprinter routes prioritized.',
    flash_surplus: '⚡ Flash Surplus Ingested: +1,200 lbs Chilled Greek Yogurt allocated to South Harbor Shelter (99.1% score).',
    shelter_surge: '👥 Shelter Demand Surge: Hope Center Pantry urgency spiked to 99/100. AI redistributed priority allocation.',
    traffic_reroute: '🛑 Fleet Traffic Bypass: Reefer Sprinter 01 auto-rerouted via 4th Ave S bypass to preserve cold-chain integrity.'
  };

  return (
    <section id="console" className="console-section">
      <div className="container">
        <div className="console-intro">
          <div className="section-kicker">Interactive Evaluation Environment</div>
          <h2>Autonomous Operations Console</h2>
          <p>Explore the real-time redistribution engine. Trigger environmental disruptors, evaluate Arrhenius thermal decay curves, and inspect sub-second dispatch decisions.</p>
        </div>

        <div className="console-frame">
          {/* Top Operational Status Header */}
          <div className="console-titlebar">
            <div className="titlebar-left">
              <div className="titlebar-dots">
                <span className="titlebar-dot r" />
                <span className="titlebar-dot y" />
                <span className="titlebar-dot g" />
              </div>
              <div className="titlebar-path">freshroute.ops / live-telemetry</div>
            </div>

            <div className="titlebar-chips">
              <div className="t-chip live">
                <span className="live-pulse" />
                Engine Active · 24ms
              </div>
              <div className="t-chip">
                <Radio size={12} color="#38BDF8" />
                IoT Reefer Fleet: 4/4 Synced
              </div>
              <div className="t-chip">
                <SunMedium size={12} color="#F59E0B" />
                {weather.tempF}°F Ambient (x{weather.perishabilityMultiplier} Decay)
              </div>
            </div>
          </div>

          {/* Scenario Simulation Control Strip */}
          <div className="sim-bar">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="sim-bar-label">Simulate Disruption:</span>
              <div className="sim-btns">
                <button
                  className={`sbtn ${activeScenario === 'heatwave' ? 'on-warn' : ''}`}
                  onClick={() => onSelectScenario('heatwave')}
                  title="Spikes ambient temperature to 94°F and accelerates perishability clock"
                >
                  <Flame size={12} /> Heatwave (+10°F)
                </button>
                <button
                  className={`sbtn ${activeScenario === 'flash_surplus' ? 'on' : ''}`}
                  onClick={() => onSelectScenario('flash_surplus')}
                  title="Injects 1,200 lbs sudden dairy donation from supermarket"
                >
                  <Truck size={12} /> Flash Surplus (+1.2k lbs)
                </button>
                <button
                  className={`sbtn ${activeScenario === 'shelter_surge' ? 'on' : ''}`}
                  onClick={() => onSelectScenario('shelter_surge')}
                  title="Simulates sudden 99/100 urgency surge at Hope Center Pantry"
                >
                  <Users size={12} /> Shelter Demand Surge
                </button>
                <button
                  className={`sbtn ${activeScenario === 'traffic_reroute' ? 'on' : ''}`}
                  onClick={() => onSelectScenario('traffic_reroute')}
                  title="Simulates highway traffic bottleneck and dynamic waypoint bypass"
                >
                  <AlertTriangle size={12} /> Highway Reroute
                </button>
                {activeScenario !== 'baseline' && (
                  <button className="sbtn" onClick={onResetScenario} style={{ color: '#E2E8F0', borderColor: '#475569' }}>
                    <RotateCcw size={11} /> Reset Baseline
                  </button>
                )}
              </div>
            </div>

            {activeScenario !== 'baseline' && (
              <div style={{ fontSize: '11px', color: '#CBD5E1', background: 'rgba(255,255,255,0.05)', padding: '3px 10px', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.1)' }}>
                {scenarioDescriptions[activeScenario]}
              </div>
            )}
          </div>

          {/* Main Console Body */}
          <div className="console-body">
            {/* Interactive KPI Summary Cards - Clicking switches tabs */}
            <div className="kpi-strip">
              <div className="kpi" onClick={() => setActiveTab('matching')} style={{ cursor: 'pointer' }} title="Click to view Match Queue">
                <div className="kpi-label">Rescued Today</div>
                <div>
                  <span className="kpi-val">{stats.rescuedLbs.toLocaleString()}</span>
                  <span className="kpi-unit">lbs</span>
                </div>
                <div className="kpi-delta">+{stats.rescuedChangePct}% · ~{Math.round(stats.rescuedLbs * 0.83).toLocaleString()} meals</div>
              </div>

              <div className="kpi" onClick={() => setActiveTab('perishability')} style={{ cursor: 'pointer' }} title="Click to view Thermal Decay Matrix">
                <div className="kpi-label">Spoilage Prevention</div>
                <div>
                  <span className="kpi-val">{stats.spoilagePreventionRate}%</span>
                </div>
                <div className="kpi-delta" style={{ color: '#F59E0B' }}>+25.4% over manual coordination</div>
              </div>

              <div className="kpi" onClick={() => setActiveTab('map')} style={{ cursor: 'pointer' }} title="Click to view Live Dispatch Map">
                <div className="kpi-label">Active Cold Fleet</div>
                <div>
                  <span className="kpi-val">{stats.activeVans}</span>
                  <span className="kpi-unit">vans</span>
                </div>
                <div className="kpi-delta" style={{ color: '#38BDF8' }}>100% Reefer Telemetry Compliant</div>
              </div>

              <div className="kpi" onClick={() => setActiveTab('architecture')} style={{ cursor: 'pointer' }} title="Click to inspect ML Model Telemetry">
                <div className="kpi-label">Pareto ML Latency</div>
                <div>
                  <span className="kpi-val">{stats.aiLatencyMs}</span>
                  <span className="kpi-unit">ms</span>
                </div>
                <div className="kpi-delta">Multi-attribute MILP solver</div>
              </div>
            </div>

            {/* Navigation Tabs Bar */}
            <div className="console-tabs">
              <div className="console-tabs-list">
                <button
                  className={`ctab ${activeTab === 'map' ? 'active' : ''}`}
                  onClick={() => setActiveTab('map')}
                >
                  <MapPin size={14} /> Live Dispatch Map
                </button>
                <button
                  className={`ctab ${activeTab === 'matching' ? 'active' : ''}`}
                  onClick={() => setActiveTab('matching')}
                >
                  <Sparkles size={14} /> Smart Match Queue
                  {pendingCount > 0 && <span className="ctab-badge">{pendingCount}</span>}
                </button>
                <button
                  className={`ctab ${activeTab === 'perishability' ? 'active' : ''}`}
                  onClick={() => setActiveTab('perishability')}
                >
                  <Clock size={14} /> Perishability Simulator
                </button>
                <button
                  className={`ctab ${activeTab === 'forecast' ? 'active' : ''}`}
                  onClick={() => setActiveTab('forecast')}
                >
                  <BarChart3 size={14} /> District Forecast
                </button>
                <button
                  className={`ctab ${activeTab === 'architecture' ? 'active' : ''}`}
                  onClick={() => setActiveTab('architecture')}
                >
                  <Cpu size={14} /> REST API Sandbox
                </button>
              </div>

              <button
                className="btn btn-sm btn-ghost"
                style={{ background: '#151F32', color: '#E2E8F0', borderColor: '#1E293B' }}
                onClick={onLogSurplus}
              >
                <PlusCircle size={13} /> Log Surplus Batch
              </button>
            </div>

            {/* Tab Panes */}
            {activeTab === 'map' && (
              <OperationsMap
                donors={donors}
                hubs={hubs}
                recipients={recipients}
                fleet={fleet}
              />
            )}

            {activeTab === 'matching' && (
              <SmartMatchQueue
                matches={matches}
                onDispatchMatch={onDispatchMatch}
                onLogSurplus={onLogSurplus}
              />
            )}

            {activeTab === 'perishability' && (
              <PerishabilityMatrix
                weather={weather}
                categories={categories}
                onSimulateHeatwave={() => onSelectScenario(activeScenario === 'heatwave' ? 'baseline' : 'heatwave')}
              />
            )}

            {activeTab === 'forecast' && (
              <DemandForecast
                districts={districts}
              />
            )}

            {activeTab === 'architecture' && (
              <ModelTelemetry
                endpoints={endpoints}
              />
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
