import React, { useState } from 'react';
import { X, Calendar, CheckCircle2, Calculator, Sparkles } from 'lucide-react';
import confetti from 'canvas-confetti';

export function RequestDemoModal({ isOpen, onClose, onScheduleSuccess, initialWeeklyVolume = 25000 }) {
  const [vol, setVol] = useState(initialWeeklyVolume);
  const [form, setForm] = useState({ name: '', email: '', org: '', orgType: 'Food Bank Network', hubCount: '1-3 Hubs', date: '', notes: '' });
  const [done, setDone] = useState(false);

  React.useEffect(() => {
    if (initialWeeklyVolume) setVol(initialWeeklyVolume);
  }, [initialWeeklyVolume]);

  if (!isOpen) return null;

  const rescued = Math.round(vol * 52 * 0.94);
  const meals = Math.round(rescued * 0.83);
  const co2 = Math.round(rescued * 2.5);
  const hours = Math.round((vol / 1000) * 8.5 * 52);

  const submit = (e) => {
    e.preventDefault();
    confetti({
      particleCount: 50,
      spread: 60,
      origin: { y: 0.6 },
      colors: ['#059669', '#34D399', '#0284C7']
    });
    setDone(true);
    onScheduleSuccess?.({ ...form, weeklyVolumeLbs: vol, annualMeals: meals, annualCo2Kg: co2 });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <div className="modal-title">Schedule a Technical Evaluation</div>
            <span style={{ fontSize: '12px', color: 'var(--ink-muted)' }}>
              Interactive walkthrough of Arrhenius decay models & VRPTW dispatch
            </span>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--ink-muted)', cursor: 'pointer' }}>
            <X size={18} />
          </button>
        </div>

        {done ? (
          <div className="modal-body" style={{ textAlign: 'center', padding: '36px 24px' }}>
            <div style={{ width: 48, height: 48, borderRadius: '50%', background: 'var(--green-50)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
              <CheckCircle2 size={28} color="var(--green-700)" />
            </div>
            <h3 style={{ fontFamily: 'var(--font-serif)', fontSize: '24px', fontWeight: 400, color: 'var(--ink-primary)', marginBottom: 8 }}>
              Evaluation Scheduled
            </h3>
            <p style={{ fontSize: '14px', color: 'var(--ink-secondary)', maxWidth: 400, margin: '0 auto 20px', lineHeight: 1.5 }}>
              Thank you, <strong>{form.name || 'Partner'}</strong>. We have sent calendar confirmation details to <strong>{form.email || 'your email'}</strong>.
            </p>
            <div style={{ background: 'var(--bg-soft)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: 16, maxWidth: 420, margin: '0 auto 24px', textAlign: 'left' }}>
              <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--green-800)', textTransform: 'uppercase', marginBottom: 8 }}>
                Estimated Annual Network Projection:
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: '13px' }}>
                <div>Meals: <strong style={{ color: 'var(--ink-primary)' }}>{meals.toLocaleString()}</strong></div>
                <div>CO₂e Diverted: <strong style={{ color: 'var(--ink-primary)' }}>{co2.toLocaleString()} kg</strong></div>
                <div>Food Rescued: <strong style={{ color: 'var(--ink-primary)' }}>{rescued.toLocaleString()} lbs</strong></div>
                <div>Admin Hours Saved: <strong style={{ color: 'var(--ink-primary)' }}>{hours.toLocaleString()}h</strong></div>
              </div>
            </div>
            <button className="btn btn-primary" onClick={onClose}>Return to Operations</button>
          </div>
        ) : (
          <form onSubmit={submit}>
            <div className="modal-body">
              <div className="roi-box">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--ink-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Calculator size={14} color="var(--green-700)" /> Impact Parameter
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 700, color: 'var(--green-800)' }}>
                    {vol.toLocaleString()} lbs / week
                  </span>
                </div>
                <input
                  type="range"
                  min="5000"
                  max="150000"
                  step="5000"
                  value={vol}
                  onChange={e => setVol(Number(e.target.value))}
                  className="calc-slider"
                />
                <div className="roi-stats">
                  <div>
                    <div className="roi-num">~{(meals / 1000).toFixed(0)}k</div>
                    <div className="roi-label">Meals / Yr</div>
                  </div>
                  <div>
                    <div className="roi-num">{(co2 / 1000).toFixed(0)}t</div>
                    <div className="roi-label">CO₂e / Yr</div>
                  </div>
                  <div>
                    <div className="roi-num">{hours.toLocaleString()}h</div>
                    <div className="roi-label">Hours Saved</div>
                  </div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="form-group">
                  <label className="form-label">Full Name *</label>
                  <input
                    required
                    placeholder="Elena Rostova"
                    className="form-input"
                    value={form.name}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Work Email *</label>
                  <input
                    type="email"
                    required
                    placeholder="elena@foodbanknetwork.org"
                    className="form-input"
                    value={form.email}
                    onChange={e => setForm({ ...form, email: e.target.value })}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="form-group">
                  <label className="form-label">Organization Name *</label>
                  <input
                    required
                    placeholder="Pacific Food Alliance"
                    className="form-input"
                    value={form.org}
                    onChange={e => setForm({ ...form, org: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Organization Type</label>
                  <select
                    className="form-select"
                    value={form.orgType}
                    onChange={e => setForm({ ...form, orgType: e.target.value })}
                  >
                    <option>Food Bank Network</option>
                    <option>Commercial Grocery Chain</option>
                    <option>Community Pantry Hub</option>
                    <option>Municipal Climate Agency</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="form-group">
                  <label className="form-label">Preferred Date</label>
                  <input
                    type="date"
                    className="form-input"
                    value={form.date}
                    onChange={e => setForm({ ...form, date: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Network Distribution Scale</label>
                  <select
                    className="form-select"
                    value={form.hubCount}
                    onChange={e => setForm({ ...form, hubCount: e.target.value })}
                  >
                    <option>1-3 Distribution Hubs</option>
                    <option>4-10 Regional Hubs</option>
                    <option>10+ Statewide Matrix</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button type="button" className="btn btn-ghost" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary">
                <Sparkles size={14} /> Request Private Pilot
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
