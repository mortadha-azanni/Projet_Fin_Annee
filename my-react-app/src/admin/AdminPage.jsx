import React from 'react';
import ETLControls from './components/ETLControls';
import ProgressFeed from './components/ProgressFeed';
import { useETL } from './hooks/useETL';
import './styles/admin.css';

export default function AdminPage() {
  const { status, logs, stats, handleStart, handlePause, handleResume, handleStop, handleClearLogs } = useETL();

  return (
    <div className="admin-layout">
      <aside className="sidebar">
        <div className="logo">⬡ Nexus</div>
        <div className="menu">
          <div className="menu-item active">ETL Dashboard</div>
        </div>
      </aside>
      
      <main className="admin-main">
        <header className="topbar">
          <h2>ETL Control Panel</h2>
        </header>

        <section className="dashboard-grid">
          <div className="controls-column">
            <ETLControls 
              status={status} 
              onStart={handleStart}
              onPause={handlePause}
              onResume={handleResume}
              onStop={handleStop}
            />

            <div className="card stats">
              <h3>Pipeline Stats</h3>
              <div className="stat-item">Products Scraped: {stats.productsScraped}</div>
              <div className="stat-item">Redis Cache Hits: {stats.redisCacheHits}</div>
            </div>
          </div>
          
          <ProgressFeed logs={logs} onClear={handleClearLogs} />
        </section>
      </main>
    </div>
  );
}