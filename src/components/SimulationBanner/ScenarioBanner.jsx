import React from 'react';
import { PlayCircle, Flame, Truck, AlertTriangle, Users, RotateCcw } from 'lucide-react';

export function ScenarioBanner({ activeScenario, onSelectScenario, onReset }) {
  return (
    <div className="scenario-banner">
      <div className="scenario-title-wrap">
        <PlayCircle size={16} />
        <span>Live Operational Simulation Lab:</span>
        <span style={{ color: 'var(--text-secondary)', fontWeight: 400, fontSize: '11.5px' }}>
          Test how FreshRoute AI responds to real-time supply chain disruptions
        </span>
      </div>

      <div className="scenario-pills">
        <button 
          className={`scenario-pill-btn warning-scenario ${activeScenario === 'heatwave' ? 'active' : ''}`}
          onClick={() => onSelectScenario('heatwave')}
          title="Simulates 94°F heatwave accelerating milk & salad decay, re-routing refrigerated fleet"
        >
          <Flame size={13} color="#F59E0B" />
          Heatwave Surge (+10°F)
        </button>

        <button 
          className={`scenario-pill-btn ${activeScenario === 'flash_surplus' ? 'active' : ''}`}
          onClick={() => onSelectScenario('flash_surplus')}
          title="Simulates sudden 1,200 lb dairy surplus drop at supermarket needing instant matching"
        >
          <Truck size={13} color="#34D399" />
          Flash Surplus (+1,200 lbs)
        </button>

        <button 
          className={`scenario-pill-btn ${activeScenario === 'shelter_surge' ? 'active' : ''}`}
          onClick={() => onSelectScenario('shelter_surge')}
          title="Simulates emergency meal demand surge at Hope Center Pantry"
        >
          <Users size={13} color="#60A5FA" />
          Shelter Urgent Influx
        </button>

        <button 
          className={`scenario-pill-btn ${activeScenario === 'traffic_reroute' ? 'active' : ''}`}
          onClick={() => onSelectScenario('traffic_reroute')}
          title="Simulates I-5 highway closure requiring AI multi-stop dynamic re-route"
        >
          <AlertTriangle size={13} color="#F87171" />
          Fleet Re-Route Alert
        </button>

        {activeScenario !== 'baseline' && (
          <button 
            className="scenario-pill-btn" 
            onClick={onReset}
            style={{ borderColor: 'rgba(255,255,255,0.2)', color: '#CBD5E1' }}
            title="Reset to default operational state"
          >
            <RotateCcw size={12} />
            Reset Baseline
          </button>
        )}
      </div>
    </div>
  );
}
