import { useRef, useEffect } from 'react';
import { Chart, BarController, BarElement, LinearScale, CategoryScale, Tooltip, Legend } from 'chart.js';
import { clinicalColors } from '../../charts/ChartjsConfig';
import { classNames } from '../../utils/Utils';

Chart.register(BarController, BarElement, LinearScale, CategoryScale, Tooltip, Legend);

const metrics = {
  labels: ['Accuracy', 'F1-Score', 'AUROC', 'AUPRC', 'Calibration'],
  current: [0.943, 0.921, 0.968, 0.952, 0.934],
  previous: [0.918, 0.896, 0.951, 0.937, 0.911],
};

export default function ModelPerformanceCard({ className = '' }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (chartRef.current) chartRef.current.destroy();
    const ctx = canvasRef.current.getContext('2d');
    chartRef.current = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: metrics.labels,
        datasets: [
          {
            label: 'Current v2.1',
            data: metrics.current,
            backgroundColor: clinicalColors.violet.DEFAULT,
            borderRadius: 4,
            barPercentage: 0.6,
          },
          {
            label: 'Previous v2.0',
            data: metrics.previous,
            backgroundColor: `${clinicalColors.violet.DEFAULT}40`,
            borderRadius: 4,
            barPercentage: 0.6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: '#94a3b8' },
          },
          y: {
            min: 0.8, max: 1,
            ticks: { color: '#94a3b8', callback: (v) => `${(v * 100).toFixed(0)}%` },
            grid: { color: '#e2e8f020' },
          },
        },
        plugins: {
          legend: {
            position: 'bottom',
            labels: { boxWidth: 12, usePointStyle: true, padding: 16 },
          },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${(ctx.parsed.y * 100).toFixed(1)}%`,
            },
          },
        },
      },
    });
    return () => chartRef.current?.destroy();
  }, []);

  return (
    <div className={classNames('bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5', className)}>
      <header className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Model Performance</h2>
        <span className="text-xs font-medium px-2 py-1 rounded-full bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400">+2.5% avg</span>
      </header>
      <div className="h-64">
        <canvas ref={canvasRef}></canvas>
      </div>
    </div>
  );
}
