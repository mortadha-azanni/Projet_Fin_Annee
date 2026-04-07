import React from 'react';

export default function ProductCard({ product, index }) {
  // Stagger the animation based on index
  const delay = `${index * 120}ms`;

  return (
    <div className="product-card fade-up" style={{ animationDelay: delay }}>
      <div className="product-image-area">
        <span className="category-badge">{product.category}</span>
        <div className="img-placeholder">{product.image}</div>
      </div>
      
      <div className="product-details">
        <h3 className="product-name">{product.name}</h3>
        <div className="product-meta">
          <span className="rating">★ {product.rating}</span>
          <span className="price">{product.price}</span>
        </div>
      </div>
      
      <button className="ghost-btn product-cta">View Product →</button>
    </div>
  );
}