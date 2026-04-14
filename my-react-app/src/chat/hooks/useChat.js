import { useState, useCallback, useRef, useEffect } from 'react';
import { WELCOME_MESSAGE, MOCK_PRODUCTS } from '../constants/mockData';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

const SMALL_TALK_PHRASES = new Set([
  'hi',
  'hello',
  'hey',
  'yo',
  'bonjour',
  'salut',
  'thanks',
  'thank you',
  'sup',
  'what now',
  'now what'
]);

const normalizeQueryText = (query) => {
  const punctuation = new Set([',', '.', '!', '?', ';', ':', '-', '_', '[', ']', '{', '}', '(', ')', "'", '"']);
  const lowered = query.trim().toLowerCase();
  const cleaned = [...lowered].filter((ch) => !punctuation.has(ch)).join('');
  return cleaned.split(' ').filter(Boolean).join(' ');
};

const isLikelySearchQuery = (query) => {
  const normalized = normalizeQueryText(query);
  if (normalized.length < 3) return false;
  if (SMALL_TALK_PHRASES.has(normalized)) return false;
  return true;
};

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

    if (!isLikelySearchQuery(query)) {
      const userMessage = {
        id: Date.now(),
        role: 'user',
        content: query,
        streaming: false,
        products: []
      };

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'I can help with product searches. Tell me what item, brand, or budget you want.',
        streaming: false,
        products: []
      };

      setMessages(prev => [...prev, userMessage, assistantMessage]);
      return;
    }

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

    (async () => {
      try {
        const res = await fetch(`${API_URL}/search`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ query })
        });

        const payload = await res.json().catch(() => null);
        if (!res.ok) {
          const detail = payload?.detail || payload?.message || `Search request failed (${res.status})`;
          throw new Error(detail);
        }

        const taskId = payload?.task_id;
        if (!taskId) {
          throw new Error('No task ID returned');
        }

        const ws = new WebSocket(`${WS_URL}/ws/status/${taskId}`);
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
          console.error('WebSocket error:', error);
          setMessages(prev => prev.map(msg => 
            msg.id === aiMessageId ? { ...msg, content: 'WebSocket connection error.', streaming: false } : msg
          ));
          setIsStreaming(false);
          streamRef.current = null;
        };
      } catch (err) {
        setMessages(prev => prev.map(msg => 
          msg.id === aiMessageId ? { ...msg, content: `Error starting search: ${err.message}`, streaming: false } : msg
        ));
        setIsStreaming(false);
        streamRef.current = null;
      }
    })();
    // --- Real Transport Layer End ---

  }, [isStreaming]);

  return {
    messages,
    sendMessage,
    isStreaming,
    resetChat
  };
}