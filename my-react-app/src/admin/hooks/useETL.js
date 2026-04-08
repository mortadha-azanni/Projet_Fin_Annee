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
    redisCacheHits: 0
  });

  const ws = useRef(null);

  const addLog = (type, message) => {
    setLogs(prev => [...prev, {
      id: Date.now(),
      type,
      time: new Date().toLocaleTimeString(),
      message
    }]);
  };

  // Setup WebSocket connection
  useEffect(() => {
    ws.current = new WebSocket(WS_BASE);

    ws.current.onopen = () => {
      addLog('success', 'Connected to Scraper background service.');
    };

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Update Local State from Backend Model
        const serverState = data.state || 'idle';
        // Map backend state strings to frontend labels (running -> Running)
        setStatus(serverState.charAt(0).toUpperCase() + serverState.slice(1));
        
        if (data.message) {
          const logType = serverState === 'error' ? 'error' : 'info';
          addLog(logType, data.message);
        }

        if (data.urls_scraped !== undefined) {
          setStats(prev => ({
            ...prev,
            productsScraped: data.urls_scraped
          }));
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
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  const handleStart = useCallback(async () => {
    addLog('info', 'Sending Launch command...');
    try {
      const res = await fetch(`${API_BASE}/scrape/launch`, { method: 'POST' });
      const data = await res.json();
      if (data.state === 'error') addLog('error', data.message);
    } catch (err) {
      addLog('error', `Failed to start: ${err.message}`);
    }
  }, []);

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
    } catch (err) {
      addLog('error', `Failed to stop: ${err.message}`);
    }
  }, []);

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