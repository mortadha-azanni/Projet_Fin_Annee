import React from 'react';
import StatusBadge from './StatusBadge';

export default function ETLControls({ status, onStart, onPause, onResume, onStop }) {
  return (
    <div className="card controls-panel">
      <h3>Controls</h3>
      <StatusBadge status={status} />
      
      <div className="btn-group">
        {(status === 'Idle' || status === 'Completed' || status === 'Error') && (
          <button className="btn-start" onClick={onStart}>Start Pipeline</button>
        )}
        
        {status === 'Running' && (
          <button className="btn-pause" onClick={onPause}>Pause</button>
        )}
        
        {status === 'Paused' && (
          <button className="btn-start" onClick={onResume}>Resume</button>
        )}
        
        {(status === 'Running' || status === 'Paused') && (
          <button className="btn-stop" onClick={onStop}>Force Stop</button>
        )}
      </div>
    </div>
  );
}