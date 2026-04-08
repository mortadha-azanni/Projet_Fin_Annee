import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import MessageList from './components/MessageList';
import ChatInput from './components/ChatInput';
import { useChat } from './hooks/useChat';
import './styles/chat.css';

export default function ChatPage() {
  const { messages, sendMessage, isStreaming, resetChat } = useChat();
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => window.innerWidth >= 1024);

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setIsSidebarOpen(true);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);

  return (
    <div className="chat-layout">
      <Sidebar 
        onNewChat={resetChat} 
        isOpen={isSidebarOpen} 
        toggleSidebar={toggleSidebar} 
      />
      
      <main className="chat-main">
        <Topbar 
          toggleSidebar={toggleSidebar} 
          isSidebarOpen={isSidebarOpen} 
        />
        
        <MessageList 
          messages={messages} 
          isStreaming={isStreaming} 
        />
        
        <ChatInput 
          onSendMessage={sendMessage} 
          disabled={isStreaming} 
        />
      </main>
    </div>
  );
}