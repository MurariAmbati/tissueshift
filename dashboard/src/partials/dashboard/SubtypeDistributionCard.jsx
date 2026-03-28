import { useRef, useEffect } from 'react';
import { Chart, DoughnutController, ArcElement, Tooltip, Legend } from 'chart.js';
import { subtypeColors } from '../../charts/ChartjsConfig';
import { classNames } from '../../utils/Utils';

Chart.register(DoughnutController, ArcElement, Tooltip, Legend);

const data = {
  labels: ['Luminal A', 'Luminal B', 'HER2+', 'Basal-like', 'Normal-like', 'Claudin-low', 'DCIS'],
  values: [842, 524, 387, 312, 198, 156, 428],
};

export default function SubtypeDistributionCard({ className = '' }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (chartRef.current) chartRef.current.destroy();
    const ctx = canvasRef.current.getContext('2d');
    chartRef.current = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: data.labels,
        datasets: [{
          data: data.values,
          backgroundColor: Object.values(subtypeColors),
          borderWidth: 0,
          hoverBorderColor: '#fff',
        }],
      },
      options: {
        cutout: '70%',
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.label}: ${ctx.parsed} (${((ctx.parsed / data.values.reduce((a, b) => a + b, 0)) * 100).toFixed(1)}%)`,
            },
          },
        },
        animation: { animateRotate: true },
      },
    });
    return () => chartRef.current?.destroy();
  }, []);

  const total = data.values.reduce((a, b) => a + b, 0);

  return (
    <div className={classNames('bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5', className)}>
      <header className="mb-4">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Subtype Distribution</h2>
      </header>
      <div className="flex items-center justify-center mb-4">
        <div className="relative w-44 h-44">
          <canvas ref={canvasRef}></canvas>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-800 dark:text-gray-100">{total.toLocaleString()}</div>
              <div className="text-xs text-gray-500">Total</div>
            </div>
          </div>
        </div>
      </div>
      <ul className="space-y-1">
        {data.labels.map((label, i) => (
          <li key={label} className="flex items-center justify-between text-sm">
            <div className="flex items-center">
              <span className="w-2.5 h-2.5 rounded-full mr-2 shrink-0" style={{ backgroundColor: Object.values(subtypeColors)[i] }} />
              <span className="text-gray-600 dark:text-gray-300">{label}</span>
            </div>
            <span className="font-medium text-gray-800 dark:text-gray-100">{((data.values[i] / total) * 100).toFixed(1)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
