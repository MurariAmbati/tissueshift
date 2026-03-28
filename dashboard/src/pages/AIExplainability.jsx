import { useState, useRef, useEffect, useCallback } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import GlowCard from '../components/GlowCard';

/* ── Feature importance data ──────────────────────────────────── */
const PREDICTIONS = [
  {
    id: 'pred-surv-5y',
    name: '5-Year Survival Probability',
    outcome: '78.3%',
    confidence: 92,
    features: [
      { name: 'Tumor Stage (T3)', shap: -0.18, direction: 'negative', category: 'Clinical' },
      { name: 'Lymph Node Status (N1)', shap: -0.14, direction: 'negative', category: 'Clinical' },
      { name: 'HER2 Status (3+)', shap: 0.22, direction: 'positive', category: 'Molecular' },
      { name: 'ER Expression (45%)', shap: 0.08, direction: 'positive', category: 'Molecular' },
      { name: 'Ki-67 (62%)', shap: -0.11, direction: 'negative', category: 'Molecular' },
      { name: 'PIK3CA E545K', shap: -0.06, direction: 'negative', category: 'Genomic' },
      { name: 'TIL Score (28%)', shap: 0.09, direction: 'positive', category: 'Pathology' },
      { name: 'Age (52)', shap: 0.03, direction: 'positive', category: 'Clinical' },
      { name: 'Grade 3', shap: -0.12, direction: 'negative', category: 'Pathology' },
      { name: 'Tumor Purity (0.74)', shap: -0.04, direction: 'negative', category: 'Pathology' },
    ],
  },
  {
    id: 'pred-pcr',
    name: 'Pathologic Complete Response (pCR)',
    outcome: '58.2%',
    confidence: 87,
    features: [
      { name: 'HER2 3+ Amplification', shap: 0.28, direction: 'positive', category: 'Molecular' },
      { name: 'Ki-67 (62%)', shap: 0.15, direction: 'positive', category: 'Molecular' },
      { name: 'TCHP Regimen', shap: 0.19, direction: 'positive', category: 'Treatment' },
      { name: 'PIK3CA Mutation', shap: -0.16, direction: 'negative', category: 'Genomic' },
      { name: 'ER Positivity (45%)', shap: -0.10, direction: 'negative', category: 'Molecular' },
      { name: 'Grade 3', shap: 0.08, direction: 'positive', category: 'Pathology' },
      { name: 'Tumor Size (4.2cm)', shap: -0.07, direction: 'negative', category: 'Clinical' },
      { name: 'TIL Score (28%)', shap: 0.11, direction: 'positive', category: 'Pathology' },
    ],
  },
  {
    id: 'pred-recurrence',
    name: 'Recurrence Risk (3-year)',
    outcome: '24.1%',
    confidence: 85,
    features: [
      { name: 'Stage IIIA', shap: 0.20, direction: 'positive', category: 'Clinical' },
      { name: 'N1 (axillary)', shap: 0.16, direction: 'positive', category: 'Clinical' },
      { name: 'PIK3CA E545K', shap: 0.09, direction: 'positive', category: 'Genomic' },
      { name: 'Ki-67 (62%)', shap: 0.07, direction: 'positive', category: 'Molecular' },
      { name: 'HER2-targeted Tx', shap: -0.22, direction: 'negative', category: 'Treatment' },
      { name: 'TIL Score (28%)', shap: -0.08, direction: 'negative', category: 'Pathology' },
      { name: 'Age (52)', shap: -0.03, direction: 'negative', category: 'Clinical' },
      { name: 'ER Expression', shap: -0.05, direction: 'negative', category: 'Molecular' },
    ],
  },
];

/* ── SHAP waterfall canvas ──────────────────────────────────── */
function SHAPWaterfall({ features }) {
  const canvasRef = useRef(null);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const cw = canvas.offsetWidth;
    const barH = 28;
    const ch = features.length * barH + 60;
    canvas.width = cw * devicePixelRatio;
    canvas.height = ch * devicePixelRatio;
    canvas.style.height = ch + 'px';
    ctx.scale(devicePixelRatio, devicePixelRatio);

    ctx.fillStyle = '#0a0a18';
    ctx.fillRect(0, 0, cw, ch);

    const maxAbs = Math.max(...features.map(f => Math.abs(f.shap)), 0.01);
    const midX = cw * 0.55;
    const barScale = (cw * 0.35) / maxAbs;

    // Sort by absolute shap
    const sorted = [...features].sort((a, b) => Math.abs(b.shap) - Math.abs(a.shap));

    sorted.forEach((feat, i) => {
      const y = 30 + i * barH;
      const barWidth = Math.abs(feat.shap) * barScale;
      const isPos = feat.shap > 0;

      // Bar
      const barX = isPos ? midX : midX - barWidth;
      const gradient = ctx.createLinearGradient(barX, 0, barX + barWidth, 0);
      if (isPos) {
        gradient.addColorStop(0, '#f43f5e40');
        gradient.addColorStop(1, '#f43f5e');
      } else {
        gradient.addColorStop(0, '#0ea5e9');
        gradient.addColorStop(1, '#0ea5e940');
      }
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.roundRect(barX, y + 2, barWidth, barH - 6, 3);
      ctx.fill();

      // Feature name
      ctx.font = '10px Inter, sans-serif';
      ctx.fillStyle = '#ffffff90';
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      ctx.fillText(feat.name, midX - 12, y + barH / 2);

      // SHAP value
      ctx.font = 'bold 10px Inter, sans-serif';
      ctx.fillStyle = isPos ? '#f43f5e' : '#0ea5e9';
      ctx.textAlign = isPos ? 'left' : 'right';
      const valX = isPos ? midX + barWidth + 6 : midX - barWidth - 6;
      ctx.fillText((isPos ? '+' : '') + feat.shap.toFixed(2), valX, y + barH / 2);

      // Category badge
      ctx.font = '8px Inter, sans-serif';
      ctx.fillStyle = '#ffffff30';
      ctx.textAlign = 'left';
      ctx.fillText(feat.category, cw - 60, y + barH / 2);
    });

    // Center line
    ctx.strokeStyle = '#ffffff20';
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(midX, 20);
    ctx.lineTo(midX, ch - 10);
    ctx.stroke();
    ctx.setLineDash([]);

    // Legend
    ctx.font = '9px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillStyle = '#0ea5e9';
    ctx.fillText('← Decreases prediction', midX - 80, 16);
    ctx.fillStyle = '#f43f5e';
    ctx.fillText('Increases prediction →', midX + 80, 16);
  }, [features]);

  useEffect(() => { draw(); }, [draw]);

  return <canvas ref={canvasRef} className="w-full" />;
}

/* ── Attention heatmap (8x8) ──────────────────────────────────── */
function AttentionGrid() {
  const cells = Array.from({ length: 64 }, () => Math.random());
  return (
    <div className="grid grid-cols-8 gap-0.5">
      {cells.map((v, i) => (
        <div
          key={i}
          className="aspect-square rounded-sm"
          style={{ backgroundColor: `rgba(139, 92, 246, ${0.1 + v * 0.8})` }}
          title={`Attention: ${(v * 100).toFixed(0)}%`}
        />
      ))}
    </div>
  );
}

export default function AIExplainability() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activePred, setActivePred] = useState(PREDICTIONS[0]);

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[1600px] mx-auto">
            <div className="mb-6">
              <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
                AI Explainability & Transparency
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">SHAP values, attention maps, and feature importance — understand every AI prediction</p>
            </div>

            {/* Prediction tabs */}
            <div className="flex gap-2 mb-6 flex-wrap">
              {PREDICTIONS.map(p => (
                <button
                  key={p.id}
                  onClick={() => setActivePred(p)}
                  className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                    activePred.id === p.id
                      ? 'bg-violet-500 text-white shadow-lg shadow-violet-500/30'
                      : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700/60'
                  }`}
                >
                  {p.name}
                </button>
              ))}
            </div>

            {/* Prediction header */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
              <GlowCard glowColor="violet" className="!p-4 text-center">
                <div className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">Prediction</div>
                <div className="text-2xl font-extrabold text-gray-800 dark:text-white">{activePred.outcome}</div>
                <div className="text-[10px] text-gray-400 mt-0.5">{activePred.name}</div>
              </GlowCard>
              <GlowCard glowColor="emerald" className="!p-4 text-center">
                <div className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">Model Confidence</div>
                <div className={`text-2xl font-extrabold ${activePred.confidence >= 90 ? 'text-emerald-500' : 'text-amber-500'}`}>{activePred.confidence}%</div>
              </GlowCard>
              <GlowCard glowColor="sky" className="!p-4 text-center">
                <div className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">Features Used</div>
                <div className="text-2xl font-extrabold text-gray-800 dark:text-white">{activePred.features.length}</div>
              </GlowCard>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              {/* SHAP waterfall */}
              <div className="xl:col-span-2">
                <GlowCard glowColor="indigo" noPad className="overflow-hidden">
                  <div className="p-4 pb-2">
                    <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100">SHAP Feature Importance — Waterfall Plot</h3>
                    <p className="text-[10px] text-gray-400 mt-0.5">Each bar shows how a feature pushed the prediction up (red) or down (blue)</p>
                  </div>
                  <SHAPWaterfall features={activePred.features} />
                </GlowCard>
              </div>

              {/* Right column */}
              <div className="space-y-4">
                {/* Attention map */}
                <GlowCard glowColor="violet" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Encoder Attention Map</h3>
                  <p className="text-[10px] text-gray-400 mb-3">8×8 patch-level attention from the vision transformer encoder</p>
                  <AttentionGrid />
                  <div className="flex justify-between mt-2">
                    <span className="text-[10px] text-gray-400">Low attention</span>
                    <span className="text-[10px] text-violet-400">High attention</span>
                  </div>
                </GlowCard>

                {/* Feature categories breakdown */}
                <GlowCard glowColor="sky" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Category Impact</h3>
                  {['Clinical', 'Molecular', 'Genomic', 'Pathology', 'Treatment'].map(cat => {
                    const feats = activePred.features.filter(f => f.category === cat);
                    if (!feats.length) return null;
                    const netShap = feats.reduce((a, f) => a + f.shap, 0);
                    const isPos = netShap > 0;
                    return (
                      <div key={cat} className="flex items-center gap-2 mb-2">
                        <span className="text-xs text-gray-400 w-20">{cat}</span>
                        <div className="flex-1 flex items-center">
                          <div className="w-1/2 flex justify-end pr-1">
                            {!isPos && <div className="h-2 rounded-full bg-sky-500" style={{ width: `${Math.abs(netShap) * 400}%` }} />}
                          </div>
                          <div className="w-px h-3 bg-gray-600" />
                          <div className="w-1/2 pl-1">
                            {isPos && <div className="h-2 rounded-full bg-rose-500" style={{ width: `${Math.abs(netShap) * 400}%` }} />}
                          </div>
                        </div>
                        <span className={`text-[10px] font-bold tabular-nums w-10 text-right ${isPos ? 'text-rose-500' : 'text-sky-500'}`}>
                          {isPos ? '+' : ''}{netShap.toFixed(2)}
                        </span>
                      </div>
                    );
                  })}
                </GlowCard>

                {/* Counterfactual */}
                <GlowCard glowColor="amber" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Counterfactual Analysis</h3>
                  <p className="text-[10px] text-gray-400 mb-2">What would change the prediction most?</p>
                  <div className="space-y-2">
                    <div className="p-2 bg-emerald-500/10 rounded-lg text-xs text-emerald-600 dark:text-emerald-400">
                      If <b>PIK3CA were wild-type</b>: prediction improves by +6.2%
                    </div>
                    <div className="p-2 bg-emerald-500/10 rounded-lg text-xs text-emerald-600 dark:text-emerald-400">
                      If <b>Ki-67 were ≤ 20%</b>: prediction improves by +8.1%
                    </div>
                    <div className="p-2 bg-rose-500/10 rounded-lg text-xs text-rose-600 dark:text-rose-400">
                      If <b>HER2 were negative</b>: prediction declines by -18.4%
                    </div>
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
