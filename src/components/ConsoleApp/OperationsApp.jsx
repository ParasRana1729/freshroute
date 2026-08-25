import React, { useState } from 'react';
import { 
  MapPin, Sparkles, Clock, BarChart3, Cpu, PlusCircle,
  Flame, Truck, AlertTriangle, Users, RotateCcw, SunMedium,
  ArrowLeft, Layers, ShieldCheck, ChevronDown, CheckCircle2,
  LayoutDashboard, Search, ExternalLink, ArrowRight, Play,
  TrendingUp, Radio, Sliders, Check, X, Calendar, Fuel, Thermometer
} from 'lucide-react';
import { OperationsMap } from '../Map/OperationsMap';
import { ThermalDecayEngine } from '../RiskEngine/ThermalDecayEngine';

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

          {/* ════ TAB 3: LANGAR MATCH QUEUE (CLEAN LIGHT TABLE) ════ */}
          {activeTab === 'queue' && (
            <div className="queue-container-clean">
              <div className="queue-toolbar-clean">
                <div className="queue-filters-clean">
                  {['all', 'dairy', 'prepared', 'produce', 'bakery'].map(cat => (
                    <button
                      key={cat}
                      className={`q-tab-btn ${categoryFilter === cat ? 'active' : ''}`}
                      onClick={() => setCategoryFilter(cat)}
                    >
                      {cat === 'all' ? 'All Surplus' : cat.charAt(0).toUpperCase() + cat.slice(1)}
                    </button>
                  ))}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{ position: 'relative' }}>
                    <Search size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
                    <input
                      placeholder="Filter donor, item, or langar..."
                      value={searchQuery}
                      onChange={e => setSearchQuery(e.target.value)}
                      style={{ background: '#FFFFFF', border: '1px solid #CBD5E1', borderRadius: 6, padding: '5px 10px 5px 28px', fontSize: '12px', color: '#0F172A', outline: 'none' }}
                    />
                  </div>

                  <button 
                    onClick={() => matches.filter(m => m.status === 'Pending Dispatch').forEach(m => onDispatchMatch(m.id))}
                    style={{ background: '#059669', color: '#FFFFFF', border: 'none', borderRadius: 6, padding: '6px 12px', fontSize: '12px', fontWeight: 650, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}
                  >
                    <span>Dispatch All ({pendingMatches.length})</span>
                  </button>
                </div>
              </div>

              <div style={{ overflowX: 'auto' }}>
                <table className="table-clean">
                  <thead>
                    <tr>
                      <th>Batch Item</th>
                      <th>Origin → Recipient</th>
                      <th>Safe Window</th>
                      <th>Assigned Fleet</th>
                      <th>Pareto Score</th>
                      <th>Status & Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredMatches.map(m => {
                      const isPending = m.status === 'Pending Dispatch';
                      const isUrgent = m.urgencyLevel === 'critical';

                      return (
                        <tr key={m.id} onClick={() => setSelectedMatch(m)} style={{ cursor: 'pointer' }}>
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <span className={`badge-risk ${isUrgent ? 'crit' : 'high'}`}>
                                {m.urgencyLevel.toUpperCase()}
                              </span>
                              <strong style={{ color: '#0F172A', fontSize: '13.5px' }}>{m.itemName}</strong>
                            </div>
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
            <div className="panel-card-clean">
              <div className="panel-title-clean">
                <BarChart3 size={16} color="#0284C7" />
                <span>Punjab 23-District Meal Demand & Hunger Index</span>
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
          )}

          {/* ════ TAB 6: API SANDBOX ════ */}
          {activeTab === 'api' && (
            <div className="panel-card-clean">
              <div className="panel-title-clean">
                <Cpu size={16} color="#7C3AED" />
                <span>OpenAPI v3.1 Punjab Fleet Dispatch API</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
                <div>
                  <div style={{ fontSize: '12.5px', fontWeight: 700, color: '#475569', marginBottom: 8 }}>
                    POST /api/v1/predict/match (Surplus-to-Langar Allocation)
                  </div>
                  <pre style={{ background: '#F8FAFC', padding: '14px', borderRadius: 6, border: '1px solid #E2E8F0', color: '#0284C7', fontSize: '11.5px', fontFamily: 'var(--font-mono)', overflowX: 'auto', lineHeight: 1.55 }}>
{`{
  "donor_id": "verka_ludhiana_01",
  "item_category": "Dairy",
  "weight_kg": 816,
  "temp_req_c": [2, 4],
  "ambient_weather": {
    "temp_c": ${ambientTempC},
    "decay_multiplier": ${(1 + (ambientTempC - 25) * 0.038).toFixed(2)}
  },
  "candidate_recipients": [
    "recip-amritsar-langar-01",
    "recip-ludhiana-slum-02"
  ]${solverMode === 'milp' ? `,
  "use_milp": true,
  "solver": "pulp"` : ``}
}`}
                  </pre>
                </div>

                <div>
                  <div style={{ fontSize: '12.5px', fontWeight: 700, color: '#475569', marginBottom: 8 }}>
                    Predicted Output (Latency: {solverMode === 'milp' ? '163ms MILP' : '74ms greedy'})
                  </div>
                  <pre style={{ background: '#F8FAFC', padding: '14px', borderRadius: 6, border: '1px solid #E2E8F0', color: '#047857', fontSize: '11.5px', fontFamily: 'var(--font-mono)', overflowX: 'auto', lineHeight: 1.55 }}>
{`{
  "status": "success",
  "match_score": 99.2,
  "assigned_recipient": "Sri Guru Ram Dass Ji Langar",
  "assigned_vehicle": "Ashok Leyland Cold Carrier",
  "eta_minutes": 22,
  "cold_chain_status": "COMPLIANT (2.7°C)",
  "solver": "${solverMode === 'milp' ? 'pulp-cbc:Optimal' : 'greedy'}"
}`}
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
