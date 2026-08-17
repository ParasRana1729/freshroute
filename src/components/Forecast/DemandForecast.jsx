import React, { useState } from 'react';
import { BarChart3, Users, AlertCircle, Calendar, Sparkles, TrendingUp, Filter } from 'lucide-react';

export function DemandForecast({ districts }) {
  const [selectedDayIndex, setSelectedDayIndex] = useState(4); // Default Friday
  const [metricType, setMetricType] = useState('lbs'); // 'lbs', 'meals', 'co2'

  const weekForecast = [
    { day: 'Monday', short: 'Mon', demandPct: 65, supplyPct: 70, demandLbs: 24000, supplyLbs: 26000 },
    { day: 'Tuesday', short: 'Tue', demandPct: 75, supplyPct: 80, demandLbs: 28000, supplyLbs: 30000 },
    { day: 'Wednesday', short: 'Wed', demandPct: 88, supplyPct: 85, demandLbs: 34000, supplyLbs: 32500 },
    { day: 'Thursday', short: 'Thu', demandPct: 92, supplyPct: 88, demandLbs: 36000, supplyLbs: 34000 },
    { day: 'Friday', short: 'Fri', demandPct: 98, supplyPct: 94, demandLbs: 41000, supplyLbs: 39600 },
    { day: 'Saturday', short: 'Sat', demandPct: 82, supplyPct: 78, demandLbs: 31000, supplyLbs: 29500 },
    { day: 'Sunday', short: 'Sun', demandPct: 55, supplyPct: 60, demandLbs: 20000, supplyLbs: 22000 },
  ];

  const currentDay = weekForecast[selectedDayIndex];

  const formatMetric = (lbs) => {
    if (metricType === 'meals') return `~${Math.round(lbs * 0.83).toLocaleString()} meals`;
    if (metricType === 'co2') return `${Math.round(lbs * 2.5).toLocaleString()} kg CO₂`;
    return `${lbs.toLocaleString()} lbs`;
  };

  return (
    <div className="forecast-grid">
      {/* 7-Day Interactive Forecast */}
      <div className="chart-panel">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '12px', borderBottom: '1px solid var(--console-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '13.5px', fontWeight: 700, color: '#FFFFFF' }}>
            <BarChart3 size={16} color="#34D399" />
            7-Day Time-Series Pantry Demand vs Surplus Supply
          </div>

          {/* Metric Toggle */}
          <div style={{ display: 'flex', gap: 4 }}>
            {[
              { id: 'lbs', label: 'Lbs' },
              { id: 'meals', label: 'Meals' },
              { id: 'co2', label: 'CO₂e' }
            ].map(m => (
              <button
                key={m.id}
                className={`sbtn ${metricType === m.id ? 'on' : ''}`}
                onClick={() => setMetricType(m.id)}
                style={{ fontSize: '11px', padding: '3px 8px' }}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11.5px', color: '#94A3B8' }}>
          <div style={{ display: 'flex', gap: 16 }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 10, height: 10, background: '#38BDF8', borderRadius: 2 }} /> Pantry Demand: <strong>{formatMetric(currentDay.demandLbs)}</strong>
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 10, height: 10, background: '#059669', borderRadius: 2 }} /> Ingested Supply: <strong>{formatMetric(currentDay.supplyLbs)}</strong>
            </span>
          </div>
          <span style={{ fontSize: '10.5px', color: '#64748B', fontFamily: 'var(--font-mono)' }}>Click day bar to inspect</span>
        </div>

        {/* Bar Chart Area */}
        <div className="bar-chart-area">
          {weekForecast.map((item, i) => {
            const isSelected = selectedDayIndex === i;
            return (
              <div
                key={i}
                className="bar-group"
                onClick={() => setSelectedDayIndex(i)}
                style={{ cursor: 'pointer', opacity: isSelected ? 1 : 0.65 }}
              >
                <div className="bars-pair">
                  <div
                    className="bar demand"
                    style={{
                      height: `${item.demandPct}%`,
                      border: isSelected ? '1px solid #FFFFFF' : 'none'
                    }}
                    title={`${item.day} Demand: ${item.demandLbs.toLocaleString()} lbs`}
                  />
                  <div
                    className="bar supply"
                    style={{
                      height: `${item.supplyPct}%`,
                      border: isSelected ? '1px solid #FFFFFF' : 'none'
                    }}
                    title={`${item.day} Supply: ${item.supplyLbs.toLocaleString()} lbs`}
                  />
                </div>
                <span className="bar-label" style={{ color: isSelected ? '#34D399' : '#64748B', fontWeight: isSelected ? 700 : 500 }}>
                  {item.short}
                </span>
              </div>
            );
          })}
        </div>

        {/* Alert Callout for Selected Day */}
        <div style={{
          background: 'rgba(56, 189, 248, 0.08)',
          border: '1px solid rgba(56, 189, 248, 0.25)',
          borderRadius: 'var(--radius-xs)',
          padding: '10px 14px',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          marginTop: '4px'
        }}>
          <AlertCircle size={16} color="#38BDF8" style={{ flexShrink: 0 }} />
          <span style={{ fontSize: '12px', color: '#BAE6FD', lineHeight: 1.5 }}>
            <strong>{currentDay.day} AI Forecast:</strong> Projected network demand of {formatMetric(currentDay.demandLbs)}. {currentDay.demandLbs > currentDay.supplyLbs ? `Anticipating ${(currentDay.demandLbs - currentDay.supplyLbs).toLocaleString()} lb gap in downtown district. Additional evening recovery route queued.` : 'Supply exceeds demand. Redistribution routing to suburban storage depots enabled.'}
          </span>
        </div>
      </div>

      {/* District Vulnerability List */}
      <div className="chart-panel">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '12px', borderBottom: '1px solid var(--console-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '13.5px', fontWeight: 700, color: '#FFFFFF' }}>
            <Users size={15} color="#A78BFA" />
            District Hunger Vulnerability Indices
          </div>
          <span style={{ fontSize: '11px', color: '#94A3B8', fontFamily: 'var(--font-mono)' }}>{districts.length} ZONES</span>
        </div>

        <div className="district-list">
          {districts.map((d, i) => {
            const deficit = d.gapLbs < 0;
            return (
              <div key={i} className="district-item">
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', fontWeight: 700, color: '#FFFFFF' }}>
                  <span>{d.district}</span>
                  <span style={{
                    fontSize: '10px',
                    fontFamily: 'var(--font-mono)',
                    padding: '1px 6px',
                    borderRadius: '4px',
                    background: d.hungerVulnerabilityIndex > 85 ? 'var(--red-tint)' : 'var(--brand-tint)',
                    color: d.hungerVulnerabilityIndex > 85 ? '#FCA5A5' : '#86EFAC',
                    border: `1px solid ${d.hungerVulnerabilityIndex > 85 ? 'var(--red-border)' : 'var(--brand-border)'}`
                  }}>
                    {d.hungerVulnerabilityIndex}/100 HVI
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#94A3B8' }}>
                  <span>Weekly Need: <strong style={{ color: '#E2E8F0', fontFamily: 'var(--font-mono)' }}>{d.weeklyForecastDemandLbs.toLocaleString()} lbs</strong></span>
                  <span style={{ color: deficit ? '#F87171' : '#34D399', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                    {deficit ? `${d.gapLbs.toLocaleString()} lb shortfall` : `+${d.gapLbs} lb balance`}
                  </span>
                </div>

                <div style={{ fontSize: '10.5px', color: '#64748B', display: 'flex', justifyContent: 'space-between' }}>
                  <span>Primary Need: <strong style={{ color: '#CBD5E1' }}>{d.primaryNeed}</strong></span>
                  <span>{d.trend}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
