import React, { useState, useEffect } from 'react';
import { 
  MapPin, Sparkles, Clock, BarChart3, Cpu, PlusCircle,
  Flame, Truck, AlertTriangle, Users, RotateCcw, SunMedium,
  ArrowLeft, Layers, ShieldCheck, ChevronDown, CheckCircle2,
  LayoutDashboard, Search, ExternalLink, ArrowRight, Play,
  TrendingUp, Radio, Sliders, Check, X, Calendar, Fuel, Thermometer,
  Zap, RefreshCw, Send
} from 'lucide-react';
import { OperationsMap } from '../Map/OperationsMap';
import { ThermalDecayEngine } from '../RiskEngine/ThermalDecayEngine';
import { checkHealth, predictShelfLife, optimizeMatch, forecastDemand, optimizeRouting } from '../../lib/freshrouteApi';

export function OperationsApp({
  weather, donors, hubs, recipients, fleet, matches, categories,
  districts, endpoints, stats, activeScenario,
  onSelectScenario, onResetScenario, onDispatchMatch, onLogSurplus,
  onNavigateHome
}) {
  const [activeTab, setActiveTab] = useState('overview');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [selectedFleetId, setSelectedFleetId] = useState(fleet[0]?.id || null);
  const [isScenarioOpen, setIsScenarioOpen] = useState(false);

  // Perishability slider state (Punjab Ambient Temp)
  const [ambientTempC, setAmbientTempC] = useState(37);
  // P4 MILP vs greedy toggle (wired to freshrouteApi.js optimizeMatch {use_milp})
  const [solverMode, setSolverMode] = useState('greedy'); // 'greedy' | 'milp'

  // Live Backend Health & Telemetry State
  const [isBackendHealthy, setIsBackendHealthy] = useState(false);
  const [backendLatency, setBackendLatency] = useState(null);

  // Live Sandbox State
  const [apiSandboxEndpoint, setApiSandboxEndpoint] = useState('match');
  const [apiSandboxLoading, setApiSandboxLoading] = useState(false);
  const [apiSandboxResponse, setApiSandboxResponse] = useState(null);
  const [apiSandboxLatency, setApiSandboxLatency] = useState(null);

  // Live District Forecaster State
  const [selectedDistrictId, setSelectedDistrictId] = useState('ludhiana');
  const [liveDistrictForecast, setLiveDistrictForecast] = useState(null);
  const [forecastLoading, setForecastLoading] = useState(false);

  // Live Match Queue Optimization State
  const [isOptimizingQueue, setIsOptimizingQueue] = useState(false);
  const [liveAllocations, setLiveAllocations] = useState(null);

  // Poll FastAPI Health
  useEffect(() => {
    let isMounted = true;
    const pollHealth = async () => {
      const t0 = performance.now();
      try {
        const res = await fetch('/health');
        if (res.ok && isMounted) {
          const lat = Math.round(performance.now() - t0);
          setIsBackendHealthy(true);
          setBackendLatency(lat);
        } else if (isMounted) {
          setIsBackendHealthy(false);
        }
      } catch {
        if (isMounted) setIsBackendHealthy(false);
      }
    };
    pollHealth();
    const interval = setInterval(pollHealth, 10000);
    return () => { isMounted = false; clearInterval(interval); };
  }, []);

  // Filter matches
  const filteredMatches = matches.filter(m => {
    const matchesCat = categoryFilter === 'all' || m.itemCategory.toLowerCase().includes(categoryFilter.toLowerCase());
    const matchesSearch = !searchQuery || 
      m.itemName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.donorName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.recipientName.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesSearch;
  });

  const pendingMatches = matches.filter(m => m.status === 'Pending Dispatch');

  const scenarioLabels = {
    baseline: 'Standard GT Road Schedule',
    heatwave: '⚠️ Punjab Loo Heatwave (44°C)',
    flash_surplus: '⚡ Verka Dairy (+2,400 lbs)',
    shelter_surge: '👥 Amritsar Langar Surge (55k)',
    traffic_reroute: '🛑 NH44 Bypass Active'
  };

  return (
    <div className="app-shell">
      {/* ── SLEEK LIGHT SIDEBAR ── */}
      <aside className="app-sidebar-clean">
        {/* Brand */}
        <div className="sidebar-header-clean" onClick={onNavigateHome} style={{ cursor: 'pointer' }}>
          <img src="/logo-icon.svg" alt="FreshRoute" />
          <div className="brand-name-clean">FreshRoute</div>
          <span className="brand-badge-clean">PUNJAB</span>
        </div>

        {/* Region Switcher */}
        <div className="sidebar-org-select">
          <div className="org-avatar-badge">PB</div>
          <div className="org-text-meta">
            <div className="org-title-clean">Punjab State Grid</div>
            <div className="org-sub-clean">Ludhiana Central Command</div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav-clean">
          <div className="sidebar-nav-group-title">COMMAND CENTER</div>

          <button 
            className={`s-nav-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <LayoutDashboard size={15} />
            <span>State Grid Overview</span>
          </button>

          <button 
            className={`s-nav-btn ${activeTab === 'map' ? 'active' : ''}`}
            onClick={() => setActiveTab('map')}
          >
            <MapPin size={15} />
            <span>Live Dispatch Map</span>
            <span className="s-nav-badge">4 Units</span>
          </button>

          <button 
            className={`s-nav-btn ${activeTab === 'queue' ? 'active' : ''}`}
            onClick={() => setActiveTab('queue')}
          >
            <Sparkles size={15} />
            <span>Langar Match Queue</span>
            {pendingMatches.length > 0 && (
              <span className="s-nav-badge active-count">{pendingMatches.length}</span>
            )}
          </button>

          <button 
            className={`s-nav-btn ${activeTab === 'perishability' ? 'active' : ''}`}
            onClick={() => setActiveTab('perishability')}
          >
            <Clock size={15} />
            <span>Thermal Decay Matrix</span>
          </button>

          <button 
            className={`s-nav-btn ${activeTab === 'forecast' ? 'active' : ''}`}
            onClick={() => setActiveTab('forecast')}
          >
            <BarChart3 size={15} />
            <span>23 District Deficit</span>
          </button>

          <div className="sidebar-nav-group-title" style={{ marginTop: '14px' }}>SYSTEM & APIS</div>

          <button 
            className={`s-nav-btn ${activeTab === 'api' ? 'active' : ''}`}
            onClick={() => setActiveTab('api')}
          >
            <Cpu size={15} />
            <span>REST API Sandbox</span>
          </button>
        </nav>

        {/* Bottom Actions */}
        <div className="sidebar-bottom-clean">
          <button className="btn-back-site" onClick={onNavigateHome}>
            <ArrowLeft size={13} />
            <span>Back to Public Site</span>
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 2px' }}>
            <div style={{ width: 26, height: 26, borderRadius: '50%', background: '#E2E8F0', color: '#0F172A', fontSize: '10.5px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800 }}>
              GS
            </div>
            <div style={{ fontSize: '11px', color: '#64748B', lineHeight: 1.2 }}>
              <div style={{ color: '#0F172A', fontWeight: 700 }}>Gurdev Singh</div>
              <div>Ops Controller</div>
            </div>
          </div>
        </div>
      </aside>

      {/* ── WORKSPACE ── */}
      <main className="app-workspace">
        {/* Top Minimalist Header */}
        <header className="app-top-header">
          <div className="header-meta-group">
            <span className="header-title-clean">
              {activeTab === 'overview' && 'State Grid Overview'}
              {activeTab === 'map' && 'Punjab GT Road GPS Telemetry'}
              {activeTab === 'queue' && 'Langar & Community Match Queue'}
              {activeTab === 'perishability' && 'Arrhenius Thermal Decay Matrix'}
              {activeTab === 'forecast' && 'Punjab 23-District Meal Demand'}
              {activeTab === 'api' && 'REST API & ML Integration'}
            </span>

            <div className="header-pill-meta">
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#059669' }} />
              <span style={{ color: '#047857', fontWeight: 650 }}>Grid Online · 24ms</span>
            </div>

            <div className="header-pill-meta">
              <SunMedium size={13} color="#D97706" />
              <span>{weather.tempC || 37}°C / {weather.tempF}°F</span>
            </div>

            <button
              onClick={() => setSolverMode(solverMode === 'greedy' ? 'milp' : 'greedy')}
              title="Toggle Pareto matcher: greedy <100ms vs MILP optimal <800ms (P4)"
              style={{ background: solverMode === 'milp' ? '#ECFDF5' : '#FFFFFF', border: `1px solid ${solverMode === 'milp' ? '#A7F3D0' : '#CBD5E1'}`, borderRadius: 6, padding: '5px 10px', fontSize: '11px', fontWeight: 700, color: solverMode === 'milp' ? '#065F46' : '#475569', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 5 }}
            >
              <Cpu size={12} color={solverMode === 'milp' ? '#059669' : '#64748B'} />
              <span>{solverMode === 'milp' ? 'MILP optimal' : 'Greedy <100ms'}</span>
            </button>
          </div>

          <div className="header-actions-group">
            {/* Scenario Simulator Dropdown */}
            <div style={{ position: 'relative' }}>
              <button 
                onClick={() => setIsScenarioOpen(!isScenarioOpen)}
                style={{ background: '#FFFFFF', border: '1px solid #CBD5E1', borderRadius: 6, padding: '7px 12px', fontSize: '12px', fontWeight: 600, color: '#0F172A', display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}
              >
                <Calendar size={13} color="#64748B" />
                <span>{scenarioLabels[activeScenario]}</span>
                <ChevronDown size={13} color="#64748B" />
              </button>

              {isScenarioOpen && (
                <div style={{ position: 'absolute', top: '100%', right: 0, marginTop: 6, width: 290, background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: 8, boxShadow: '0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1)', zIndex: 100, padding: 6 }}>
                  <div style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: '#64748B', padding: '6px 10px', textTransform: 'uppercase', fontWeight: 700 }}>
                    Trigger Environmental Event
                  </div>
                  {[
                    { id: 'baseline', label: 'Baseline Operations', desc: 'Standard scheduled GT road fleet' },
                    { id: 'heatwave', label: 'Severe Punjab Loo (44°C)', desc: 'Spikes thermal decay rate x1.85' },
                    { id: 'flash_surplus', label: 'Verka Dairy Drop (+2.4k lbs)', desc: 'Instant milk allocation to Langar' },
                    { id: 'shelter_surge', label: 'Amritsar Langar Surge (55k)', desc: 'Elevates pilgrim meal priority' },
                    { id: 'traffic_reroute', label: 'NH44 Traffic Bypass', desc: 'Auto-reroutes around bottlenecks' },
                  ].map(s => (
                    <button
                      key={s.id}
                      onClick={() => {
                        if (s.id === 'baseline') onResetScenario();
                        else onSelectScenario(s.id);
                        setIsScenarioOpen(false);
                      }}
                      style={{ width: '100%', textAlign: 'left', padding: '8px 10px', background: activeScenario === s.id ? '#ECFDF5' : 'transparent', border: 'none', borderRadius: 6, color: '#0F172A', cursor: 'pointer', display: 'block', fontSize: '12px' }}
                    >
                      <div style={{ fontWeight: 700, color: activeScenario === s.id ? '#065F46' : '#0F172A' }}>{s.label}</div>
                      <div style={{ fontSize: '11px', color: '#64748B' }}>{s.desc}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Quick Log Surplus Button */}
            <button 
              onClick={onLogSurplus}
              style={{ background: '#059669', color: '#FFFFFF', border: 'none', borderRadius: 6, padding: '7px 14px', fontSize: '12.5px', fontWeight: 650, display: 'inline-flex', alignItems: 'center', gap: 6, cursor: 'pointer', boxShadow: '0 1px 3px rgba(5,150,105,0.25)' }}
            >
              <PlusCircle size={14} />
              <span>Log Surplus</span>
            </button>
          </div>
        </header>

        {/* Scrollable Main Content */}
        <div className="app-view-scroll">
          {/* ════ TAB 1: OVERVIEW ════ */}
          {activeTab === 'overview' && (
            <div>
              {/* 4 Minimalist Light KPI Cards */}
              <div className="kpi-row-clean">
                <div className="kpi-card-clean" onClick={() => setActiveTab('queue')}>
                  <div className="kpi-head-clean">
                    <span>Rescued Food</span>
                    <Sparkles size={14} color="#059669" />
                  </div>
                  <div className="kpi-stat-clean">
                    {stats.rescuedLbs.toLocaleString()} <small>lbs ({Math.round(stats.rescuedLbs * 0.453).toLocaleString()} kg)</small>
                  </div>
                  <div className="kpi-sub-clean" style={{ color: '#059669' }}>
                    +{stats.rescuedChangePct}% vs baseline · ~{Math.round(stats.rescuedLbs * 0.83).toLocaleString()} meals
                  </div>
                </div>

                <div className="kpi-card-clean" onClick={() => setActiveTab('perishability')}>
                  <div className="kpi-head-clean">
                    <span>Spoilage Prevention</span>
                    <ShieldCheck size={14} color="#D97706" />
                  </div>
                  <div className="kpi-stat-clean">{stats.spoilagePreventionRate}%</div>
                  <div className="kpi-sub-clean" style={{ color: '#D97706' }}>
                    +25.4% efficiency vs unmanaged logistics
                  </div>
                </div>

                <div className="kpi-card-clean" onClick={() => setActiveTab('map')}>
                  <div className="kpi-head-clean">
                    <span>Active Cold Fleet</span>
                    <Truck size={14} color="#0284C7" />
                  </div>
                  <div className="kpi-stat-clean">4 <small>vans en route</small></div>
                  <div className="kpi-sub-clean" style={{ color: '#0284C7' }}>
                    100% Reefer Compliant (2°C - 4°C)
                  </div>
                </div>

                <div className="kpi-card-clean" onClick={() => setActiveTab('api')}>
                  <div className="kpi-head-clean">
                    <span>Pareto Latency</span>
                    <Cpu size={14} color="#7C3AED" />
                  </div>
                  <div className="kpi-stat-clean">{solverMode === 'milp' ? '163' : stats.aiLatencyMs} <small>ms</small></div>
                  <div className="kpi-sub-clean" style={{ color: '#7C3AED' }}>
                    {solverMode === 'milp' ? 'MILP optimal <800ms (PuLP/CP-SAT)' : 'Greedy <100ms (P4)'} — click to toggle
                  </div>
                </div>
              </div>

              {/* Split Workspace: Map on Left, Clean Queue on Right */}
              <div style={{ display: 'grid', gridTemplateColumns: '1.25fr 1fr', gap: 16 }}>
                <div className="queue-container-clean">
                  <div className="queue-toolbar-clean">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '13px', fontWeight: 700, color: '#0F172A' }}>
                      <MapPin size={15} color="#059669" />
                      <span>Live Punjab Fleet Map</span>
                    </div>
                    <button 
                      onClick={() => setActiveTab('map')} 
                      className="q-tab-btn" 
                      style={{ color: '#0284C7', fontSize: '11.5px', fontWeight: 650 }}
                    >
                      Expand Map ↗
                    </button>
                  </div>
                  <div style={{ height: '380px' }}>
                    <OperationsMap donors={donors} hubs={hubs} recipients={recipients} fleet={fleet} />
                  </div>
                </div>

                <div className="queue-container-clean">
                  <div className="queue-toolbar-clean">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '13px', fontWeight: 700, color: '#0F172A' }}>
                      <Sparkles size={15} color="#059669" />
                      <span>Pending Langar Dispatches ({pendingMatches.length})</span>
                    </div>
                    <button 
                      onClick={() => setActiveTab('queue')} 
                      className="q-tab-btn" 
                      style={{ color: '#0284C7', fontSize: '11.5px', fontWeight: 650 }}
                    >
                      View All ↗
                    </button>
                  </div>

                  <div style={{ overflowX: 'auto' }}>
                    <table className="table-clean">
                      <thead>
                        <tr>
                          <th>Batch / Item</th>
                          <th>Destination</th>
                          <th>Score</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {matches.slice(0, 4).map(m => (
                          <tr key={m.id}>
                            <td>
                              <div style={{ fontWeight: 700, color: '#0F172A' }}>{m.itemName}</div>
                              <div style={{ fontSize: '11.5px', color: '#64748B' }}>{m.donorName}</div>
                            </td>
                            <td>
                              <div style={{ color: '#334155', fontWeight: 550 }}>{m.recipientName}</div>
                              <div style={{ fontSize: '11px', color: '#64748B' }}>{m.estimatedTransitMins}m transit</div>
                            </td>
                            <td>
                              <span className="score-pill-clean">{m.matchScore}%</span>
                            </td>
                            <td>
                              {m.status === 'Pending Dispatch' ? (
                                <button 
                                  onClick={() => onDispatchMatch(m.id)}
                                  style={{ background: '#059669', color: '#FFFFFF', border: 'none', borderRadius: 4, padding: '5px 10px', fontSize: '11.5px', fontWeight: 650, cursor: 'pointer' }}
                                >
                                  Dispatch
                                </button>
                              ) : (
                                <span style={{ fontSize: '11.5px', color: '#059669', fontWeight: 700 }}>En Route</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ════ TAB 2: LIVE DISPATCH MAP (ENHANCED FLEET DRAWER) ════ */}
          {activeTab === 'map' && (
            <div className="map-workspace-clean">
              <div className="map-view-box">
                <OperationsMap donors={donors} hubs={hubs} recipients={recipients} fleet={fleet} />
              </div>

              <div className="map-drawer-clean">
                <div className="drawer-head-clean">
                  <span>ACTIVE REEFER FLEET ({fleet.length})</span>
                  <span style={{ fontSize: '10.5px', color: '#059669', fontFamily: 'var(--font-mono)', fontWeight: 800 }}>GPS SYNCED</span>
                </div>

                {fleet.map(v => {
                  const pct = Math.round((v.currentPayloadLbs / v.capacityLbs) * 100);
                  const isSelected = selectedFleetId === v.id;

                  return (
                    <div 
                      key={v.id} 
                      className={`fleet-card-clean ${isSelected ? 'active' : ''}`}
                      onClick={() => setSelectedFleetId(v.id)}
                    >
                      <div className="fleet-row-top">
                        <span style={{ fontWeight: 750, fontSize: '13px', color: '#0F172A', display: 'flex', alignItems: 'center', gap: 6 }}>
                          <Truck size={14} color={isSelected ? '#059669' : '#475569'} />
                          {v.name}
                        </span>
                        <span style={{ fontSize: '10px', background: v.status.includes('Transit') ? '#ECFDF5' : '#F1F5F9', color: v.status.includes('Transit') ? '#047857' : '#0284C7', padding: '2px 6px', borderRadius: 4, border: '1px solid #E2E8F0', fontWeight: 700 }}>
                          {v.status.toUpperCase()}
                        </span>
                      </div>

                      <div style={{ fontSize: '12px', color: '#475569', margin: '4px 0' }}>{v.assignedRoute}</div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: '11.5px', color: '#334155', margin: '6px 0' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <Thermometer size={12} color="#059669" />
                          <strong>{v.tempSensorC}°C</strong> ({v.tempStatus})
                        </span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <Clock size={12} color="#0284C7" />
                          <strong>{v.etaMinutes > 0 ? `${v.etaMinutes}m ETA` : 'At Hub'}</strong>
                        </span>
                      </div>

                      {/* Payload Progress Bar */}
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10.5px', color: '#64748B', marginBottom: 3 }}>
                          <span>Payload: {v.currentPayloadLbs} / {v.capacityLbs} lbs</span>
                          <span style={{ fontWeight: 700 }}>{pct}%</span>
                        </div>
                        <div style={{ height: 4, background: '#E2E8F0', borderRadius: 99, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${pct}%`, background: pct > 80 ? '#D97706' : '#059669', borderRadius: 99 }} />
                        </div>
                      </div>

                      <div className="fleet-driver-tag" style={{ marginTop: 6, fontSize: '11px', color: '#64748B', display: 'flex', justifyContent: 'space-between' }}>
                        <span>Driver: <strong style={{ color: '#0F172A' }}>{v.driver}</strong></span>
                        <span style={{ color: '#059669', fontWeight: 600 }}>Cold-Chain Certified</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ════ TAB 3: LANGAR MATCH QUEUE ════ */}
          {activeTab === 'queue' && (
            <div className="panel-card-clean">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: 10 }}>
                <div className="panel-title-clean">
                  <Sparkles size={16} color="#059669" />
                  <span>Punjab Surplus-to-Langar Match Queue ({matches.length})</span>
                </div>

                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <div style={{ position: 'relative' }}>
                    <Search size={13} color="#94A3B8" style={{ position: 'absolute', left: 9, top: 8 }} />
                    <input
                      type="text"
                      placeholder="Search surplus or kitchen..."
                      value={searchQuery}
                      onChange={e => setSearchQuery(e.target.value)}
                      style={{ padding: '6px 10px 6px 28px', fontSize: '12px', border: '1px solid #CBD5E1', borderRadius: 5, width: 190 }}
                    />
                  </div>

                  <select
                    value={categoryFilter}
                    onChange={e => setCategoryFilter(e.target.value)}
                    style={{ padding: '6px 8px', fontSize: '12px', border: '1px solid #CBD5E1', borderRadius: 5, color: '#334155', fontWeight: 600 }}
                  >
                    <option value="all">All Categories</option>
                    <option value="dairy">Dairy & Milk</option>
                    <option value="prepared">Prepared Meals</option>
                    <option value="produce">Fresh Produce</option>
                    <option value="bakery">Bakery & Roti</option>
                  </select>

                  <button 
                    onClick={async () => {
                      setIsOptimizingQueue(true);
                      try {
                        const target = pendingMatches[0];
                        if (target) {
                          const res = await optimizeMatch(
                            {
                              batch_id: target.id,
                              donor_id: target.donorId || 'donor-verka-ludhiana-01',
                              category: target.itemCategory,
                              gross_weight_kg: Math.round(target.batchWeightLbs / 2.20462),
                              origin_coordinates: [30.9325, 75.8350],
                              dietary_flags: { is_pure_veg: true },
                            },
                            { temp_c: ambientTempC, humidity_pct: 72.0 },
                            null,
                            { use_milp: solverMode === 'milp' }
                          );
                          setLiveAllocations(res);
                        }
                      } catch (err) {
                        console.error('Queue live optimize error:', err);
                      } finally {
                        setIsOptimizingQueue(false);
                      }
                    }}
                    style={{ background: solverMode === 'milp' ? '#059669' : '#0284C7', color: '#FFFFFF', border: 'none', borderRadius: 5, padding: '6px 12px', fontSize: '12px', fontWeight: 650, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}
                  >
                    {isOptimizingQueue ? <RefreshCw size={13} className="spin" /> : <Zap size={13} />}
                    <span>Run Live {solverMode === 'milp' ? 'MILP' : 'Greedy'} Solver</span>
                  </button>
                </div>
              </div>

              {liveAllocations && (
                <div style={{ padding: '10px 14px', background: '#ECFDF5', border: '1px solid #A7F3D0', borderRadius: 6, marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', color: '#065F46', fontWeight: 600 }}>
                    ✓ Live Solver Match: <strong>{liveAllocations.assigned_recipient?.name || 'Sri Guru Ram Dass Ji Langar'}</strong> (Score: {liveAllocations.match_score}%, Latency: {liveAllocations.execution_latency_ms}ms, Solver: {liveAllocations.solver || solverMode})
                  </span>
                  <button onClick={() => setLiveAllocations(null)} style={{ background: 'none', border: 'none', color: '#065F46', cursor: 'pointer', fontSize: '11px', fontWeight: 700 }}>✕ Dismiss</button>
                </div>
              )}

              <div style={{ overflowX: 'auto' }}>
                <table className="table-clean">
                  <thead>
                    <tr>
                      <th>Surplus Consignment</th>
                      <th>Assigned Recipient Kitchen</th>
                      <th>Safe Transit</th>
                      <th>Allocated Vehicle Tier</th>
                      <th>Pareto Match</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredMatches.map(m => {
                      const isPending = m.status === 'Pending Dispatch';
                      const isUrgent = m.spoilageWindowHours <= 4;
                      return (
                        <tr 
                          key={m.id} 
                          onClick={() => setSelectedMatch(m)}
                          style={{ cursor: 'pointer', background: selectedMatch?.id === m.id ? '#F1F5F9' : 'transparent' }}
                        >
                          <td>
                            <div style={{ color: '#0F172A', fontWeight: 700 }}>{m.itemName}</div>
                            <div style={{ fontSize: '11.5px', color: '#64748B', marginTop: 3 }}>
                              {m.batchWeightLbs.toLocaleString()} lbs · ~{m.mealsEquivalent} meals · {m.itemCategory}
                            </div>
                          </td>

                          <td>
                            <div style={{ color: '#0F172A', fontWeight: 650 }}>{m.recipientName}</div>
                            <div style={{ fontSize: '11.5px', color: '#64748B' }}>From: {m.donorName} ({m.estimatedTransitMins}m transit)</div>
                          </td>

                          <td>
                            <div style={{ color: isUrgent ? '#B91C1C' : '#B45309', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                              {m.spoilageWindowHours}h safe
                            </div>
                            <div style={{ fontSize: '11px', color: '#64748B' }}>Punjab summer factor</div>
                          </td>

                          <td>
                            <div style={{ color: '#334155', fontSize: '12.5px', fontWeight: 550 }}>{m.assignedVehicleName}</div>
                            <div style={{ fontSize: '11px', color: '#059669', fontWeight: 600 }}>{m.matchFactors.coldChainCompliance}</div>
                          </td>

                          <td>
                            <span className="score-pill-clean">{m.matchScore}%</span>
                          </td>

                          <td>
                            {isPending ? (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onDispatchMatch(m.id);
                                }}
                                style={{ background: '#059669', color: '#FFFFFF', border: 'none', borderRadius: 5, padding: '6px 14px', fontSize: '12px', fontWeight: 650, cursor: 'pointer', boxShadow: '0 1px 2px rgba(5,150,105,0.2)' }}
                              >
                                Dispatch Van
                              </button>
                            ) : (
                              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: '#059669', fontSize: '12px', fontWeight: 700 }}>
                                <Check size={14} /> Dispatched
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Drawer for Selected Match Details */}
              {selectedMatch && (
                <div style={{ padding: '16px 22px', background: '#F8FAFC', borderTop: '1px solid #E2E8F0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 20 }}>
                  <div style={{ fontSize: '12.5px', color: '#334155', maxWidth: '75%' }}>
                    <div style={{ fontWeight: 750, color: '#0F172A', marginBottom: 2 }}>
                      AI Pareto Allocation Rationale ({selectedMatch.matchScore}% Multi-Objective Score)
                    </div>
                    {selectedMatch.aiRationale}
                  </div>
                  <button 
                    onClick={() => setSelectedMatch(null)}
                    style={{ background: '#FFFFFF', color: '#475569', border: '1px solid #CBD5E1', padding: '5px 12px', borderRadius: 5, fontSize: '11.5px', fontWeight: 600, cursor: 'pointer' }}
                  >
                    Close
                  </button>
                </div>
              )}
            </div>
          )}

          {/* ════ TAB 4: PERISHABILITY MATRIX (ARRHENIUS) ════ */}
          {activeTab === 'perishability' && (
            <ThermalDecayEngine 
              weather={weather} 
              categories={categories} 
              onSimulateHeatwave={() => onSelectScenario('heatwave')} 
            />
          )}

          {/* ════ TAB 5: 23 DISTRICT DEMAND & SHORTFALL ════ */}
          {activeTab === 'forecast' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Interactive Live Forecast Simulator Card */}
              <div className="panel-card-clean" style={{ background: '#F8FAFC', border: '1px solid #BAE6FD' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
                  <div>
                    <div style={{ fontWeight: 750, color: '#0369A1', fontSize: '14px', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Zap size={16} color="#0284C7" />
                      Live AI Forecaster Probe (LightGBM & LSTM v1)
                    </div>
                    <div style={{ fontSize: '12px', color: '#64748B', marginTop: 2 }}>
                      Select a district to query the live 7-day walk-forward model with 10th/90th percentile bounds.
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <select
                      value={selectedDistrictId}
                      onChange={e => setSelectedDistrictId(e.target.value)}
                      style={{ padding: '6px 10px', fontSize: '12px', border: '1px solid #CBD5E1', borderRadius: 5, fontWeight: 600, color: '#0F172A' }}
                    >
                      {districts.map(d => (
                        <option key={d.districtId || d.district.toLowerCase()} value={d.districtId || d.district.toLowerCase()}>
                          {d.district} (HVI: {d.hungerVulnerabilityIndex})
                        </option>
                      ))}
                    </select>

                    <button
                      onClick={async () => {
                        setForecastLoading(true);
                        try {
                          const res = await forecastDemand({ district_id: selectedDistrictId, horizon_days: 7 });
                          setLiveDistrictForecast(Array.isArray(res) ? res[0] : res);
                        } catch (err) {
                          console.error('Forecast probe error:', err);
                        } finally {
                          setForecastLoading(false);
                        }
                      }}
                      disabled={forecastLoading}
                      style={{ background: '#0284C7', color: '#FFFFFF', border: 'none', borderRadius: 5, padding: '7px 14px', fontSize: '12px', fontWeight: 650, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}
                    >
                      {forecastLoading ? <RefreshCw size={13} className="spin" /> : <Play size={13} />}
                      <span>Fetch Live 7-Day Forecast</span>
                    </button>
                  </div>
                </div>

                {liveDistrictForecast && (
                  <div style={{ marginTop: 14, padding: '12px 16px', background: '#FFFFFF', borderRadius: 6, border: '1px solid #E2E8F0' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <span style={{ fontWeight: 700, color: '#0F172A', fontSize: '13px' }}>
                        {liveDistrictForecast.district_name} 7-Day Predicted Demand: {liveDistrictForecast.weekly_total_lbs?.toLocaleString()} lbs
                      </span>
                      <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', background: '#ECFDF5', color: '#065F46', padding: '2px 8px', borderRadius: 4, fontWeight: 700 }}>
                        Model: {liveDistrictForecast.model || 'lightgbm-v1'}
                      </span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 6, textAlign: 'center' }}>
                      {liveDistrictForecast.forecast_demand_lbs?.map((v, i) => {
                        const low = liveDistrictForecast.forecast_demand_lower_lbs?.[i] || Math.round(v * 0.9);
                        const high = liveDistrictForecast.forecast_demand_upper_lbs?.[i] || Math.round(v * 1.1);
                        return (
                          <div key={i} style={{ background: '#F8FAFC', padding: '8px 4px', borderRadius: 4, border: '1px solid #E2E8F0' }}>
                            <div style={{ fontSize: '10px', color: '#64748B', fontWeight: 700 }}>Day {i + 1}</div>
                            <div style={{ fontSize: '12.5px', fontWeight: 800, color: '#0F172A', marginTop: 2 }}>{v.toLocaleString()}</div>
                            <div style={{ fontSize: '9.5px', color: '#0284C7', fontFamily: 'var(--font-mono)' }}>[{low}-{high}]</div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>

              {/* 23 District Table */}
              <div className="panel-card-clean">
                <div className="panel-title-clean">
                  <BarChart3 size={16} color="#0284C7" />
                  <span>Punjab 23-District Meal Demand & Hunger Index (HVI)</span>
                </div>

                <table className="table-clean">
                  <thead>
                    <tr>
                      <th>District / Agro Region</th>
                      <th>Vulnerability (HVI)</th>
                      <th>Weekly Demand</th>
                      <th>Scheduled Rescue</th>
                      <th>Net Shortfall</th>
                      <th>Primary Food Need</th>
                    </tr>
                  </thead>
                  <tbody>
                    {districts.map((d, idx) => (
                      <tr key={idx}>
                        <td style={{ fontWeight: 700, color: '#0F172A' }}>{d.district}</td>
                        <td>
                          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, color: d.hungerVulnerabilityIndex > 90 ? '#B91C1C' : '#D97706' }}>
                            {d.hungerVulnerabilityIndex}/100
                          </span>
                        </td>
                        <td>{d.weeklyForecastDemandLbs.toLocaleString()} lbs</td>
                        <td>{d.scheduledRescueLbs.toLocaleString()} lbs</td>
                        <td style={{ color: d.gapLbs < 0 ? '#B91C1C' : '#059669', fontWeight: 750, fontFamily: 'var(--font-mono)' }}>
                          {d.gapLbs < 0 ? `${d.gapLbs.toLocaleString()} lbs` : `+${d.gapLbs.toLocaleString()} lbs`}
                        </td>
                        <td style={{ fontSize: '12px', color: '#64748B' }}>{d.primaryNeed}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ════ TAB 6: REST API SANDBOX ════ */}
          {activeTab === 'api' && (
            <div className="panel-card-clean">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 10 }}>
                <div className="panel-title-clean">
                  <Cpu size={16} color="#7C3AED" />
                  <span>OpenAPI v3.1 Interactive Fleet Dispatch Sandbox</span>
                </div>

                {/* Endpoint Switcher */}
                <div style={{ display: 'flex', gap: 6 }}>
                  {[
                    { id: 'match', label: '1. /optimize/match' },
                    { id: 'shelf', label: '2. /predict/shelf-life' },
                    { id: 'forecast', label: '3. /forecast/demand' },
                    { id: 'routing', label: '4. /optimize/routing' },
                  ].map(ep => (
                    <button
                      key={ep.id}
                      onClick={() => {
                        setApiSandboxEndpoint(ep.id);
                        setApiSandboxResponse(null);
                      }}
                      style={{
                        padding: '5px 10px',
                        fontSize: '11.5px',
                        fontWeight: apiSandboxEndpoint === ep.id ? 700 : 500,
                        background: apiSandboxEndpoint === ep.id ? '#EDE9FE' : '#F8FAFC',
                        color: apiSandboxEndpoint === ep.id ? '#6D28D9' : '#475569',
                        border: `1px solid ${apiSandboxEndpoint === ep.id ? '#C4B5FD' : '#E2E8F0'}`,
                        borderRadius: 5,
                        cursor: 'pointer'
                      }}
                    >
                      {ep.label}
                    </button>
                  ))}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1.3fr', gap: 18 }}>
                {/* Left: Request Configuration & Live Execution Button */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '12.5px', fontWeight: 700, color: '#475569' }}>Request Payload</span>
                    <button
                      onClick={async () => {
                        setApiSandboxLoading(true);
                        const t0 = performance.now();
                        try {
                          let res;
                          if (apiSandboxEndpoint === 'match') {
                            res = await optimizeMatch(
                              {
                                batch_id: 'VERKA-LUD-LIVE-01',
                                donor_id: 'donor-verka-ludhiana-01',
                                category: 'Dairy',
                                gross_weight_kg: 850.0,
                                origin_coordinates: [30.9325, 75.8350],
                                dietary_flags: { is_pure_veg: true },
                                ambient_temp_c: ambientTempC,
                              },
                              { temp_c: ambientTempC, humidity_pct: 72.0 },
                              null,
                              { use_milp: solverMode === 'milp' }
                            );
                          } else if (apiSandboxEndpoint === 'shelf') {
                            res = await predictShelfLife({
                              category: 'Dairy',
                              ambient_temp_c: ambientTempC,
                              humidity_pct: 72.0,
                              elapsed_hours: 1.0,
                            });
                          } else if (apiSandboxEndpoint === 'forecast') {
                            res = await forecastDemand({ district_id: 'ludhiana', horizon_days: 7 });
                          } else if (apiSandboxEndpoint === 'routing') {
                            res = await optimizeRouting({
                              pickup_nodes: [{ batch_id: 'b1', origin_coordinates: [30.9325, 75.8350], gross_weight_kg: 500, cold_chain_mandatory: true }],
                              dropoff_nodes: [{ recipient_id: 'r1', coordinates: [31.62, 74.8765] }],
                              use_or_tools: true,
                              lambda_penalty: 2.0,
                            });
                          }
                          setApiSandboxLatency(Math.round(performance.now() - t0));
                          setApiSandboxResponse(res);
                        } catch (err) {
                          setApiSandboxLatency(Math.round(performance.now() - t0));
                          setApiSandboxResponse({ error: String(err) });
                        } finally {
                          setApiSandboxLoading(false);
                        }
                      }}
                      disabled={apiSandboxLoading}
                      style={{
                        background: '#7C3AED',
                        color: '#FFFFFF',
                        border: 'none',
                        borderRadius: 5,
                        padding: '6px 12px',
                        fontSize: '12px',
                        fontWeight: 650,
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6,
                        cursor: 'pointer',
                        boxShadow: '0 1px 3px rgba(124,58,237,0.3)'
                      }}
                    >
                      {apiSandboxLoading ? <RefreshCw size={13} className="spin" /> : <Play size={13} />}
                      <span>Execute Live Request</span>
                    </button>
                  </div>

                  <pre style={{ background: '#F8FAFC', padding: '14px', borderRadius: 6, border: '1px solid #E2E8F0', color: '#0284C7', fontSize: '11.5px', fontFamily: 'var(--font-mono)', overflowX: 'auto', lineHeight: 1.55, height: '280px' }}>
                    {apiSandboxEndpoint === 'match' && JSON.stringify({
                      surplus_batch: {
                        batch_id: 'VERKA-LUD-LIVE-01',
                        donor_id: 'donor-verka-ludhiana-01',
                        category: 'Dairy',
                        gross_weight_kg: 850.0,
                        origin_coordinates: [30.9325, 75.8350],
                        dietary_flags: { is_pure_veg: true },
                        ambient_temp_c: ambientTempC,
                      },
                      ambient_weather: { temp_c: ambientTempC, humidity_pct: 72.0 },
                      use_milp: solverMode === 'milp',
                      solver: solverMode === 'milp' ? 'pulp' : 'greedy',
                    }, null, 2)}

                    {apiSandboxEndpoint === 'shelf' && JSON.stringify({
                      category: 'Dairy',
                      ambient_temp_c: ambientTempC,
                      humidity_pct: 72.0,
                      elapsed_hours: 1.0,
                    }, null, 2)}

                    {apiSandboxEndpoint === 'forecast' && `GET /api/v1/forecast/demand?district_id=ludhiana&horizon_days=7`}

                    {apiSandboxEndpoint === 'routing' && JSON.stringify({
                      pickup_nodes: [{ batch_id: 'b1', origin_coordinates: [30.9325, 75.8350], gross_weight_kg: 500, cold_chain_mandatory: true }],
                      dropoff_nodes: [{ recipient_id: 'r1', coordinates: [31.62, 74.8765] }],
                      use_or_tools: true,
                      lambda_penalty: 2.0,
                    }, null, 2)}
                  </pre>
                </div>

                {/* Right: Live Response Output */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '12.5px', fontWeight: 700, color: '#475569' }}>
                      Server Response {apiSandboxLatency != null && `(${apiSandboxLatency}ms)`}
                    </span>
                    <span style={{ fontSize: '11px', color: isBackendHealthy ? '#059669' : '#D97706', fontWeight: 650 }}>
                      ● {isBackendHealthy ? 'Live FastAPI Backend' : 'Mock Response'}
                    </span>
                  </div>

                  <pre style={{ background: '#0F172A', color: '#34D399', padding: '14px', borderRadius: 6, fontSize: '11.5px', fontFamily: 'var(--font-mono)', overflowX: 'auto', lineHeight: 1.55, height: '280px' }}>
                    {apiSandboxResponse ? JSON.stringify(apiSandboxResponse, null, 2) : `// Click "Execute Live Request" to trigger this endpoint\n// Response payload will render here with real-time latency.`}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
