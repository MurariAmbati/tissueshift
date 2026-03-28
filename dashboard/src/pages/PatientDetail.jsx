import { useState, useRef, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Chart, DoughnutController, ArcElement, LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend } from 'chart.js';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import RiskBadge from '../components/RiskBadge';
import SubtypeBadge from '../components/SubtypeBadge';
import ConfidenceBar from '../components/ConfidenceBar';
import { subtypeColors, clinicalColors } from '../charts/ChartjsConfig';
import { classNames } from '../utils/Utils';

Chart.register(DoughnutController, ArcElement, LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend);

const patient = {
  id: 'P-2846',
  age: 67,
  sex: 'Female',
  stage: 'IIIB',
  grade: 3,
  tumor_size: '4.2 cm',
  lymph_nodes: '7/18 positive',
  er: '-', pr: '-', her2: '-', ki67: '82%',
  subtype: 'basal',
  risk: 'high',
  confidence: 0.94,
  subtypeProbs: { luminal_a: 0.01, luminal_b: 0.02, her2_enriched: 0.02, basal: 0.94, normal_like: 0.005, claudin_low: 0.005 },
  treatments: [
    { name: 'AC-T (Doxo + Cyclo → Paclitaxel)', status: 'current', start: '2024-01-02' },
    { name: 'Pembrolizumab (PD-1 inhibitor)', status: 'planned', start: '2024-03-01' },
  ],
  genomicFeatures: { tp53_mutation: true, brca1_methylation: true, pik3ca_mutation: false, myc_amplification: true, ccnd1_amplification: false },
  survivalPrediction: { months_12: 0.78, months_24: 0.54, months_60: 0.31 },
};

export default function PatientDetail() {
  const { id } = useParams();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const subtypeChartRef = useRef(null);
  const subtypeCanvasRef = useRef(null);
  const trajectoryChartRef = useRef(null);
  const trajectoryCanvasRef = useRef(null);

  useEffect(() => {
    if (subtypeChartRef.current) subtypeChartRef.current.destroy();
    const ctx = subtypeCanvasRef.current.getContext('2d');
    const probs = patient.subtypeProbs;
    subtypeChartRef.current = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: Object.keys(probs).map((k) => k.replace(/_/g, ' ')),
        datasets: [{ data: Object.values(probs), backgroundColor: Object.keys(probs).map((k) => subtypeColors[k] || '#94a3b8'), borderWidth: 0 }],
      },
      options: { cutout: '65%', plugins: { legend: { display: false } } },
    });
    return () => subtypeChartRef.current?.destroy();
  }, []);

  useEffect(() => {
    if (trajectoryChartRef.current) trajectoryChartRef.current.destroy();
    const ctx = trajectoryCanvasRef.current.getContext('2d');
    const months = [0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60];
    const survival = months.map((m) => Math.exp(-0.693 * m / 30));
    const upper = survival.map((s) => Math.min(1, s + 0.08));
    const lower = survival.map((s) => Math.max(0, s - 0.08));
    trajectoryChartRef.current = new Chart(ctx, {
      type: 'line',
      data: {
        labels: months,
        datasets: [
          { label: 'Predicted', data: survival, borderColor: clinicalColors.violet.DEFAULT, borderWidth: 2, pointRadius: 3, tension: 0.3, fill: false },
          { label: 'Upper 95% CI', data: upper, borderColor: `${clinicalColors.violet.DEFAULT}30`, borderWidth: 1, borderDash: [4, 4], pointRadius: 0, fill: '+1', backgroundColor: `${clinicalColors.violet.DEFAULT}10`, tension: 0.3 },
          { label: 'Lower 95% CI', data: lower, borderColor: `${clinicalColors.violet.DEFAULT}30`, borderWidth: 1, borderDash: [4, 4], pointRadius: 0, fill: false, tension: 0.3 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: {
          x: { title: { display: true, text: 'Months' }, grid: { display: false } },
          y: { min: 0, max: 1, title: { display: true, text: 'Survival Prob.' }, ticks: { callback: (v) => `${(v * 100).toFixed(0)}%` } },
        },
        plugins: { legend: { display: false } },
      },
    });
    return () => trajectoryChartRef.current?.destroy();
  }, []);

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
            {/* Breadcrumb */}
            <div className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              <Link to="/patients" className="text-violet-500 hover:text-violet-600">Patients</Link>
              <span className="mx-2">→</span>
              <span>{id}</span>
            </div>

            {/* Patient header */}
            <div className="flex flex-wrap items-start justify-between gap-4 mb-8">
              <div>
                <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold mb-2">{patient.id}</h1>
                <div className="flex flex-wrap gap-2 items-center">
                  <SubtypeBadge subtype={patient.subtype} />
                  <RiskBadge level={patient.risk} />
                  <span className="text-sm text-gray-500 dark:text-gray-400">Stage {patient.stage} • Grade {patient.grade}</span>
                </div>
              </div>
              <div className="flex gap-2">
                <Link to={`/patients/${id}/timeline`} className="btn text-sm font-medium bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700/60 rounded-lg px-4 py-2 hover:border-gray-300">Timeline</Link>
                <Link to={`/digital-twin/${id}`} className="btn text-sm font-medium bg-violet-500 text-white rounded-lg px-4 py-2 hover:bg-violet-600">Digital Twin</Link>
                <Link to={`/reports/${id}`} className="btn text-sm font-medium bg-gray-900 text-gray-100 rounded-lg px-4 py-2 hover:bg-gray-800 dark:bg-gray-100 dark:text-gray-800 dark:hover:bg-white">Generate Report</Link>
              </div>
            </div>

            <div className="grid grid-cols-12 gap-6">
              {/* Clinical info */}
              <div className="col-span-12 lg:col-span-4 space-y-6">
                <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5">
                  <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Clinical Profile</h2>
                  <dl className="space-y-3 text-sm">
                    {[['Age', `${patient.age} years`], ['Sex', patient.sex], ['Tumor Size', patient.tumor_size], ['Lymph Nodes', patient.lymph_nodes], ['ER', patient.er], ['PR', patient.pr], ['HER2', patient.her2], ['Ki-67', patient.ki67]].map(([k, v]) => (
                      <div key={k} className="flex justify-between">
                        <dt className="text-gray-500 dark:text-gray-400">{k}</dt>
                        <dd className="font-medium text-gray-800 dark:text-gray-100">{v}</dd>
                      </div>
                    ))}
                  </dl>
                </div>

                {/* Subtype probabilities */}
                <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5">
                  <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Subtype Probabilities</h2>
                  <div className="flex justify-center mb-4">
                    <div className="w-36 h-36 relative">
                      <canvas ref={subtypeCanvasRef}></canvas>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-xl font-bold text-gray-800 dark:text-gray-100">{(patient.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  </div>
                  <ul className="space-y-2">
                    {Object.entries(patient.subtypeProbs).map(([k, v]) => (
                      <li key={k} className="flex items-center justify-between text-sm">
                        <div className="flex items-center">
                          <span className="w-2 h-2 rounded-full mr-2" style={{ backgroundColor: subtypeColors[k] }} />
                          <span className="text-gray-600 dark:text-gray-300 capitalize">{k.replace(/_/g, ' ')}</span>
                        </div>
                        <span className="font-medium text-gray-800 dark:text-gray-100">{(v * 100).toFixed(1)}%</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Main content */}
              <div className="col-span-12 lg:col-span-8 space-y-6">
                {/* Predicted survival */}
                <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5">
                  <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Predicted Survival Trajectory</h2>
                  <div className="flex gap-4 mb-4">
                    {[['1-year', patient.survivalPrediction.months_12], ['2-year', patient.survivalPrediction.months_24], ['5-year', patient.survivalPrediction.months_60]].map(([label, val]) => (
                      <div key={label} className="flex-1 text-center bg-gray-50 dark:bg-gray-900/30 rounded-lg py-3">
                        <div className="text-2xl font-bold text-gray-800 dark:text-gray-100">{(val * 100).toFixed(0)}%</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">{label} survival</div>
                      </div>
                    ))}
                  </div>
                  <div className="h-56">
                    <canvas ref={trajectoryCanvasRef}></canvas>
                  </div>
                </div>

                {/* Treatments */}
                <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5">
                  <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Treatment Plan</h2>
                  <div className="space-y-3">
                    {patient.treatments.map((t, i) => (
                      <div key={i} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900/30 rounded-lg">
                        <div>
                          <div className="font-medium text-gray-800 dark:text-gray-100 text-sm">{t.name}</div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">Start: {t.start}</div>
                        </div>
                        <span className={classNames(
                          'text-xs font-medium px-2.5 py-1 rounded-full',
                          t.status === 'current' ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400' : 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400',
                        )}>{t.status}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Genomic features */}
                <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5">
                  <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Genomic Aberrations</h2>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(patient.genomicFeatures).map(([gene, present]) => (
                      <span key={gene} className={classNames(
                        'text-xs font-medium px-3 py-1.5 rounded-full',
                        present ? 'bg-rose-100 dark:bg-rose-500/20 text-rose-700 dark:text-rose-400' : 'bg-gray-100 dark:bg-gray-700/50 text-gray-500 dark:text-gray-400',
                      )}>
                        {gene.replace(/_/g, ' ').toUpperCase()}: {present ? 'Detected' : 'Not detected'}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
