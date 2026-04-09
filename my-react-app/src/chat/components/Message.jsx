import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ProductCard from './ProductCard';

export default function Message({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`message ${isUser ? 'user' : 'ai'}`}>
      <div className="message-content">
        {!isUser && message.mode === 'product_search' && (
          <div className="message-meta">
            <span className="mode-pill mode-product">Product Search</span>
          </div>
        )}

        <div className="bubble">
          {isUser ? (
            message.content
          ) : (
            <div className="markdown-prose">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
          {!isUser && message.streaming && <span className="cursor">▍</span>}
        </div>
        
        {message.products && message.products.length > 0 && (
          <div className="product-grid">
            {message.products.map((product, i) => (
              <ProductCard key={product.id} product={product} index={i} />
            ))}
          </div>
        )}
      </div>
      
      <div className="avatar">
        {isUser ? 'BJ' : 'AI'}
      </div>
    </div>
  );
}