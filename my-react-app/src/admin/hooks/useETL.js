import { useState, useCallback } from 'react';

export function useETL() {
  const [status, setStatus] = useState('Idle');
  const [logs, setLogs] = useState([
    { id: 1, type: 'info', time: new Date().toLocaleTimeString(), message: 'System ready. Waiting for Start command.' }
  ]);
  const [stats, setStats] = useState({
    productsScraped: 0,
    redisCacheHits: 0
  });

  const addLog = (type, message) => {
    setLogs(prev => [...prev, {
      id: Date.now(),
      type,
      time: new Date().toLocaleTimeString(),
      message
    }]);
  };

  const handleStart = useCallback(() => {
    setStatus('Running');
    addLog('info', 'ETL Pipeline started. Reading URLs...');
    
    // Simulate some work
    setTimeout(() => {
       if(status !== 'Running') return;
       setStats(s => ({ ...s, productsScraped: 12 }));
       addLog('success', 'Scraped 12 products successfully.');
    }, 2000);
  }, [status]);

  const handlePause = useCallback(() => {
    setStatus('Paused');
    addLog('warning', 'ETL Pipeline paused. Buffer preserved.');
  }, []);

  const handleResume = useCallback(() => {
    setStatus('Running');
    addLog('info', 'ETL Pipeline resumed.');
  }, []);

  const handleStop = useCallback(() => {
    setStatus('Stopping');
    addLog('warning', 'Stop signal sent. Waiting for current product to finish...');
    
    setTimeout(() => {
      setStatus('Idle');
      addLog('info', 'ETL Pipeline forced stopped.');
    }, 1500);
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