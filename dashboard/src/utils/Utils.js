// Utility helpers

export const formatNumber = (n) =>
  Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(n);

export const formatPercent = (n) =>
  `${(n * 100).toFixed(1)}%`;

export const formatDate = (d) =>
  new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });

export const classNames = (...classes) => classes.filter(Boolean).join(' ');

export const riskLevel = (score) => {
  if (score < 0.3) return 'low';
  if (score < 0.6) return 'moderate';
  return 'high';
};

export const riskColor = (level) => ({
  low:      'emerald',
  moderate: 'amber',
  high:     'rose',
}[level] || 'gray');

export const confidenceLevel = (score) => {
  if (score >= 0.85) return { label: 'High', color: 'emerald' };
  if (score >= 0.6)  return { label: 'Moderate', color: 'amber' };
  return { label: 'Low', color: 'rose' };
};
