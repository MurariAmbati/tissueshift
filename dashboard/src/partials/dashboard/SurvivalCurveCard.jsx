import { useRef, useEffect } from 'react';
import { Chart, LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend, Filler } from 'chart.js';
import { subtypeColors } from '../../charts/ChartjsConfig';
import { classNames } from '../../utils/Utils';

Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend, Filler);

const months = Array.from({ length: 60 }, (_, i) => i);
const generateKM = (median) => months.map((m) => Math.exp(-0.693 * m / median));

const curves = [
  { label: 'Luminal A', data: generateKM(72), color: subtypeColors.luminal_a },
  { label: 'Luminal B', data: generateKM(54), color: subtypeColors.luminal_b },
  { label: 'HER2+', data: generateKM(42), color: subtypeColors.her2_enriched },
  { label: 'Basal-like', data: generateKM(30), color: subtypeColors.basal },
  { label: 'Normal-like', data: generateKM(60), color: subtypeColors.normal_like },
];

export default function SurvivalCurveCard({ className = '' }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (chartRef.current) chartRef.current.destroy();
    const ctx = canvasRef.current.getContext('2d');
    chartRef.current = new Chart(ctx, {
      type: 'line',
      data: {
        labels: months,
        datasets: curves.map((c) => ({
          label: c.label,
          data: c.data,
          borderColor: c.color,
          backgroundColor: `${c.color}10`,
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.3,
          fill: false,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            title: { display: true, text: 'Months', color: '#94a3b8' },
            ticks: { maxTicksLimit: 7, color: '#94a3b8' },
            grid: { display: false },
          },
          y: {
            title: { display: true, text: 'Survival Probability', color: '#94a3b8' },
            min: 0, max: 1,
            ticks: { color: '#94a3b8', callback: (v) => `${(v * 100).toFixed(0)}%` },
            grid: { color: '#e2e8f020' },
          },
        },
        plugins: {
          legend: {
            position: 'bottom',
            labels: { boxWidth: 12, usePointStyle: true, pointStyleWidth: 8, padding: 16 },
          },
          tooltip: {
            callbacks: {
              title: (ctx) => `Month ${ctx[0].label}`,
              label: (ctx) => `${ctx.dataset.label}: ${(ctx.parsed.y * 100).toFixed(1)}%`,
            },
          },
        },
        interaction: { mode: 'index', intersect: false },
      },
    });
    return () => chartRef.current?.destroy();
  }, []);

  return (
    <div className={classNames('bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5', className)}>
      <header className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Kaplan-Meier Survival Curves</h2>
        <span className="text-xs text-gray-400 dark:text-gray-500">5-year follow-up</span>
      </header>
      <div className="h-72">
        <canvas ref={canvasRef}></canvas>
      </div>
    </div>
  );
}
