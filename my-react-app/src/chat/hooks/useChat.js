import { useState, useCallback, useRef, useEffect } from 'react';
import { WELCOME_MESSAGE } from '../constants/mockData';

const API_BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const WS_BASE = import.meta.env.VITE_WS_URL || API_BASE.replace(/^http/i, 'ws');
const PRODUCT_INTENT_PATTERN = /(buy|purchase|recommend|suggest|looking for|need a|need an|find me|search|best|budget|price|laptop|pc|computer|phone|smartphone|tablet|headset|headphone|earbuds|keyboard|mouse|monitor|printer|camera|ssd|ram|gpu|iphone|samsung|xiaomi|macbook|lenovo|hp|asus|dell|portable|ordinateur|pc portable|t[eé]l[eé]phone|prix|produit|article)/i;

const classifyIntent = async (message) => {
  try {
    const res = await fetch(`${API_BASE}/intent/classify`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message })
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data?.detail || `Intent classification failed (${res.status})`);
    }

    return data?.intent === 'product_search';
  } catch {
    // Fallback keeps chat usable even if classifier endpoint is unavailable.
    return PRODUCT_INTENT_PATTERN.test(message);
  }
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

    const trimmedQuery = query.trim();

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: trimmedQuery,
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
      content: 'Analyzing your request...',
      streaming: true,
      mode: 'normal_chat',
      products: []
    }]);

    classifyIntent(trimmedQuery).then((isProductIntent) => {
      setMessages(prev => prev.map(msg =>
        msg.id === aiMessageId
          ? {
              ...msg,
              mode: isProductIntent ? 'product_search' : 'normal_chat',
              content: isProductIntent ? 'Starting product search...' : 'Thinking...'
            }
          : msg
      ));

      if (!isProductIntent) {
        fetch(`${API_BASE}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ message: trimmedQuery })
        }).then(async (res) => {
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            const errorDetail = data?.detail || data?.error || `Chat request failed (${res.status})`;
            throw new Error(errorDetail);
          }
          return data;
        }).then((data) => {
          setMessages(prev => prev.map(msg =>
            msg.id === aiMessageId
              ? { ...msg, content: data.response || 'Sorry, I could not generate a response.', streaming: false, products: [] }
              : msg
          ));
          setIsStreaming(false);
        }).catch((err) => {
          const errorMessage = err?.message || 'Error generating response.';
          setMessages(prev => prev.map(msg =>
            msg.id === aiMessageId
              ? { ...msg, content: `Error: ${errorMessage}`, streaming: false, products: [] }
              : msg
          ));
          setIsStreaming(false);
        });

        return;
      }

      fetch(`${API_BASE}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: trimmedQuery })
      }).then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          const errorDetail = data?.detail || data?.error || `Search request failed (${res.status})`;
          throw new Error(errorDetail);
        }
        return data;
      })
        .then(data => {
          const taskId = data.task_id;
          if (!taskId) {
            throw new Error('No task ID returned');
          }

          const ws = new WebSocket(`${WS_BASE}/ws/status/${taskId}`);
          let settled = false;
          streamRef.current = ws;

          ws.onmessage = (event) => {
            const resp = JSON.parse(event.data);
            let content = resp.status;

            if (resp.state === 'SUCCESS') {
              content = resp.final_response || 'Search Complete';
              settled = true;
              setMessages(prev => prev.map(msg => 
                msg.id === aiMessageId 
                  ? { ...msg, streaming: false, content: content, products: mapProducts(resp.results) || [] } 
                  : msg
              ));
              setIsStreaming(false);
              ws.close();
              streamRef.current = null;
            } else if (resp.state === 'FAILURE') {
              settled = true;
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
            settled = true;
            setMessages(prev => prev.map(msg => 
              msg.id === aiMessageId ? { ...msg, content: 'WebSocket connection error.', streaming: false } : msg
            ));
            setIsStreaming(false);
          };

          ws.onclose = () => {
            if (!settled) {
              setMessages(prev => prev.map(msg =>
                msg.id === aiMessageId
                  ? { ...msg, content: 'Search connection closed before completion. Please retry.', streaming: false }
                  : msg
              ));
              setIsStreaming(false);
            }
            if (streamRef.current === ws) {
              streamRef.current = null;
            }
          };
        })
        .catch(err => {
          const errorMessage = err?.message || 'Error starting search.';
          setMessages(prev => prev.map(message => 
            message.id === aiMessageId ? { ...message, content: `Error starting search: ${errorMessage}`, streaming: false } : message
          ));
          setIsStreaming(false);
        });
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