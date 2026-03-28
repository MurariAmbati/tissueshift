import { Chart, Tooltip, Legend } from 'chart.js';

Chart.register(Tooltip, Legend);

// Clinical color scheme
Chart.defaults.font.family = "'Inter', 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif";
Chart.defaults.font.weight = '500';
Chart.defaults.color = '#94a3b8';
Chart.defaults.scale.grid.color = '#e2e8f0';
Chart.defaults.plugins.tooltip.titleColor = '#1e293b';
Chart.defaults.plugins.tooltip.bodyColor = '#475569';
Chart.defaults.plugins.tooltip.backgroundColor = '#fff';
Chart.defaults.plugins.tooltip.borderWidth = 1;
Chart.defaults.plugins.tooltip.borderColor = '#e2e8f0';
Chart.defaults.plugins.tooltip.displayColors = false;
Chart.defaults.plugins.tooltip.mode = 'nearest';
Chart.defaults.plugins.tooltip.intersect = false;
Chart.defaults.plugins.tooltip.position = 'nearest';
Chart.defaults.plugins.tooltip.caretSize = 0;
Chart.defaults.plugins.tooltip.caretPadding = 20;
Chart.defaults.plugins.tooltip.cornerRadius = 8;
Chart.defaults.plugins.tooltip.padding = 8;

// Clinical palette
export const clinicalColors = {
  violet:   { DEFAULT: '#8b5cf6', light: '#c4b5fd', dark: '#6d28d9' },
  teal:     { DEFAULT: '#14b8a6', light: '#5eead4', dark: '#0d9488' },
  rose:     { DEFAULT: '#f43f5e', light: '#fda4af', dark: '#e11d48' },
  amber:    { DEFAULT: '#f59e0b', light: '#fcd34d', dark: '#d97706' },
  emerald:  { DEFAULT: '#10b981', light: '#6ee7b7', dark: '#059669' },
  sky:      { DEFAULT: '#0ea5e9', light: '#7dd3fc', dark: '#0284c7' },
  indigo:   { DEFAULT: '#6366f1', light: '#a5b4fc', dark: '#4f46e5' },
};

// Subtype colors (consistent across all charts)
export const subtypeColors = {
  luminal_a:     '#10b981',
  luminal_b:     '#0ea5e9',
  her2_enriched: '#f59e0b',
  basal:         '#f43f5e',
  normal_like:   '#8b5cf6',
  claudin_low:   '#6366f1',
  dcis:          '#94a3b8',
};
