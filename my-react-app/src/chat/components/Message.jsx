import React from 'react';
import ProductCard from './ProductCard';

export default function Message({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`message ${isUser ? 'user' : 'ai'}`}>
      <div className="message-content">
        <div className="bubble">
          {message.content}
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