import React, { useState } from 'react';
import { Cpu, Network, GitBranch, Sliders, Terminal, Copy, CheckCircle, Play, Code2 } from 'lucide-react';

export function ModelTelemetry({ endpoints }) {
  const [sel, setSel] = useState(endpoints[0]);
  const [copied, setCopied] = useState(false);
  const [codeLang, setCodeLang] = useState('curl'); // 'curl', 'python', 'node'
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState(null);

  const copy = (t) => {
    navigator.clipboard.writeText(t);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExecuteRequest = () => {
    setIsExecuting(true);
    setExecutionResult(null);

    setTimeout(() => {
      setIsExecuting(false);
      setExecutionResult({
        status: 200,
        statusText: 'OK',
        latencyMs: Math.floor(Math.random() * 40) + 65,
        timestamp: new Date().toISOString(),
        data: {
          status: 'success',
          engine_version: 'FreshRoute-MILPv4.2',
          solver: 'Highs-Pareto-v1.4',
          objective_value: 0.9842,
          recommendation: {
            assigned_hub: 'Hub-SouthHarbor',
            van_id: 'van-04-reefer',
            estimated_transit_min: 14.2,
            thermal_loss_risk_pct: 1.4,
            co2_diverted_kg: 3000
          }
        }
      });
    }, 600);
  };

  const generateSnippet = () => {
    if (codeLang === 'python') {
      return `import requests

url = "https://api.freshroute.ops/v1${sel.endpoint.replace('/api/v1', '')}"
headers = {"Authorization": "Bearer fr_live_99a8x...", "Content-Type": "application/json"}
payload = ${sel.samplePayload}

response = requests.post(url, json=payload, headers=headers)
print(response.json())`;
    }

    if (codeLang === 'node') {
      return `const response = await fetch("https://api.freshroute.ops/v1${sel.endpoint.replace('/api/v1', '')}", {
  method: "${sel.method}",
  headers: {
    "Authorization": "Bearer fr_live_99a8x...",
    "Content-Type": "application/json"
  },
  body: JSON.stringify(${sel.samplePayload})
});

const result = await response.json();
console.log(result);`;
    }

    return `curl -X ${sel.method} "https://api.freshroute.ops/v1${sel.endpoint.replace('/api/v1', '')}" \\
  -H "Authorization: Bearer fr_live_99a8x..." \\
  -H "Content-Type: application/json" \\
  -d '${sel.samplePayload.replace(/\n/g, '').replace(/\s+/g, ' ')}'`;
  };

  return (
    <div className="arch-grid">
      {/* Left Panel: Mathematical Formulations & Architecture */}
      <div className="risk-panel">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '12px', borderBottom: '1px solid var(--console-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '13.5px', fontWeight: 700, color: '#FFFFFF' }}>
            <Cpu size={16} color="#34D399" />
            AI Optimization Pipeline Architecture
          </div>
          <span style={{ fontSize: '11px', color: '#38BDF8', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>PLUGGABLE ML</span>
        </div>

        <p style={{ fontSize: '12px', color: '#94A3B8', lineHeight: 1.55, margin: 0 }}>
          FreshRoute is architected with a decoupled microservice API layer. Connect custom ML models to these core optimization routines:
        </p>

        {[
          {
            icon: <Network size={15} color="#34D399" />,
            title: '1. Pareto Multi-Objective Matching',
            color: '#059669',
            desc: 'Mixed-Integer Linear Program (MILP) optimizing hunger vulnerability, perishability decay, and vehicle transit times.'
          },
          {
            icon: <Sliders size={15} color="#F59E0B" />,
            title: '2. Arrhenius Thermal Decay Model',
            color: '#D97706',
            desc: 'Gradient-boosted survival hazard models integrating live NOAA ambient temperatures and trailer IoT thermistors.'
          },
          {
            icon: <GitBranch size={15} color="#38BDF8" />,
            title: '3. Dynamic Cold-Chain VRPTW',
            color: '#0284C7',
            desc: 'Time-window vehicle routing problem (VRPTW) with real-time multi-stop traffic bypass.'
          },
        ].map((p, i) => (
          <div key={i} style={{
            background: '#0B1019',
            borderRadius: 'var(--radius-xs)',
            padding: '12px 14px',
            borderLeft: `3px solid ${p.color}`,
            borderTop: '1px solid var(--console-border-subtle)',
            borderRight: '1px solid var(--console-border-subtle)',
            borderBottom: '1px solid var(--console-border-subtle)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              {p.icon}
              <strong style={{ fontSize: '12.5px', color: '#FFFFFF' }}>{p.title}</strong>
            </div>
            <p style={{ fontSize: '11.5px', color: '#94A3B8', margin: 0, lineHeight: 1.5 }}>{p.desc}</p>
          </div>
        ))}
      </div>

      {/* Right Panel: Interactive Sandbox & OpenAPI Explorer */}
      <div className="risk-panel">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '12px', borderBottom: '1px solid var(--console-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '13.5px', fontWeight: 700, color: '#FFFFFF' }}>
            <Terminal size={16} color="#38BDF8" />
            Interactive REST Endpoint Sandbox
          </div>

          <div style={{ display: 'flex', gap: 4 }}>
            {['curl', 'python', 'node'].map(lang => (
              <button
                key={lang}
                className={`sbtn ${codeLang === lang ? 'on' : ''}`}
                onClick={() => setCodeLang(lang)}
                style={{ fontSize: '10.5px', padding: '2px 7px', textTransform: 'uppercase' }}
              >
                {lang}
              </button>
            ))}
          </div>
        </div>

        {/* Endpoint Selector Pills */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {endpoints.map((ep, i) => (
            <button
              key={i}
              className={`sbtn ${sel.endpoint === ep.endpoint ? 'on' : ''}`}
              onClick={() => {
                setSel(ep);
                setExecutionResult(null);
              }}
              style={{ fontSize: '11px', fontFamily: 'var(--font-mono)' }}
            >
              <span style={{ fontWeight: 'bold', color: ep.method === 'POST' ? '#34D399' : '#38BDF8', marginRight: 4 }}>
                {ep.method}
              </span>
              {ep.endpoint.replace('/api/v1', '')}
            </button>
          ))}
        </div>

        {/* Request Header Bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span style={{ fontSize: '12.5px', fontWeight: 700, color: '#FFFFFF' }}>{sel.purpose}</span>
            <span style={{ fontSize: '11px', color: '#94A3B8', display: 'block' }}>{sel.description}</span>
          </div>

          <div style={{ display: 'flex', gap: 6 }}>
            <button className="sbtn" onClick={() => copy(generateSnippet())} style={{ fontSize: '11px' }}>
              {copied ? <CheckCircle size={11} color="#10B981" /> : <Copy size={11} />}
              {copied ? 'Copied' : 'Copy'}
            </button>
            <button
              className="btn btn-sm btn-primary"
              onClick={handleExecuteRequest}
              disabled={isExecuting}
              style={{ fontSize: '11px', padding: '4px 10px' }}
            >
              <Play size={11} /> {isExecuting ? 'Solving...' : 'Send Request'}
            </button>
          </div>
        </div>

        {/* Code Snippet Box */}
        <pre className="code-block" style={{ maxHeight: '140px' }}><code>{generateSnippet()}</code></pre>

        {/* Simulated Execution Response */}
        {executionResult && (
          <div style={{
            background: '#070A10',
            border: '1px solid #10B981',
            borderRadius: 'var(--radius-xs)',
            padding: '10px 12px',
            fontSize: '11px',
            fontFamily: 'var(--font-mono)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, color: '#34D399' }}>
              <span>HTTP/2 200 OK</span>
              <span>Latency: {executionResult.latencyMs}ms</span>
            </div>
            <pre style={{ color: '#A7F3D0', margin: 0, overflowX: 'auto' }}>
              {JSON.stringify(executionResult.data, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
