import { useState, useEffect } from 'react';

/**
 * Mini sparkline chart rendered inline — perfect for KPI cards
 * to show trend data without full Chart.js overhead.
 */
export default function Sparkline({ data = [], color = '#8b5cf6', width = 80, height = 28, className = '' }) {
  if (!data.length) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const step = width / (data.length - 1);

  const points = data.map((v, i) => {
    const x = i * step;
    const y = height - ((v - min) / range) * (height - 4) - 2;
    return `${x},${y}`;
  });

  const pathD = points.reduce((acc, pt, i) => acc + (i === 0 ? `M${pt}` : ` L${pt}`), '');

  // Gradient fill
  const fillPoints = [...points, `${width},${height}`, `0,${height}`];
  const fillD = fillPoints.reduce((acc, pt, i) => acc + (i === 0 ? `M${pt}` : ` L${pt}`), '') + ' Z';

  return (
    <svg width={width} height={height} className={className} viewBox={`0 0 ${width} ${height}`}>
      <path d={fillD} fill={color} opacity="0.1" />
      <path d={pathD} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      {/* Glow dot on last point */}
      <circle cx={data.length > 1 ? (data.length - 1) * step : 0} cy={height - ((data[data.length - 1] - min) / range) * (height - 4) - 2} r="2.5" fill={color} />
    </svg>
  );
}
