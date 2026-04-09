import { useState, useCallback, useEffect, useRef } from 'react';

const API_BASE = 'http://localhost:8000';
const WS_BASE = 'ws://localhost:8000/websocket_progress';

export function useETL() {
  const [status, setStatus] = useState('Idle');
  const [logs, setLogs] = useState([
    { id: 1, type: 'info', time: new Date().toLocaleTimeString(), message: 'System ready. Waiting for Start command.' }
  ]);
  const [stats, setStats] = useState({
    productsScraped: 0,
    productsInDb: 0,
    redisCacheHits: 0
  });

  const ws = useRef(null);

  const applyServerPayload = useCallback((data) => {
    const serverState = String(data?.state || 'idle').toLowerCase();
    setStatus(serverState.charAt(0).toUpperCase() + serverState.slice(1));

    if (typeof data?.urls_scraped === 'number' && Number.isFinite(data.urls_scraped)) {
      setStats(prev => ({
        ...prev,
        productsScraped: Math.max(0, data.urls_scraped)
      }));
    }
  }, []);

  const addLog = (type, message) => {
    setLogs(prev => [...prev, {
      id: Date.now(),
      type,
      time: new Date().toLocaleTimeString(),
      message
    }]);
  };

  const loadDbCount = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/scrape/db-count`);
      const data = await res.json();
      if (typeof data?.products_in_db === 'number' && Number.isFinite(data.products_in_db)) {
        setStats(prev => ({
          ...prev,
          productsInDb: Math.max(0, data.products_in_db)
        }));
      }
    } catch {
      // Keep current value if count fetch fails.
    }
  }, []);

  // Setup initial status + WebSocket connection
  useEffect(() => {
    let cancelled = false;

    const loadInitialStatus = async () => {
      try {
        const res = await fetch(`${API_BASE}/scrape/status`);
        const data = await res.json();
        if (!cancelled) {
          applyServerPayload(data);
          await loadDbCount();
        }
      } catch (err) {
        addLog('warning', 'Failed to load initial pipeline status.');
      }
    };

    loadInitialStatus();

    ws.current = new WebSocket(WS_BASE);

    ws.current.onopen = () => {
      addLog('success', 'Connected to Scraper background service.');
    };

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        applyServerPayload(data);
        const serverState = String(data?.state || 'idle').toLowerCase();
        
        if (data.message) {
          const logType = serverState === 'error' ? 'error' : 'info';
          addLog(logType, data.message);
        }

        if (serverState === 'completed' || serverState === 'idle') {
          loadDbCount();
        }
      } catch (err) {
        console.error("Failed to parse websocket message", err);
      }
    };

    ws.current.onerror = () => {
      addLog('error', 'WebSocket connection error.');
    };

    ws.current.onclose = () => {
      addLog('warning', 'Disconnected from background service.');
    };

    return () => {
      cancelled = true;
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [applyServerPayload, loadDbCount]);

  const handleStart = useCallback(async () => {
    addLog('info', 'Sending Launch command...');
    try {
      const res = await fetch(`${API_BASE}/scrape/launch`, { method: 'POST' });
      const data = await res.json();
      if (data.state === 'error') addLog('error', data.message);
      await loadDbCount();
    } catch (err) {
      addLog('error', `Failed to start: ${err.message}`);
    }
  }, [loadDbCount]);

  const handlePause = useCallback(async () => {
    addLog('info', 'Sending Pause command...');
    try {
      const res = await fetch(`${API_BASE}/scrape/pause`, { method: 'POST' });
      const data = await res.json();
      if (data.state === 'error') addLog('error', data.message);
    } catch (err) {
      addLog('error', `Failed to pause: ${err.message}`);
    }
  }, []);

  const handleResume = useCallback(async () => {
    addLog('info', 'Sending Resume command...');
    try {
      const res = await fetch(`${API_BASE}/scrape/resume`, { method: 'POST' });
      const data = await res.json();
      if (data.state === 'error') addLog('error', data.message);
    } catch (err) {
      addLog('error', `Failed to resume: ${err.message}`);
    }
  }, []);

  const handleStop = useCallback(async () => {
    addLog('info', 'Sending Force Stop command...');
    try {
      const res = await fetch(`${API_BASE}/scrape/stop`, { method: 'POST' });
      const data = await res.json();
      if (data.state === 'error') addLog('error', data.message);
      await loadDbCount();
    } catch (err) {
      addLog('error', `Failed to stop: ${err.message}`);
    }
  }, [loadDbCount]);

  const handleClearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  return {
    status,
    logs,
    stats,
    handleStart,
    handlePause,
    handleResume,
    handleStop,
    handleClearLogs
  };
}