import React, { useRef, useEffect } from 'react';

export default function ProgressFeed({ logs, onClear }) {
  const feedRef = useRef(null);

  useEffect(() => {
    feedRef.current?.scrollTo({
      top: feedRef.current.scrollHeight,
      behavior: 'smooth'
    });
  }, [logs]);

  return (
    <div className="card progress-feed">
      <div className="feed-header">
        <h3>Live Progress</h3>
        <button className="ghost-btn" onClick={onClear}>Clear Feed</button>
      </div>
      
      <div className="log-area" ref={feedRef}>
        {logs.map((log) => (
          <div key={log.id} className={`log-line log-${log.type}`}>
            <span className="log-time">[{log.time}]</span> {log.message}
          </div>
        ))}
      </div>
    </div>
  );
}