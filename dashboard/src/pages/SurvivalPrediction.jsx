import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import GlowCard from '../components/GlowCard';

/* ── Generate synthetic survival data ────────────────────────────── */
function generateCohort(n, medianSurvival, label, seed = 1) {
  const rng = (i) => { const s = Math.sin(i * 127.1 + seed) * 43758.5; return s - Math.floor(s); };
  const patients = [];
  for (let i = 0; i < n; i++) {
    // Exponential-ish distribution
    const u = rng(i * 3 + seed);
    const time = -medianSurvival * Math.log(1 - u * 0.95);
    const censored = rng(i * 7 + seed) > 0.75; // 25% censored
    patients.push({ time: Math.max(0.5, Math.min(time, 60)), censored, label });
  }
  return patients.sort((a, b) => a.time - b.time);
}

function kaplanMeier(patients) {
  const n = patients.length;
  let atRisk = n;
  const curve = [{ t: 0, s: 1.0 }];
  patients.forEach(p => {
    if (!p.censored) {
      const s = curve[curve.length - 1].s * ((atRisk - 1) / atRisk);
      curve.push({ t: p.time, s });
    }
    atRisk--;
  });
  curve.push({ t: 60, s: curve[curve.length - 1].s });
  return curve;
}

/* ── Risk groups ────────────────────────────────────────────────── */
const RISK_GROUPS = [
  { key: 'low', label: 'Low Risk', color: '#10b981', median: 42, n: 85, seed: 1 },
  { key: 'mid', label: 'Intermediate', color: '#f59e0b', median: 24, n: 72, seed: 2 },
  { key: 'high', label: 'High Risk', color: '#f43f5e', median: 11, n: 58, seed: 3 },
];

/* ── Model features ranked by importance ─────────────────────────── */
const FEATURES = [
  { name: 'Nuclear pleomorphism score', importance: 0.187, category: 'Morphology' },
  { name: 'Tumor-stroma ratio', importance: 0.156, category: 'Morphology' },
  { name: 'CD8+ TIL density', importance: 0.141, category: 'Immune' },
  { name: 'Mitotic count (10 HPF)', importance: 0.128, category: 'Morphology' },
  { name: 'Necrosis percentage', importance: 0.095, category: 'Morphology' },
  { name: 'PD-L1 TPS', importance: 0.088, category: 'Biomarker' },
  { name: 'Vascular invasion', importance: 0.072, category: 'Morphology' },
  { name: 'Ki-67 index', importance: 0.063, category: 'Biomarker' },
  { name: 'Lymphovascular invasion', importance: 0.041, category: 'Morphology' },
  { name: 'Patient age', importance: 0.029, category: 'Clinical' },
];

const CAT_COLORS = { Morphology: '#7c3aed', Immune: '#10b981', Biomarker: '#0ea5e9', Clinical: '#64748b' };

/* ── Cox model summary ───────────────────────────────────────────── */
const COX_SUMMARY = [
  { covariate: 'Nuclear Score', hr: 2.14, ci_low: 1.62, ci_high: 2.83, p: '<0.001' },
  { covariate: 'TIL Density', hr: 0.58, ci_low: 0.44, ci_high: 0.76, p: '<0.001' },
  { covariate: 'Mitotic Count', hr: 1.87, ci_low: 1.38, ci_high: 2.53, p: '<0.001' },
  { covariate: 'PD-L1 TPS', hr: 0.71, ci_low: 0.55, ci_high: 0.92, p: '0.008' },
  { covariate: 'Necrosis %', hr: 1.45, ci_low: 1.12, ci_high: 1.88, p: '0.005' },
  { covariate: 'Age', hr: 1.02, ci_low: 1.00, ci_high: 1.04, p: '0.042' },
];

export default function SurvivalPrediction() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const canvasRef = useRef(null);
  const [visibleGroups, setVisibleGroups] = useState({ low: true, mid: true, high: true });
  const [showCI, setShowCI] = useState(false);
  const [hoveredTime, setHoveredTime] = useState(null);

  const cohorts = useMemo(() =>
    RISK_GROUPS.map(g => ({
      ...g,
      patients: generateCohort(g.n, g.median, g.key, g.seed),
    })).map(g => ({
      ...g,
      curve: kaplanMeier(g.patients),
    })),
  []);

  /* ── Draw KM curves ─────────────────────────────────────── */
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width = canvas.offsetWidth * 2;
    const H = canvas.height = canvas.offsetHeight * 2;
    ctx.scale(2, 2);
    const w = W / 2, h = H / 2;
    ctx.clearRect(0, 0, w, h);

    const pad = { top: 20, right: 20, bottom: 40, left: 50 };
    const pw = w - pad.left - pad.right;
    const ph = h - pad.top - pad.bottom;
    const maxT = 60;

    const tx = t => pad.left + (t / maxT) * pw;
    const ty = s => pad.top + (1 - s) * ph;

    // Grid
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 6; i++) {
      const x = tx((i / 6) * maxT);
      ctx.beginPath(); ctx.moveTo(x, pad.top); ctx.lineTo(x, h - pad.bottom); ctx.stroke();
    }
    for (let i = 0; i <= 5; i++) {
      const y = ty(i / 5);
      ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
      ctx.fillStyle = '#9ca3af';
      ctx.font = '10px Inter, sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText(`${(i * 20)}%`, pad.left - 6, y + 3);
    }

    // X axis labels
    ctx.textAlign = 'center';
    ctx.fillStyle = '#9ca3af';
    for (let i = 0; i <= 6; i++) {
      ctx.fillText(`${Math.round((i / 6) * maxT)}`, tx((i / 6) * maxT), h - pad.bottom + 16);
    }
    ctx.fillText('Months', w / 2, h - 4);
    // Y axis label
    ctx.save();
    ctx.translate(12, h / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('Survival Probability', 0, 0);
    ctx.restore();

    // Confidence intervals (approximate)
    if (showCI) {
      cohorts.forEach(g => {
        if (!visibleGroups[g.key]) return;
        ctx.fillStyle = g.color;
        ctx.globalAlpha = 0.08;
        ctx.beginPath();
        g.curve.forEach((pt, i) => {
          const ci = 0.06 * Math.sqrt(1 / Math.max(1, g.n - i * 3));
          const fn = i === 0 ? 'moveTo' : 'lineTo';
          ctx[fn](tx(pt.t), ty(Math.min(1, pt.s + ci)));
        });
        for (let i = g.curve.length - 1; i >= 0; i--) {
          const pt = g.curve[i];
          const ci = 0.06 * Math.sqrt(1 / Math.max(1, g.n - i * 3));
          ctx.lineTo(tx(pt.t), ty(Math.max(0, pt.s - ci)));
        }
        ctx.closePath();
        ctx.fill();
        ctx.globalAlpha = 1;
      });
    }

    // KM step curves
    cohorts.forEach(g => {
      if (!visibleGroups[g.key]) return;
      ctx.strokeStyle = g.color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      g.curve.forEach((pt, i) => {
        if (i === 0) {
          ctx.moveTo(tx(pt.t), ty(pt.s));
        } else {
          ctx.lineTo(tx(pt.t), ty(g.curve[i - 1].s)); // horizontal step
          ctx.lineTo(tx(pt.t), ty(pt.s)); // vertical drop
        }
      });
      ctx.stroke();

      // Censored marks
      g.patients.filter(p => p.censored).forEach(p => {
        const sAtTime = g.curve.reduce((acc, pt) => pt.t <= p.time ? pt.s : acc, 1);
        ctx.strokeStyle = g.color;
        ctx.lineWidth = 1.5;
        const cx = tx(p.time), cy = ty(sAtTime);
        ctx.beginPath(); ctx.moveTo(cx, cy - 3); ctx.lineTo(cx, cy + 3); ctx.stroke();
      });
    });

    // Hover line
    if (hoveredTime !== null) {
      const hx = tx(hoveredTime);
      ctx.strokeStyle = '#6b7280';
      ctx.lineWidth = 0.8;
      ctx.setLineDash([4, 3]);
      ctx.beginPath(); ctx.moveTo(hx, pad.top); ctx.lineTo(hx, h - pad.bottom); ctx.stroke();
      ctx.setLineDash([]);

      // Survival at hover time
      ctx.font = 'bold 10px Inter, sans-serif';
      cohorts.forEach((g, gi) => {
        if (!visibleGroups[g.key]) return;
        const sAtTime = g.curve.reduce((acc, pt) => pt.t <= hoveredTime ? pt.s : acc, 1);
        ctx.fillStyle = g.color;
        ctx.textAlign = 'left';
        ctx.fillText(`${g.label}: ${(sAtTime * 100).toFixed(1)}%`, hx + 6, pad.top + 14 + gi * 14);
      });
    }
  }, [cohorts, visibleGroups, showCI, hoveredTime]);

  useEffect(() => { draw(); }, [draw]);

  const handleMouseMove = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const pad = { left: 50, right: 20 };
    const mx = (e.clientX - rect.left) / rect.width;
    const pw = 1 - (pad.left + pad.right) / (rect.width);
    const relX = (mx - pad.left / rect.width) / pw;
    if (relX >= 0 && relX <= 1) {
      setHoveredTime(relX * 60);
    } else {
      setHoveredTime(null);
    }
  };

  const toggleGroup = (key) => setVisibleGroups(v => ({ ...v, [key]: !v[key] }));

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
            <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-1">Survival Prediction</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
              Morphology-based survival analysis &middot; Cox PH model &middot; {cohorts.reduce((s, g) => s + g.n, 0)} total patients
            </p>

            <div className="grid grid-cols-12 gap-6">
              {/* KM Curve */}
              <div className="col-span-12 xl:col-span-8">
                <GlowCard>
                  <div className="p-4">
                    <div className="flex flex-wrap items-center gap-3 mb-3">
                      <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100">Kaplan-Meier Curves</h2>
                      <div className="flex items-center gap-2 ml-auto">
                        {RISK_GROUPS.map(g => (
                          <button
                            key={g.key}
                            onClick={() => toggleGroup(g.key)}
                            className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium transition ${visibleGroups[g.key] ? 'text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-500'}`}
                            style={visibleGroups[g.key] ? { backgroundColor: g.color } : {}}
                          >
                            {g.label} (n={g.n})
                          </button>
                        ))}
                        <div className="h-5 w-px bg-gray-300 dark:bg-gray-600 mx-1" />
                        <label className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
                          <input type="checkbox" checked={showCI} onChange={() => setShowCI(!showCI)} className="rounded text-violet-500" />
                          95% CI
                        </label>
                      </div>
                    </div>
                    <canvas
                      ref={canvasRef}
                      className="w-full rounded-lg bg-white dark:bg-gray-950 border border-gray-200 dark:border-gray-700"
                      style={{ height: 380 }}
                      onMouseMove={handleMouseMove}
                      onMouseLeave={() => setHoveredTime(null)}
                    />
                    <div className="flex items-center gap-4 mt-2 text-[10px] text-gray-400">
                      <span>Step function = KM estimator</span>
                      <span>Vertical ticks = censored events</span>
                      <span>Log-rank p &lt; 0.001</span>
                    </div>
                  </div>
                </GlowCard>

                {/* Feature importance */}
                <GlowCard className="mt-6">
                  <div className="p-4">
                    <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3">Feature Importance (SHAP)</h2>
                    <div className="space-y-2">
                      {FEATURES.map(f => (
                        <div key={f.name} className="flex items-center gap-3">
                          <span className="text-xs text-gray-600 dark:text-gray-400 w-44 truncate">{f.name}</span>
                          <div className="flex-1 h-4 bg-gray-100 dark:bg-gray-800 rounded overflow-hidden relative">
                            <div className="h-full rounded" style={{ width: `${f.importance * 100 / 0.2}%`, backgroundColor: CAT_COLORS[f.category] }} />
                          </div>
                          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 w-10 text-right">{(f.importance * 100).toFixed(1)}%</span>
                          <span className="text-[9px] px-1.5 py-0.5 rounded-full font-medium" style={{ backgroundColor: CAT_COLORS[f.category] + '20', color: CAT_COLORS[f.category] }}>{f.category}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </GlowCard>
              </div>

              {/* Right panel */}
              <div className="col-span-12 xl:col-span-4 flex flex-col gap-4">
                {/* Risk group summary */}
                <GlowCard>
                  <div className="p-4">
                    <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3">Risk Stratification</h2>
                    <div className="space-y-3">
                      {cohorts.map(g => {
                        const events = g.patients.filter(p => !p.censored).length;
                        const medianActual = g.patients[Math.floor(g.patients.length / 2)]?.time.toFixed(1);
                        return (
                          <div key={g.key} className="p-3 rounded-lg border border-gray-100 dark:border-gray-700">
                            <div className="flex items-center gap-2 mb-2">
                              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: g.color }} />
                              <span className="text-xs font-semibold text-gray-800 dark:text-gray-100">{g.label}</span>
                            </div>
                            <dl className="grid grid-cols-2 gap-y-1 text-xs">
                              <dt className="text-gray-500">Patients</dt><dd className="font-medium text-gray-700 dark:text-gray-300">{g.n}</dd>
                              <dt className="text-gray-500">Events</dt><dd className="font-medium text-gray-700 dark:text-gray-300">{events}</dd>
                              <dt className="text-gray-500">Median OS</dt><dd className="font-medium text-gray-700 dark:text-gray-300">{medianActual} mo</dd>
                              <dt className="text-gray-500">1-yr Survival</dt>
                              <dd className="font-medium text-gray-700 dark:text-gray-300">
                                {(g.curve.reduce((acc, pt) => pt.t <= 12 ? pt.s : acc, 1) * 100).toFixed(0)}%
                              </dd>
                            </dl>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </GlowCard>

                {/* Cox regression table */}
                <GlowCard>
                  <div className="p-4">
                    <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3">Cox PH Model</h2>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
                            <th className="text-left pb-1.5 font-medium">Covariate</th>
                            <th className="text-right pb-1.5 font-medium">HR</th>
                            <th className="text-right pb-1.5 font-medium">95% CI</th>
                            <th className="text-right pb-1.5 font-medium">p</th>
                          </tr>
                        </thead>
                        <tbody>
                          {COX_SUMMARY.map(row => (
                            <tr key={row.covariate} className="border-t border-gray-100 dark:border-gray-700/50">
                              <td className="py-1.5 text-gray-700 dark:text-gray-300">{row.covariate}</td>
                              <td className={`py-1.5 text-right font-semibold ${row.hr > 1 ? 'text-rose-600' : 'text-teal-600'}`}>{row.hr.toFixed(2)}</td>
                              <td className="py-1.5 text-right text-gray-500">{row.ci_low.toFixed(2)}&ndash;{row.ci_high.toFixed(2)}</td>
                              <td className="py-1.5 text-right font-medium text-gray-600 dark:text-gray-400">{row.p}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <p className="text-[10px] text-gray-400 mt-2">Concordance index (C-statistic): 0.782</p>
                  </div>
                </GlowCard>

                {/* Model info */}
                <GlowCard>
                  <div className="p-4">
                    <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3">Model Details</h2>
                    <dl className="space-y-2 text-xs">
                      {[
                        { label: 'Architecture', value: 'ResNet-50 + Cox head' },
                        { label: 'Input', value: '256\u00d7256 px patches @ 20\u00d7' },
                        { label: 'Training Set', value: '1,247 WSIs (TCGA)' },
                        { label: 'Validation', value: '5-fold cross-validation' },
                        { label: 'C-Index (val)', value: '0.782 \u00b1 0.023' },
                        { label: 'Calibration', value: 'Brier score 0.18' },
                      ].map(row => (
                        <div key={row.label} className="flex justify-between">
                          <dt className="text-gray-500 dark:text-gray-400">{row.label}</dt>
                          <dd className="font-medium text-gray-800 dark:text-gray-100">{row.value}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                </GlowCard>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
