import { useState, useCallback, useRef } from 'react';
import { WELCOME_MESSAGE, MOCK_PRODUCTS } from '../constants/mockData';

export function useChat() {
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [isStreaming, setIsStreaming] = useState(false);
  const streamRef = useRef(null);

  const resetChat = useCallback(() => {
    if (streamRef.current) clearInterval(streamRef.current);
    setIsStreaming(false);
    setMessages([{ ...WELCOME_MESSAGE, id: Date.now() }]);
  }, []);

  const sendMessage = useCallback((query) => {
    if (!query.trim() || isStreaming) return;

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: query,
      streaming: false,
      products: []
    };

    setMessages(prev => [...prev, userMessage]);
    setIsStreaming(true);

    const aiMessageId = Date.now() + 1;
    
    // Simulate Gateway latency
    setTimeout(() => {
      setMessages(prev => [...prev, {
        id: aiMessageId,
        role: 'assistant',
        content: '',
        streaming: true,
        products: []
      }]);

      const mockResponse = `Here's what I found for "${query}". I've gathered some great options tailored to your request. Let me know what you think!`;
      let currentLength = 0;
      
      // Simulate token streaming
      streamRef.current = setInterval(() => {
        currentLength += 2;
        
        if (currentLength >= mockResponse.length) {
          clearInterval(streamRef.current);
          
          setMessages(prev => prev.map(msg => 
            msg.id === aiMessageId ? { ...msg, content: mockResponse } : msg
          ));

          // Simulate product retrieval delay
          setTimeout(() => {
            setMessages(prev => prev.map(msg => 
              msg.id === aiMessageId 
                ? { ...msg, streaming: false, products: MOCK_PRODUCTS } 
                : msg
            ));
            setIsStreaming(false);
          }, 300);

        } else {
          setMessages(prev => prev.map(msg => 
            msg.id === aiMessageId 
              ? { ...msg, content: mockResponse.substring(0, currentLength) } 
              : msg
          ));
        }
      }, 50);

    }, 400);

  }, [isStreaming]);

  return {
    messages,
    sendMessage,
    isStreaming,
    resetChat
  };
}