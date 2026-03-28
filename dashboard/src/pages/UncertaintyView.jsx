import { useState, useRef, useEffect } from 'react';
import { Chart, LineController, LineElement, PointElement, LinearScale, CategoryScale, ScatterController, Tooltip, Legend } from 'chart.js';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import MetricCard from '../components/MetricCard';
import { clinicalColors } from '../charts/ChartjsConfig';
import { classNames } from '../utils/Utils';

Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, ScatterController, Tooltip, Legend);

export default function UncertaintyView() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const calRef = useRef(null); const calChartRef = useRef(null);
  const covRef = useRef(null); const covChartRef = useRef(null);

  // Calibration plot
  useEffect(() => {
    if (calChartRef.current) calChartRef.current.destroy();
    const ctx = calRef.current.getContext('2d');
    const bins = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0];
    const observed = [0.08, 0.19, 0.31, 0.38, 0.52, 0.58, 0.71, 0.79, 0.88, 0.96];
    calChartRef.current = new Chart(ctx, {
      type: 'line',
      data: {
        labels: bins,
        datasets: [
          { label: 'Model', data: observed, borderColor: clinicalColors.violet.DEFAULT, borderWidth: 2, pointRadius: 4, pointBackgroundColor: clinicalColors.violet.DEFAULT, tension: 0 },
          { label: 'Perfect', data: bins, borderColor: '#94a3b8', borderWidth: 1, borderDash: [6, 4], pointRadius: 0 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: {
          x: { title: { display: true, text: 'Predicted Probability', color: '#94a3b8' }, min: 0, max: 1 },
          y: { title: { display: true, text: 'Observed Frequency', color: '#94a3b8' }, min: 0, max: 1 },
        },
        plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, padding: 16 } } },
      },
    });
    return () => calChartRef.current?.destroy();
  }, []);

  // Coverage vs alpha
  useEffect(() => {
    if (covChartRef.current) covChartRef.current.destroy();
    const ctx = covRef.current.getContext('2d');
    const alphas = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5];
    const empirical = [0.96, 0.91, 0.87, 0.81, 0.77, 0.72, 0.62, 0.52];
    const nominal = alphas.map((a) => 1 - a);
    covChartRef.current = new Chart(ctx, {
      type: 'line',
      data: {
        labels: alphas.map((a) => `${(a * 100).toFixed(0)}%`),
        datasets: [
          { label: 'Empirical', data: empirical, borderColor: clinicalColors.teal.DEFAULT, borderWidth: 2, pointRadius: 4, pointBackgroundColor: clinicalColors.teal.DEFAULT },
          { label: 'Nominal', data: nominal, borderColor: '#94a3b8', borderWidth: 1, borderDash: [6, 4], pointRadius: 0 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: {
          x: { title: { display: true, text: 'Significance Level (α)', color: '#94a3b8' } },
          y: { title: { display: true, text: 'Coverage', color: '#94a3b8' }, min: 0.4, max: 1 },
        },
        plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, padding: 16 } } },
      },
    });
    return () => covChartRef.current?.destroy();
  }, []);

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
            <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold mb-2">Uncertainty Quantification</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-8">Calibration quality, conformal prediction sets, and aleatoric/epistemic decomposition</p>

            {/* Metrics */}
            <div className="grid grid-cols-12 gap-6 mb-6">
              <MetricCard className="col-span-12 sm:col-span-6 xl:col-span-3" title="ECE" value="0.018" subtitle="Expected Calibration Error" />
              <MetricCard className="col-span-12 sm:col-span-6 xl:col-span-3" title="Coverage @95%" value="96.1%" subtitle="Conformal coverage" />
              <MetricCard className="col-span-12 sm:col-span-6 xl:col-span-3" title="Avg Set Size" value="1.23" subtitle="Conformal set avg size" />
              <MetricCard className="col-span-12 sm:col-span-6 xl:col-span-3" title="Brier Score" value="0.042" subtitle="Mean squared probability" />
            </div>

            <div className="grid grid-cols-12 gap-6 mb-6">
              {/* Calibration plot */}
              <div className="col-span-12 lg:col-span-6 bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5">
                <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Reliability Diagram</h2>
                <div className="h-72"><canvas ref={calRef}></canvas></div>
              </div>

              {/* Coverage plot */}
              <div className="col-span-12 lg:col-span-6 bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5">
                <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Conformal Coverage</h2>
                <div className="h-72"><canvas ref={covRef}></canvas></div>
              </div>
            </div>

            {/* Decomposition */}
            <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5">
              <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Uncertainty Decomposition by Subtype</h2>
              <div className="overflow-x-auto">
                <table className="table-auto w-full text-sm">
                  <thead className="text-xs uppercase text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-900/20 border-b border-gray-200 dark:border-gray-700/60">
                    <tr>
                      <th className="px-4 py-3 text-left">Subtype</th>
                      <th className="px-4 py-3 text-center">Total</th>
                      <th className="px-4 py-3 text-center">Aleatoric</th>
                      <th className="px-4 py-3 text-center">Epistemic</th>
                      <th className="px-4 py-3 text-center">Conformal Set Size</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700/60 text-gray-700 dark:text-gray-300">
                    {[
                      { sub: 'Luminal A', total: 0.08, aleatoric: 0.05, epistemic: 0.03, setSize: 1.1 },
                      { sub: 'Luminal B', total: 0.14, aleatoric: 0.08, epistemic: 0.06, setSize: 1.3 },
                      { sub: 'HER2+', total: 0.12, aleatoric: 0.07, epistemic: 0.05, setSize: 1.2 },
                      { sub: 'Basal-like', total: 0.09, aleatoric: 0.06, epistemic: 0.03, setSize: 1.1 },
                      { sub: 'Normal-like', total: 0.22, aleatoric: 0.10, epistemic: 0.12, setSize: 1.8 },
                      { sub: 'Claudin-low', total: 0.19, aleatoric: 0.09, epistemic: 0.10, setSize: 1.6 },
                    ].map((r) => (
                      <tr key={r.sub}>
                        <td className="px-4 py-3 font-medium">{r.sub}</td>
                        <td className="px-4 py-3 text-center">{r.total.toFixed(3)}</td>
                        <td className="px-4 py-3 text-center">{r.aleatoric.toFixed(3)}</td>
                        <td className="px-4 py-3 text-center">{r.epistemic.toFixed(3)}</td>
                        <td className="px-4 py-3 text-center">{r.setSize.toFixed(1)}</td>
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
