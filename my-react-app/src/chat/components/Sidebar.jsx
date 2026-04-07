import React from 'react';
import { MOCK_HISTORY } from '../constants/mockData';

export default function Sidebar({ onNewChat, isOpen, toggleSidebar }) {
  return (
    <aside className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
      <div className="sidebar-header">
        <div className="logo">⬡ Nexus</div>
        <button className="close-sidebar lg:hidden" onClick={toggleSidebar}>✕</button>
      </div>
      
      <button className="new-chat" onClick={onNewChat}>
        New Chat
      </button>
      
      <div className="history">
        {MOCK_HISTORY.map((item, i) => (
          <div key={item.id} className={`history-item ${i === 0 ? 'active' : ''}`}>
            <span className="icon">💬</span>
            <div className="history-text">
              <span className="history-title">{item.title}</span>
              <span className="history-time">{item.timestamp}</span>
            </div>
          </div>
        ))}
      </div>
      
      <div className="user-info">
        <div className="avatar">BJ</div>
        <div>
          <div className="username">Boj</div>
          <div className="plan">Free Plan</div>
        </div>
      </div>
    </aside>
  );
}