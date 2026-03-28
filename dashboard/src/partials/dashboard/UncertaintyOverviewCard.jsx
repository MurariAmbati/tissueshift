import { useRef, useEffect } from 'react';
import { Chart, RadarController, RadialLinearScale, PointElement, LineElement, Filler, Tooltip } from 'chart.js';
import { clinicalColors } from '../../charts/ChartjsConfig';
import { classNames } from '../../utils/Utils';

Chart.register(RadarController, RadialLinearScale, PointElement, LineElement, Filler, Tooltip);

export default function UncertaintyOverviewCard({ className = '' }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (chartRef.current) chartRef.current.destroy();
    const ctx = canvasRef.current.getContext('2d');
    chartRef.current = new Chart(ctx, {
      type: 'radar',
      data: {
        labels: ['Aleatoric', 'Epistemic', 'Calibration', 'Coverage', 'Sharpness'],
        datasets: [{
          label: 'Current Model',
          data: [0.85, 0.91, 0.93, 0.95, 0.88],
          borderColor: clinicalColors.violet.DEFAULT,
          backgroundColor: `${clinicalColors.violet.DEFAULT}20`,
          borderWidth: 2,
          pointRadius: 3,
          pointBackgroundColor: clinicalColors.violet.DEFAULT,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            min: 0, max: 1,
            ticks: { display: false, stepSize: 0.2 },
            grid: { color: '#e2e8f030' },
            pointLabels: { color: '#94a3b8', font: { size: 10 } },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.label}: ${(ctx.parsed.r * 100).toFixed(0)}%`,
            },
          },
        },
      },
    });
    return () => chartRef.current?.destroy();
  }, []);

  return (
    <div className={classNames('bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5', className)}>
      <header className="mb-2">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Uncertainty Quality</h2>
      </header>
      <div className="h-48">
        <canvas ref={canvasRef}></canvas>
      </div>
      <div className="mt-2 text-center">
        <span className="text-xs font-medium px-2 py-1 rounded-full bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400">Well-calibrated</span>
      </div>
    </div>
  );
}
