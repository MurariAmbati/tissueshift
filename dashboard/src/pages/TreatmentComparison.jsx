import { useState, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Chart, BarController, BarElement, LinearScale, CategoryScale, Tooltip, Legend } from 'chart.js';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import { clinicalColors } from '../charts/ChartjsConfig';
import { classNames } from '../utils/Utils';

Chart.register(BarController, BarElement, LinearScale, CategoryScale, Tooltip, Legend);

const regimens = [
  { name: 'AC-T', survival12: 0.89, survival24: 0.72, survival60: 0.48, pCR: 0.23, toxicityGrade3: 0.34, cost: '$18,400' },
  { name: 'TCH', survival12: 0.91, survival24: 0.76, survival60: 0.52, pCR: 0.31, toxicityGrade3: 0.28, cost: '$24,200' },
  { name: 'Pembrolizumab + Chemo', survival12: 0.93, survival24: 0.79, survival60: 0.57, pCR: 0.42, toxicityGrade3: 0.31, cost: '$42,000' },
  { name: 'Olaparib (BRCA+)', survival12: 0.87, survival24: 0.68, survival60: 0.44, pCR: 0.18, toxicityGrade3: 0.19, cost: '$54,000' },
  { name: 'Capecitabine', survival12: 0.82, survival24: 0.61, survival60: 0.38, pCR: 0.12, toxicityGrade3: 0.22, cost: '$8,200' },
];

export default function TreatmentComparison() {
  const { id } = useParams();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (chartRef.current) chartRef.current.destroy();
    const ctx = canvasRef.current.getContext('2d');
    chartRef.current = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: regimens.map((r) => r.name),
        datasets: [
          { label: '1-Year', data: regimens.map((r) => r.survival12), backgroundColor: clinicalColors.violet.DEFAULT, borderRadius: 4 },
          { label: '2-Year', data: regimens.map((r) => r.survival24), backgroundColor: clinicalColors.teal.DEFAULT, borderRadius: 4 },
          { label: '5-Year', data: regimens.map((r) => r.survival60), backgroundColor: clinicalColors.amber.DEFAULT, borderRadius: 4 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: {
          x: { grid: { display: false } },
          y: { min: 0, max: 1, ticks: { callback: (v) => `${(v * 100).toFixed(0)}%` } },
        },
        plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, padding: 16 } } },
      },
    });
    return () => chartRef.current?.destroy();
  }, []);

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
            <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold mb-2">Treatment Comparison</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-8">
              {id ? `Counterfactual drug comparison for Patient ${id}` : 'Compare predicted outcomes across treatment regimens using causal inference'}
            </p>

            {/* Survival comparison chart */}
            <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5 mb-6">
              <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Predicted Survival by Regimen</h2>
              <div className="h-72">
                <canvas ref={canvasRef}></canvas>
              </div>
            </div>

            {/* Comparison table */}
            <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="table-auto w-full text-sm">
                  <thead className="text-xs uppercase text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-900/20 border-b border-gray-200 dark:border-gray-700/60">
                    <tr>
                      <th className="px-4 py-3 text-left font-semibold">Regimen</th>
                      <th className="px-4 py-3 text-center font-semibold">1yr OS</th>
                      <th className="px-4 py-3 text-center font-semibold">2yr OS</th>
                      <th className="px-4 py-3 text-center font-semibold">5yr OS</th>
                      <th className="px-4 py-3 text-center font-semibold">pCR Rate</th>
                      <th className="px-4 py-3 text-center font-semibold">Grade 3+ Tox.</th>
                      <th className="px-4 py-3 text-right font-semibold">Est. Cost</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700/60">
                    {regimens.map((r, i) => (
                      <tr key={r.name} className={classNames('text-gray-700 dark:text-gray-300', i === 2 ? 'bg-violet-50/50 dark:bg-violet-500/5' : '')}>
                        <td className="px-4 py-3 font-medium">
                          {r.name}
                          {i === 2 && <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-violet-100 dark:bg-violet-500/20 text-violet-600 dark:text-violet-400">Recommended</span>}
                        </td>
                        <td className="px-4 py-3 text-center">{(r.survival12 * 100).toFixed(0)}%</td>
                        <td className="px-4 py-3 text-center">{(r.survival24 * 100).toFixed(0)}%</td>
                        <td className="px-4 py-3 text-center">{(r.survival60 * 100).toFixed(0)}%</td>
                        <td className="px-4 py-3 text-center">{(r.pCR * 100).toFixed(0)}%</td>
                        <td className="px-4 py-3 text-center">
                          <span className={classNames('text-xs font-medium px-2 py-0.5 rounded-full', r.toxicityGrade3 > 0.3 ? 'bg-rose-100 dark:bg-rose-500/20 text-rose-600' : r.toxicityGrade3 > 0.2 ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-600' : 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600')}>
                            {(r.toxicityGrade3 * 100).toFixed(0)}%
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right text-gray-800 dark:text-gray-100 font-medium">{r.cost}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
