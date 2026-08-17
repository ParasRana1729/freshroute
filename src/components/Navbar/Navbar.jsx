import React from 'react';
import { Calendar, Terminal } from 'lucide-react';

export function Navbar({ onRequestDemo, onScrollToConsole }) {
  return (
    <header className="navbar">
      <div className="navbar-inner">
        <div className="nav-brand" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
          <img src="/logo-icon.svg" alt="FreshRoute" />
          <span className="nav-brand-name">FreshRoute</span>
        </div>

        <nav>
          <ul className="nav-links">
            <li><a href="#console" className="nav-link">Live Operations</a></li>
            <li><a href="#how-it-works" className="nav-link">Architecture</a></li>
            <li><a href="#impact" className="nav-link">Impact Calculator</a></li>
            <li><a href="#comparison" className="nav-link">Model Benchmark</a></li>
          </ul>
        </nav>

        <div className="nav-actions">
          <button className="btn btn-ghost btn-sm" onClick={onScrollToConsole}>
            <Terminal size={13} />
            Console
          </button>
          <button className="btn btn-primary btn-sm" onClick={onRequestDemo}>
            <Calendar size={13} />
            Request Demo
          </button>
        </div>
      </div>
    </header>
  );
}
