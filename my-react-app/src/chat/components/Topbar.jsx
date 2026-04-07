import React from 'react';

export default function Topbar({ toggleSidebar, isSidebarOpen }) {
  return (
    <header className="topbar">
      {!isSidebarOpen && (
        <button className="hamburger" onClick={toggleSidebar}>☰</button>
      )}
      
      <div className="status">
        <span className="dot"></span> AI Shopping Assistant
      </div>
      
      <div className="topbar-actions">
        <button className="ghost-btn">Share</button>
        <button className="ghost-btn icon-btn">⋯</button>
      </div>
    </header>
  );
}