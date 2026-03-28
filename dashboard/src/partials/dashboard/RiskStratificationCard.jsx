import { useRef, useEffect } from 'react';
import { Chart, BarController, BarElement, LinearScale, CategoryScale, Tooltip } from 'chart.js';
import { classNames } from '../../utils/Utils';

Chart.register(BarController, BarElement, LinearScale, CategoryScale, Tooltip);

const data = {
  labels: ['0-0.2', '0.2-0.4', '0.4-0.6', '0.6-0.8', '0.8-1.0'],
  counts: [1847, 412, 167, 194, 227],
};

export default function RiskStratificationCard({ className = '' }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (chartRef.current) chartRef.current.destroy();
    const ctx = canvasRef.current.getContext('2d');
    chartRef.current = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.labels,
        datasets: [{
          data: data.counts,
          backgroundColor: ['#10b981', '#34d399', '#fbbf24', '#f97316', '#f43f5e'],
          borderRadius: 4,
          barPercentage: 0.7,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        scales: {
          x: {
            grid: { color: '#e2e8f020' },
            ticks: { color: '#94a3b8' },
          },
          y: {
            grid: { display: false },
            ticks: { color: '#94a3b8' },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.parsed.x} patients`,
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
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Risk Stratification</h2>
        <span className="text-xs text-gray-400 dark:text-gray-500">Risk Score Range</span>
      </header>
      <div className="h-64">
        <canvas ref={canvasRef}></canvas>
      </div>
      <div className="flex items-center justify-between mt-3 text-xs text-gray-500 dark:text-gray-400">
        <span>Low Risk ← </span>
        <span> → High Risk</span>
      </div>
    </div>
  );
}
