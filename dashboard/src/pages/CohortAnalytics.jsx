import { useState, useRef, useEffect } from 'react';
import { Chart, BarController, BarElement, LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend, Filler } from 'chart.js';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import MetricCard from '../components/MetricCard';
import DropdownFilter from '../components/DropdownFilter';
import { clinicalColors, subtypeColors } from '../charts/ChartjsConfig';
import { classNames } from '../utils/Utils';

Chart.register(BarController, BarElement, LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend, Filler);

export default function CohortAnalytics() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [stage, setStage] = useState('all');
  const ageRef = useRef(null); const ageChartRef = useRef(null);
  const survRef = useRef(null); const survChartRef = useRef(null);

  // Age distribution
  useEffect(() => {
    if (ageChartRef.current) ageChartRef.current.destroy();
    const ctx = ageRef.current.getContext('2d');
    ageChartRef.current = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['20-29', '30-39', '40-49', '50-59', '60-69', '70-79', '80+'],
        datasets: [{
          data: [42, 187, 534, 812, 724, 389, 159],
          backgroundColor: clinicalColors.violet.DEFAULT,
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { grid: { display: false } }, y: { grid: { color: '#e2e8f020' } } },
      },
    });
    return () => ageChartRef.current?.destroy();
  }, []);

  // Survival by stage
  useEffect(() => {
    if (survChartRef.current) survChartRef.current.destroy();
    const ctx = survRef.current.getContext('2d');
    const months = Array.from({ length: 61 }, (_, i) => i);
    const stages = [
      { label: 'Stage I', median: 96, color: '#10b981' },
      { label: 'Stage II', median: 72, color: '#0ea5e9' },
      { label: 'Stage III', median: 42, color: '#f59e0b' },
      { label: 'Stage IV', median: 18, color: '#f43f5e' },
    ];
    survChartRef.current = new Chart(ctx, {
      type: 'line',
      data: {
        labels: months,
        datasets: stages.map((s) => ({
          label: s.label,
          data: months.map((m) => Math.exp(-0.693 * m / s.median)),
          borderColor: s.color, borderWidth: 2, pointRadius: 0, tension: 0.3, fill: false,
        })),
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: {
          x: { title: { display: true, text: 'Months' }, grid: { display: false }, ticks: { maxTicksLimit: 7 } },
          y: { min: 0, max: 1, title: { display: true, text: 'OS' }, ticks: { callback: (v) => `${(v * 100).toFixed(0)}%` } },
        },
        plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, padding: 16 } } },
        interaction: { mode: 'index', intersect: false },
      },
    });
    return () => survChartRef.current?.destroy();
  }, []);

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
            <div className="flex flex-wrap items-center justify-between mb-8">
              <div>
                <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold">Cohort Analytics</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Population-level stratification and epidemiological insights</p>
              </div>
              <DropdownFilter id="stage-filter" label="Stage" options={[{ value: 'all', label: 'All Stages' }, 'I', 'II', 'III', 'IV']} value={stage} onChange={setStage} />
            </div>

            {/* KPIs */}
            <div className="grid grid-cols-12 gap-6 mb-6">
              <MetricCard className="col-span-12 sm:col-span-6 xl:col-span-3" title="Cohort Size" value="2,847" change="12.5%" changeDir="up" />
              <MetricCard className="col-span-12 sm:col-span-6 xl:col-span-3" title="Median Age" value="58.3 yrs" />
              <MetricCard className="col-span-12 sm:col-span-6 xl:col-span-3" title="5yr OS (Overall)" value="68.4%" change="2.1%" changeDir="up" />
              <MetricCard className="col-span-12 sm:col-span-6 xl:col-span-3" title="Triple-Negative" value="16.8%" subtitle="(478 patients)" />
            </div>

            <div className="grid grid-cols-12 gap-6">
              <div className="col-span-12 lg:col-span-5 bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5">
                <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Age Distribution</h2>
                <div className="h-64"><canvas ref={ageRef}></canvas></div>
              </div>
              <div className="col-span-12 lg:col-span-7 bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5">
                <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Survival by Stage</h2>
                <div className="h-64"><canvas ref={survRef}></canvas></div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
