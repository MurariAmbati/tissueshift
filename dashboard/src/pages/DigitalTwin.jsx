import { useState, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Chart, LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend, Filler } from 'chart.js';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import { clinicalColors, subtypeColors } from '../charts/ChartjsConfig';
import { classNames } from '../utils/Utils';

Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend, Filler);

const drugs = ['Tamoxifen', 'Paclitaxel', 'Pembrolizumab', 'Trastuzumab', 'Capecitabine'];

export default function DigitalTwin() {
  const { id } = useParams();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [horizonMonths, setHorizonMonths] = useState(24);
  const [selectedDrug, setSelectedDrug] = useState('Paclitaxel');
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (chartRef.current) chartRef.current.destroy();
    const ctx = canvasRef.current.getContext('2d');
    const months = Array.from({ length: horizonMonths + 1 }, (_, i) => i);
    const baseline = months.map((m) => Math.exp(-0.693 * m / 28));
    const treated = months.map((m) => Math.exp(-0.693 * m / 42));
    const upper = treated.map((v) => Math.min(1, v + 0.06));
    const lower = treated.map((v) => Math.max(0, v - 0.06));

    chartRef.current = new Chart(ctx, {
      type: 'line',
      data: {
        labels: months,
        datasets: [
          { label: `With ${selectedDrug}`, data: treated, borderColor: clinicalColors.teal.DEFAULT, borderWidth: 2.5, pointRadius: 0, tension: 0.3, fill: false },
          { label: 'Baseline (no treatment)', data: baseline, borderColor: clinicalColors.rose.DEFAULT, borderWidth: 2, borderDash: [6, 4], pointRadius: 0, tension: 0.3, fill: false },
          { label: '95% CI upper', data: upper, borderColor: `${clinicalColors.teal.DEFAULT}30`, borderWidth: 1, pointRadius: 0, tension: 0.3, fill: '+1', backgroundColor: `${clinicalColors.teal.DEFAULT}15` },
          { label: '95% CI lower', data: lower, borderColor: `${clinicalColors.teal.DEFAULT}30`, borderWidth: 1, pointRadius: 0, tension: 0.3, fill: false },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: {
          x: { title: { display: true, text: 'Months', color: '#94a3b8' }, grid: { display: false } },
          y: { min: 0, max: 1, title: { display: true, text: 'Survival Probability', color: '#94a3b8' }, ticks: { callback: (v) => `${(v * 100).toFixed(0)}%` } },
        },
        plugins: {
          legend: { position: 'bottom', labels: { filter: (item) => !item.text.includes('CI'), usePointStyle: true, padding: 16 } },
        },
        interaction: { mode: 'index', intersect: false },
      },
    });
    return () => chartRef.current?.destroy();
  }, [horizonMonths, selectedDrug]);

  const stateVars = [
    { name: 'Tumor Volume', current: '3.8 cm³', predicted: '1.2 cm³', delta: '-68%', trend: 'down' },
    { name: 'ctDNA Level', current: '420 copies/mL', predicted: '85 copies/mL', delta: '-80%', trend: 'down' },
    { name: 'Ki-67 Index', current: '82%', predicted: '34%', delta: '-59%', trend: 'down' },
    { name: 'TIL Score', current: '32%', predicted: '58%', delta: '+81%', trend: 'up' },
    { name: 'Immune Score', current: '0.42', predicted: '0.71', delta: '+69%', trend: 'up' },
  ];

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
            <div className="flex flex-wrap items-center justify-between mb-8">
              <div>
                <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold">Digital Twin Simulator</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{id ? `Patient ${id}` : 'Neural ODE-driven patient trajectory forecasting'}</p>
              </div>
            </div>

            {/* Controls */}
            <div className="flex flex-wrap gap-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Drug Intervention</label>
                <select className="form-select text-sm rounded-lg border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-800" value={selectedDrug} onChange={(e) => setSelectedDrug(e.target.value)}>
                  {drugs.map((d) => <option key={d}>{d}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Forecast Horizon</label>
                <div className="flex items-center gap-2">
                  <input type="range" min="6" max="60" step="6" value={horizonMonths} onChange={(e) => setHorizonMonths(Number(e.target.value))} className="w-36" />
                  <span className="text-sm text-gray-600 dark:text-gray-300 w-14">{horizonMonths}mo</span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-12 gap-6">
              {/* Trajectory chart */}
              <div className="col-span-12 lg:col-span-8 bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5">
                <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Predicted Trajectory</h2>
                <div className="h-80">
                  <canvas ref={canvasRef}></canvas>
                </div>
              </div>

              {/* State variables */}
              <div className="col-span-12 lg:col-span-4 bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5">
                <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Predicted State Changes</h2>
                <p className="text-xs text-gray-400 dark:text-gray-500 mb-4">After {horizonMonths} months with {selectedDrug}</p>
                <div className="space-y-4">
                  {stateVars.map((s) => (
                    <div key={s.name} className="p-3 bg-gray-50 dark:bg-gray-900/30 rounded-lg">
                      <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">{s.name}</div>
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="text-sm text-gray-500 line-through mr-2">{s.current}</span>
                          <span className="text-sm font-semibold text-gray-800 dark:text-gray-100">{s.predicted}</span>
                        </div>
                        <span className={classNames('text-xs font-bold px-2 py-0.5 rounded-full', s.trend === 'down' ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400' : 'bg-teal-100 dark:bg-teal-500/20 text-teal-700 dark:text-teal-400')}>
                          {s.delta}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
