import React from 'react';

export default function ProductCard({ product, index }) {
  // Stagger the animation based on index
  const delay = `${index * 120}ms`;

  return (
    <div className="product-card fade-up" style={{ animationDelay: delay }}>
      <div className="product-image-area">
        <span className="category-badge">{product.category}</span>
        {product.urlimg ? (
          <img 
            src={product.urlimg} 
            alt={product.name} 
            style={{ width: '100%', height: '100%', objectFit: 'contain' }} 
          />
        ) : (
          <div className="img-placeholder">📦</div>
        )}
      </div>
      
      <div className="product-details">
        <h3 className="product-name" title={product.name}>
          {product.name.length > 50 ? product.name.substring(0, 48) + '...' : product.name}
        </h3>
        <div className="product-meta">
          <span className="rating">★ {product.rating}</span>
          <span className="price">{product.price}</span>
        </div>
      </div>
      
      <a 
        href={product.urllink} 
        target="_blank" 
        rel="noopener noreferrer" 
        className="ghost-btn product-cta" 
        style={{ display: 'block', textAlign: 'center', textDecoration: 'none' }}
      >
        View Product →
      </a>
    </div>
  );
}