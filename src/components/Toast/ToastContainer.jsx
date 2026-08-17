import React from 'react';
import { CheckCircle, AlertTriangle, Info, X } from 'lucide-react';

export function ToastContainer({ toasts, onDismiss }) {
  if (!toasts || toasts.length === 0) return null;
  return (
    <div className="toast-container">
      {toasts.map(t => (
        <div key={t.id} className={`toast ${t.type || ''}`}>
          {t.type === 'success' && <CheckCircle size={16} color="#0D9668" />}
          {t.type === 'warning' && <AlertTriangle size={16} color="#E5890A" />}
          {t.type !== 'success' && t.type !== 'warning' && <Info size={16} color="#3B82F6" />}
          <div style={{flex:1}}>
            <strong style={{fontSize:13,display:'block'}}>{t.title}</strong>
            <span style={{fontSize:12,color:'var(--ink-secondary)'}}>{t.message}</span>
          </div>
          <button onClick={() => onDismiss(t.id)} style={{background:'none',border:'none',color:'var(--ink-muted)',cursor:'pointer'}}><X size={14} /></button>
        </div>
      ))}
    </div>
  );
}
