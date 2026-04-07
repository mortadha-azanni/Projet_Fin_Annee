import React from 'react';

export default function StatusBadge({ status }) {
  // Map PRD status colors to CSS classes
  const getBadgeClass = () => {
    switch (status.toLowerCase()) {
      case 'running': return 'green';
      case 'paused': return 'amber';
      case 'stopping': return 'amber';
      case 'error': return 'red';
      case 'completed': return 'teal';
      default: return 'idle'; // gray
    }
  };

  return (
    <div className={`status-badge ${getBadgeClass()}`}>
      STATUS: {status.toUpperCase()}
    </div>
  );
}