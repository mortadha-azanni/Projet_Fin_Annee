import React, { useState } from 'react';
import { SUGGESTION_CHIPS } from '../constants/mockData';

export default function ChatInput({ onSendMessage, disabled }) {
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (disabled || !input.trim()) return;
    onSendMessage(input);
    setInput('');
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleChipClick = (suggestion) => {
    if (disabled) return;
    onSendMessage(suggestion);
  };

  return (
    <div className="chat-input-container">
      {!disabled && (
        <div className="suggestions">
          {SUGGESTION_CHIPS.map((chip, i) => (
             <button 
                key={i} 
                className="chip"
                onClick={() => handleChipClick(chip)}
                disabled={disabled}
              >
                {chip}
              </button>
          ))}
        </div>
      )}

      <div className={`input-box ${disabled ? 'disabled' : ''}`}>
        <textarea 
          placeholder="Type a message..." 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled}
          rows={1}
        />
        <button 
          className={`send-btn ${disabled ? 'streaming' : ''}`}
          onClick={handleSend}
          disabled={disabled || !input.trim()}
        >
          {disabled ? <div className="spinner"></div> : '↑'}
        </button>
      </div>
      <div className="input-hint">
        Press Enter to send · Shift+Enter for new line
      </div>
    </div>
  );
}