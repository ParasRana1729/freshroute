import React, { useState } from 'react';
import { 
  Sparkles, ArrowRight, Send, Check, Leaf, Scale, Utensils, Clock, 
  Search, SlidersHorizontal, CheckCircle2, ShieldCheck, Zap
} from 'lucide-react';
import confetti from 'canvas-confetti';

export function SmartMatchQueue({ matches, onDispatchMatch, onLogSurplus }) {
  const [filterCat, setFilterCat] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('score');
  const [expandedMatchId, setExpandedMatchId] = useState(null);

  const cats = ['all', 'Dairy', 'Prepared', 'Produce', 'Bakery'];

  const filtered = matches.filter(m => {
    const matchCat = filterCat === 'all' || m.itemCategory.toLowerCase().includes(filterCat.toLowerCase());
    const matchSearch = searchQuery === '' || 
      m.itemName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.donorName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.recipientName.toLowerCase().includes(searchQuery.toLowerCase());
    return matchCat && matchSearch;
  }).sort((a, b) => {
    if (sortBy === 'score') return b.matchScore - a.matchScore;
    if (sortBy === 'urgency') return a.spoilageWindowHours - b.spoilageWindowHours;
    if (sortBy === 'weight') return b.batchWeightLbs - a.batchWeightLbs;
    return 0;
  });

  const pendingMatches = matches.filter(m => m.status === 'Pending Dispatch');

  const handleDispatch = (match) => {
    confetti({
      particleCount: 40,
      spread: 55,
      origin: { y: 0.8 },
      colors: ['#059669', '#34D399', '#0284C7']
    });
    onDispatchMatch(match.id);
  };

  const handleBatchDispatch = () => {
    confetti({
      particleCount: 70,
      spread: 80,
      origin: { y: 0.7 },
      colors: ['#059669', '#34D399', '#38BDF8', '#F59E0B']
    });
    pendingMatches.forEach(m => onDispatchMatch(m.id));
  };

  return (
    <div>
      {/* Header Search & Filter Bar */}
      <div className="matching-header-bar">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Sparkles size={16} color="#34D399" />
          <div>
            <div style={{ fontSize: '13.5px', fontWeight: 700, color: '#FFFFFF' }}>
              Multi-Objective Pareto Queue
            </div>
            <div style={{ fontSize: '11.5px', color: '#94A3B8' }}>
              {pendingMatches.length} pending execution · Solved via Mixed-Integer Linear Optimization
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {/* Quick Search */}
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <Search size={13} color="#64748B" style={{ position: 'absolute', left: 8 }} />
            <input
              type="text"
              placeholder="Search donor, item, pantry..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{
                background: '#0B1019',
                border: '1px solid var(--console-border)',
                borderRadius: 'var(--radius-xs)',
                padding: '5px 10px 5px 28px',
                fontSize: '12px',
                color: '#FFFFFF',
                outline: 'none',
                width: '200px'
              }}
            />
          </div>

          {/* Sort Selector */}
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            style={{
              background: '#0B1019',
              border: '1px solid var(--console-border)',
              borderRadius: 'var(--radius-xs)',
              padding: '5px 8px',
              fontSize: '12px',
              color: '#CBD5E1',
              outline: 'none'
            }}
          >
            <option value="score">Sort: Pareto Score</option>
            <option value="urgency">Sort: Expiry Clock</option>
            <option value="weight">Sort: Batch Weight</option>
          </select>

          {/* Batch Dispatch Button */}
          {pendingMatches.length > 1 && (
            <button
              className="btn btn-sm btn-primary"
              onClick={handleBatchDispatch}
              style={{ fontSize: '12px', padding: '5px 12px' }}
            >
              <Zap size={12} /> Dispatch All ({pendingMatches.length})
            </button>
          )}
        </div>
      </div>

      {/* Category Pills */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 12, flexWrap: 'wrap' }}>
        {cats.map(c => (
          <button
            key={c}
            className={`sbtn ${filterCat === c ? 'on' : ''}`}
            onClick={() => setFilterCat(c)}
          >
            {c === 'all' ? 'All Categories' : c}
          </button>
        ))}
      </div>

      {/* Matches Grid */}
      <div className="match-grid">
        {filtered.map(m => {
          const isCrit = m.urgencyLevel === 'critical';
          const isHigh = m.urgencyLevel === 'high';
          const dispatched = m.status === 'Dispatched';
          const isExpanded = expandedMatchId === m.id;

          return (
            <div key={m.id} className={`match-card ${isCrit ? 'critical' : isHigh ? 'urgent' : ''}`}>
              <div className="match-top">
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    <span style={{
                      fontSize: '10.5px',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      padding: '2px 8px',
                      borderRadius: 'var(--radius-full)',
                      fontFamily: 'var(--font-mono)',
                      background: isCrit ? 'var(--red-tint)' : isHigh ? 'var(--amber-tint)' : 'var(--brand-tint)',
                      color: isCrit ? '#FCA5A5' : isHigh ? '#FCD34D' : '#86EFAC',
                      border: `1px solid ${isCrit ? 'var(--red-border)' : isHigh ? 'var(--amber-border)' : 'var(--brand-border)'}`
                    }}>
                      {m.urgencyLevel} · {m.itemCategory}
                    </span>
                    {dispatched && (
                      <span style={{
                        fontSize: '10.5px',
                        fontWeight: 700,
                        background: 'var(--cyan-tint)',
                        color: '#7DD3FC',
                        border: '1px solid var(--cyan-border)',
                        padding: '2px 8px',
                        borderRadius: 'var(--radius-full)',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 4
                      }}>
                        <Check size={11} /> En Route
                      </span>
                    )}
                  </div>

                  <div style={{ fontSize: '14.5px', fontWeight: 700, color: '#FFFFFF', letterSpacing: '-0.01em' }}>
                    {m.itemName}
                  </div>

                  <div style={{ display: 'flex', gap: 12, fontSize: '11.5px', color: '#94A3B8', alignItems: 'center' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                      <Scale size={12} color="#CBD5E1" />
                      <strong style={{ color: '#E2E8F0' }}>{m.batchWeightLbs.toLocaleString()} lbs</strong>
                    </span>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                      <Utensils size={12} color="#CBD5E1" />
                      ~{m.mealsEquivalent.toLocaleString()} meals
                    </span>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                      <Clock size={12} color="#CBD5E1" />
                      {m.spoilageWindowHours}h shelf
                    </span>
                  </div>
                </div>

                <div className="match-score">
                  <span>{m.matchScore}%</span>
                  <span style={{ fontSize: '7.5px', fontWeight: 700, color: '#94A3B8', letterSpacing: '0.04em' }}>SCORE</span>
                </div>
              </div>

              <div className="match-route">
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '9.5px', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>Donor Source</div>
                  <div style={{ fontSize: '12.5px', fontWeight: 700, color: '#FFFFFF' }}>{m.donorName}</div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', color: '#34D399', padding: '0 10px', fontSize: '11px' }}>
                  <ArrowRight size={15} />
                  <span style={{ fontFamily: 'var(--font-mono)' }}>{m.estimatedTransitMins}m ETA</span>
                </div>
                <div style={{ flex: 1, textAlign: 'right' }}>
                  <div style={{ fontSize: '9.5px', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>Pantry Recipient</div>
                  <div style={{ fontSize: '12.5px', fontWeight: 700, color: '#FFFFFF' }}>{m.recipientName}</div>
                </div>
              </div>

              <div className="match-factors">
                <div className="mf-item">
                  <span className="l">Proximity</span>
                  <span className="v">{m.matchFactors.proximityScore}</span>
                </div>
                <div className="mf-item">
                  <span className="l">Decay Risk</span>
                  <span className="v" style={{ color: isCrit ? '#F87171' : '#FFFFFF' }}>{m.matchFactors.perishabilityUrgency}</span>
                </div>
                <div className="mf-item">
                  <span className="l">Need Index</span>
                  <span className="v">{m.matchFactors.recipientNeedScore}</span>
                </div>
                <div className="mf-item">
                  <span className="l">Diet Match</span>
                  <span className="v" style={{ color: '#34D399' }}>{m.matchFactors.dietaryCompatibility}</span>
                </div>
                <div className="mf-item" style={{ gridColumn: 'span 2' }}>
                  <span className="l">Reefer Assigned</span>
                  <span className="v" style={{ color: '#38BDF8' }}>{m.assignedVehicleName || 'Reefer Sprinter'}</span>
                </div>
              </div>

              <div className="match-rationale">
                <strong style={{ color: '#FFFFFF' }}>AI Pareto Rationale: </strong>{m.aiRationale}
              </div>

              <div className="match-actions">
                <span style={{ fontSize: '11.5px', color: '#94A3B8', display: 'flex', alignItems: 'center', gap: 5 }}>
                  <Leaf size={13} color="#34D399" />
                  {m.co2SavedKg} kg CO₂e Saved
                </span>
                {dispatched ? (
                  <button className="sbtn" disabled style={{ opacity: 0.7 }}>
                    <Check size={12} color="#10B981" /> Dispatched
                  </button>
                ) : (
                  <button className="btn btn-sm btn-primary" onClick={() => handleDispatch(m)}>
                    <Send size={12} /> Dispatch Van
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
