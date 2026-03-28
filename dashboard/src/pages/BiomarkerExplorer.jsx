import { useState, useRef, useEffect } from 'react';
import { Chart, ScatterController, PointElement, LinearScale, Tooltip, Legend } from 'chart.js';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import { clinicalColors, subtypeColors } from '../charts/ChartjsConfig';
import { classNames } from '../utils/Utils';

Chart.register(ScatterController, PointElement, LinearScale, Tooltip, Legend);

const biomarkers = [
  { name: 'ERBB2 Amplification', novelty: 0.12, importance: 0.94, direction: 'oncogenic', associated: 'HER2+' },
  { name: 'ESR1 Expression', novelty: 0.08, importance: 0.91, direction: 'prognostic', associated: 'Luminal A/B' },
  { name: 'MYC Amplification', novelty: 0.34, importance: 0.82, direction: 'oncogenic', associated: 'Basal-like' },
  { name: 'FOXC1 Overexpression', novelty: 0.72, importance: 0.76, direction: 'novel', associated: 'Claudin-low' },
  { name: 'CDH1 Loss', novelty: 0.58, importance: 0.68, direction: 'novel', associated: 'Lobular' },
  { name: 'PIK3CA Hotspot', novelty: 0.22, importance: 0.85, direction: 'targetable', associated: 'Luminal A' },
  { name: 'TP53 GOF Mutations', novelty: 0.15, importance: 0.89, direction: 'oncogenic', associated: 'Basal-like' },
  { name: 'GATA3 Truncation', novelty: 0.45, importance: 0.71, direction: 'novel', associated: 'Luminal B' },
  { name: 'NTRK Fusion', novelty: 0.88, importance: 0.52, direction: 'targetable', associated: 'Rare' },
  { name: 'BRCA2 Biallelic', novelty: 0.31, importance: 0.78, direction: 'targetable', associated: 'HRD' },
];

const dirColors = { oncogenic: '#f43f5e', prognostic: '#0ea5e9', novel: '#8b5cf6', targetable: '#10b981' };

export default function BiomarkerExplorer() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const canvasRef = useRef(null); const chartRef = useRef(null);

  useEffect(() => {
    if (chartRef.current) chartRef.current.destroy();
    const ctx = canvasRef.current.getContext('2d');
    const groups = {};
    biomarkers.forEach((b) => {
      if (!groups[b.direction]) groups[b.direction] = [];
      groups[b.direction].push({ x: b.novelty, y: b.importance, label: b.name });
    });
    chartRef.current = new Chart(ctx, {
      type: 'scatter',
      data: {
        datasets: Object.entries(groups).map(([dir, points]) => ({
          label: dir.charAt(0).toUpperCase() + dir.slice(1),
          data: points,
          backgroundColor: dirColors[dir],
          pointRadius: 7,
          pointHoverRadius: 10,
        })),
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: {
          x: { min: 0, max: 1, title: { display: true, text: 'Novelty Score', color: '#94a3b8' } },
          y: { min: 0.4, max: 1, title: { display: true, text: 'Clinical Importance', color: '#94a3b8' } },
        },
        plugins: {
          legend: { position: 'bottom', labels: { usePointStyle: true, padding: 16 } },
          tooltip: { callbacks: { label: (ctx) => `${ctx.raw.label}: novelty=${ctx.raw.x.toFixed(2)}, importance=${ctx.raw.y.toFixed(2)}` } },
        },
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
            <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold mb-2">Biomarker Explorer</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-8">Discover novel molecular signatures from latent space analysis</p>

            {/* Scatter plot */}
            <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5 mb-6">
              <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Novelty vs Clinical Importance</h2>
              <div className="h-80"><canvas ref={canvasRef}></canvas></div>
            </div>

            {/* Biomarker table */}
            <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="table-auto w-full text-sm">
                  <thead className="text-xs uppercase text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-900/20 border-b border-gray-200 dark:border-gray-700/60">
                    <tr>
                      <th className="px-4 py-3 text-left">Biomarker</th>
                      <th className="px-4 py-3 text-center">Novelty</th>
                      <th className="px-4 py-3 text-center">Importance</th>
                      <th className="px-4 py-3 text-center">Type</th>
                      <th className="px-4 py-3 text-left">Associated Subtype</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700/60 text-gray-700 dark:text-gray-300">
                    {biomarkers.sort((a, b) => b.importance - a.importance).map((b) => (
                      <tr key={b.name}>
                        <td className="px-4 py-3 font-medium">{b.name}</td>
                        <td className="px-4 py-3 text-center">
                          <div className="flex items-center justify-center gap-2">
                            <div className="w-16 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                              <div className="h-full bg-violet-500 rounded-full" style={{ width: `${b.novelty * 100}%` }} />
                            </div>
                            <span className="text-xs w-8">{(b.novelty * 100).toFixed(0)}%</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-center font-medium">{(b.importance * 100).toFixed(0)}%</td>
                        <td className="px-4 py-3 text-center">
                          <span className="text-xs font-medium px-2 py-0.5 rounded-full" style={{ backgroundColor: `${dirColors[b.direction]}20`, color: dirColors[b.direction] }}>
                            {b.direction}
                          </span>
                        </td>
                        <td className="px-4 py-3">{b.associated}</td>
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
