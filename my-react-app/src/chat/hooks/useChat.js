import { useState, useCallback, useRef, useEffect } from 'react';
import { WELCOME_MESSAGE, MOCK_PRODUCTS } from '../constants/mockData';

// Format the ranker results into UI product cards
const mapProducts = (results) => {
  if (!Array.isArray(results)) return [];
  return results.map((res, i) => {
    const doc = res.document || res || {};
    return {
      id: doc.id || `product-${i}`,
      name: doc.description || doc.title || doc.name || 'Found Item',
      category: doc.category_name || 'PRODUCT',
      price: doc.price ? `${doc.price} DT` : 'Check Site',
      rating: doc.rating || (4 + Math.random()).toFixed(1), // Mock rating if missing
      urlimg: doc.urlimg || null,
      urllink: doc.urllink || '#'
    };
  });
};

export function useChat() {
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [isStreaming, setIsStreaming] = useState(false);
  
  // Track all async operations for cleanup
  const streamRef = useRef(null);
  const timersRef = useRef(new Set());

  const clearAllAsync = useCallback(() => {
    if (streamRef.current) {
      if (typeof streamRef.current.close === 'function') {
        streamRef.current.close();
      } else {
        clearInterval(streamRef.current);
      }
      streamRef.current = null;
    }
    timersRef.current.forEach(clearTimeout);
    timersRef.current.clear();
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return clearAllAsync;
  }, [clearAllAsync]);

  const resetChat = useCallback(() => {
    clearAllAsync();
    setIsStreaming(false);
    setMessages([{ ...WELCOME_MESSAGE, id: Date.now() }]);
  }, [clearAllAsync]);

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
    
    // --- Real Transport Layer Start ---
    setMessages(prev => [...prev, {
      id: aiMessageId,
      role: 'assistant',
      content: 'Starting search...',
      streaming: true,
      products: []
    }]);

    fetch(`${import.meta.env.VITE_API_URL}/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query: query })
    }).then(res => res.json())
      .then(data => {
        const taskId = data.task_id;
        if (!taskId) {
          throw new Error('No task ID returned');
        }

        const ws = new WebSocket(`${import.meta.env.VITE_WS_URL}/ws/status/${taskId}`);
        streamRef.current = ws;

        ws.onmessage = (event) => {
          const resp = JSON.parse(event.data);
          let content = resp.status;

          if (resp.state === 'SUCCESS') {
            content = resp.final_response || 'Search Complete';
            setMessages(prev => prev.map(msg => 
              msg.id === aiMessageId 
                ? { ...msg, streaming: false, content: content, products: mapProducts(resp.results) || [] } 
                : msg
            ));
            setIsStreaming(false);
            ws.close();
            streamRef.current = null;
          } else if (resp.state === 'FAILURE') {
            setMessages(prev => prev.map(msg => 
              msg.id === aiMessageId ? { ...msg, content: 'Error: ' + resp.error, streaming: false } : msg
            ));
            setIsStreaming(false);
            ws.close();
            streamRef.current = null;
          } else {
            setMessages(prev => prev.map(msg => 
              msg.id === aiMessageId ? { ...msg, content: `*${content}...*` } : msg
            ));
          }
        };

        ws.onerror = (error) => {
          console.error("WebSocket error:", error);
          setMessages(prev => prev.map(msg => 
            msg.id === aiMessageId ? { ...msg, content: 'WebSocket connection error.', streaming: false } : msg
          ));
          setIsStreaming(false);
        };
      })
      .catch(err => {
        setMessages(prev => prev.map(msg => 
          msg.id === aiMessageId ? { ...msg, content: 'Error starting search.', streaming: false } : msg
        ));
        setIsStreaming(false);
      });
    // --- Real Transport Layer End ---

  }, [isStreaming]);

  return {
    messages,
    sendMessage,
    isStreaming,
    resetChat
  };
}