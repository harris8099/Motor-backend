import React from 'react';
import './SkeletonCard.css';

function SkeletonCard() {
  return (
    <div className="skeleton-card">
      <div className="skeleton-header">
        <div className="skeleton-icon"></div>
        <div className="skeleton-title"></div>
      </div>
      <div className="skeleton-value"></div>
      <div className="skeleton-unit"></div>
    </div>
  );
}

export default SkeletonCard;
