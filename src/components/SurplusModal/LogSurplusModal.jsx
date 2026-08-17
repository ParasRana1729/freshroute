import React, { useState } from 'react';
import { X, PlusCircle } from 'lucide-react';

export function LogSurplusModal({ isOpen, onClose, onAddSurplus, donors }) {
  const [form, setForm] = useState({
    donorName: donors[0]?.name || '',
    category: 'Dairy',
    itemName: '',
    weightLbs: 1200,
    shelfLifeHours: 18,
    tempReq: '2°C - 4°C Strict Cold-Chain',
    urgencyLevel: 'high',
    notes: ''
  });

  if (!isOpen) return null;

  const submit = (e) => {
    e.preventDefault();
    onAddSurplus(form);
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <div className="modal-title">Log Punjab Mandi / Dairy Surplus</div>
            <span style={{ fontSize: '12px', color: 'var(--ink-muted)' }}>
              Ingest batch into Punjab State Pareto Allocation Matrix
            </span>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--ink-muted)', cursor: 'pointer' }}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={submit}>
          <div className="modal-body">
            <div className="form-group">
              <label className="form-label">Donor Facility</label>
              <select
                className="form-select"
                value={form.donorName}
                onChange={e => setForm({ ...form, donorName: e.target.value })}
              >
                {donors.map(d => (
                  <option key={d.id} value={d.name}>{d.name} ({d.category})</option>
                ))}
              </select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="form-group">
                <label className="form-label">Perishability Category</label>
                <select
                  className="form-select"
                  value={form.category}
                  onChange={e => setForm({ ...form, category: e.target.value })}
                >
                  <option value="Dairy">Chilled Verka Dairy (Milk, Paneer, Dahi)</option>
                  <option value="Prepared">Prepared Cooked Langar Meals</option>
                  <option value="Produce">Fresh Mandi Vegetables & Fruits</option>
                  <option value="Bakery">Whole Wheat Atta & Bakery Rations</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Batch Description</label>
                <input
                  required
                  placeholder="e.g. 100 Crates Verka Pasteurized Milk"
                  className="form-input"
                  value={form.itemName}
                  onChange={e => setForm({ ...form, itemName: e.target.value })}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="form-group">
                <label className="form-label">Gross Weight (lbs)</label>
                <input
                  type="number"
                  required
                  min="10"
                  className="form-input"
                  value={form.weightLbs}
                  onChange={e => setForm({ ...form, weightLbs: Number(e.target.value) })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Estimated Shelf-Life (hours)</label>
                <input
                  type="number"
                  required
                  min="1"
                  className="form-input"
                  value={form.shelfLifeHours}
                  onChange={e => setForm({ ...form, shelfLifeHours: Number(e.target.value) })}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="form-group">
                <label className="form-label">Cold-Chain Temperature Spec</label>
                <select
                  className="form-select"
                  value={form.tempReq}
                  onChange={e => setForm({ ...form, tempReq: e.target.value })}
                >
                  <option>2°C - 4°C Strict Cold-Chain</option>
                  <option>4°C - 8°C Chilled Transport</option>
                  <option>Dry Ambient (Grains / Atta)</option>
                  <option>Deep Frozen (&lt;-18°C)</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Thermal Urgency Level</label>
                <select
                  className="form-select"
                  value={form.urgencyLevel}
                  onChange={e => setForm({ ...form, urgencyLevel: e.target.value })}
                >
                  <option value="critical">Critical (Immediate GT Road Pickup)</option>
                  <option value="high">High (&lt;16h Window)</option>
                  <option value="moderate">Moderate (&lt;48h Window)</option>
                </select>
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              <PlusCircle size={14} /> Ingest into Punjab Grid
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
