import { useState, useEffect, useRef, useCallback } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import GlowCard from '../components/GlowCard';

/* ── Data modalities as interconnected nodes ─────────────────────── */
const MODALITIES = [
  { id: 'he', label: 'H&E\nHistology', x: 0.5, y: 0.15, color: '#f43f5e', icon: 'HE', desc: 'Hematoxylin & Eosin whole-slide images at 40x magnification' },
  { id: 'genomic', label: 'Genomics\n(WGS/WES)', x: 0.18, y: 0.35, color: '#8b5cf6', icon: 'GN', desc: 'Whole-genome/exome sequencing — mutations, CNV, SV' },
  { id: 'transcriptomic', label: 'Transcriptomics\n(RNA-seq)', x: 0.82, y: 0.35, color: '#0ea5e9', icon: 'TX', desc: 'Bulk + single-cell RNA-seq gene expression profiles' },
  { id: 'proteomic', label: 'Proteomics\n(RPPA/MS)', x: 0.15, y: 0.65, color: '#10b981', icon: 'PR', desc: 'Reverse-phase protein array & mass spectrometry' },
  { id: 'metabolomic', label: 'Metabolomics', x: 0.85, y: 0.65, color: '#f59e0b', icon: 'MB', desc: 'Metabolite profiling via LC-MS/MS' },
  { id: 'spatial', label: 'Spatial\nTranscriptomics', x: 0.35, y: 0.50, color: '#ec4899', icon: 'SP', desc: 'Visium / MERFISH spatially-resolved gene expression' },
  { id: 'clinical', label: 'Clinical\nData', x: 0.65, y: 0.50, color: '#6366f1', icon: 'CL', desc: 'EHR records, staging, treatment history, outcomes' },
  { id: 'imaging', label: 'Radiology\n(MRI/CT)', x: 0.50, y: 0.78, color: '#14b8a6', icon: 'IM', desc: 'Breast MRI, CT, PET-CT imaging data' },
  { id: 'worldmodel', label: 'TissueShift\nWorld Model', x: 0.50, y: 0.48, color: '#fff', icon: 'TS', desc: 'The central integration hub — fuses all modalities', special: true },
];

const EDGES = [
  { from: 'he', to: 'worldmodel', width: 3 },
  { from: 'genomic', to: 'worldmodel', width: 2.5 },
  { from: 'transcriptomic', to: 'worldmodel', width: 2.5 },
  { from: 'proteomic', to: 'worldmodel', width: 2 },
  { from: 'metabolomic', to: 'worldmodel', width: 1.5 },
  { from: 'spatial', to: 'worldmodel', width: 2 },
  { from: 'clinical', to: 'worldmodel', width: 2.5 },
  { from: 'imaging', to: 'worldmodel', width: 2 },
  { from: 'he', to: 'spatial', width: 1 },
  { from: 'genomic', to: 'transcriptomic', width: 1 },
  { from: 'transcriptomic', to: 'proteomic', width: 1 },
  { from: 'proteomic', to: 'metabolomic', width: 0.8 },
];

const OUTPUTS = [
  { label: 'Subtype Prediction', conf: '96.1%', color: '#8b5cf6' },
  { label: 'Risk Stratification', conf: '94.3%', color: '#f43f5e' },
  { label: 'Treatment Response', conf: '89.7%', color: '#10b981' },
  { label: 'Survival Forecast', conf: '91.2%', color: '#0ea5e9' },
  { label: 'Biomarker Discovery', conf: '87.4%', color: '#f59e0b' },
  { label: 'Drug Sensitivity', conf: '85.8%', color: '#ec4899' },
];

export default function MultiOmicsHub() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const canvasRef = useRef(null);
  const [selected, setSelected] = useState(null);
  const frameRef = useRef(0);
  const nodesMap = Object.fromEntries(MODALITIES.map(m => [m.id, m]));

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const cw = canvas.offsetWidth;
    const ch = canvas.offsetHeight;
    canvas.width = cw * devicePixelRatio;
    canvas.height = ch * devicePixelRatio;
    ctx.scale(devicePixelRatio, devicePixelRatio);

    ctx.fillStyle = '#070714';
    ctx.fillRect(0, 0, cw, ch);

    const t = performance.now() / 1000;

    // Edges with flowing particles
    for (const edge of EDGES) {
      const from = nodesMap[edge.from];
      const to = nodesMap[edge.to];
      const x1 = from.x * cw, y1 = from.y * ch;
      const x2 = to.x * cw, y2 = to.y * ch;

      // Line
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      const grad = ctx.createLinearGradient(x1, y1, x2, y2);
      grad.addColorStop(0, from.color + '40');
      grad.addColorStop(1, to.color + '40');
      ctx.strokeStyle = grad;
      ctx.lineWidth = edge.width;
      ctx.stroke();

      // Flowing particle
      const speed = 0.3 + edge.width * 0.1;
      const phase = (t * speed + edge.from.length * 0.5) % 1;
      const px = x1 + (x2 - x1) * phase;
      const py = y1 + (y2 - y1) * phase;
      ctx.beginPath();
      ctx.arc(px, py, edge.width + 1, 0, Math.PI * 2);
      ctx.fillStyle = from.color + 'cc';
      ctx.shadowColor = from.color;
      ctx.shadowBlur = 10;
      ctx.fill();
      ctx.shadowBlur = 0;
    }

    // Nodes
    for (const node of MODALITIES) {
      const px = node.x * cw;
      const py = node.y * ch;
      const isCenter = node.special;
      const baseR = isCenter ? 42 : 30;
      const pulse = isCenter ? 1 + Math.sin(t * 2) * 0.08 : 1;
      const r = baseR * pulse;

      // Outer glow
      const glow = ctx.createRadialGradient(px, py, 0, px, py, r * 2);
      glow.addColorStop(0, (isCenter ? '#8b5cf6' : node.color) + '30');
      glow.addColorStop(1, 'transparent');
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(px, py, r * 2, 0, Math.PI * 2);
      ctx.fill();

      // Node circle
      ctx.beginPath();
      ctx.arc(px, py, r, 0, Math.PI * 2);
      if (isCenter) {
        const cGrad = ctx.createRadialGradient(px, py, 0, px, py, r);
        cGrad.addColorStop(0, '#8b5cf680');
        cGrad.addColorStop(1, '#6366f140');
        ctx.fillStyle = cGrad;
      } else {
        ctx.fillStyle = node.color + '25';
      }
      ctx.fill();
      ctx.strokeStyle = (isCenter ? '#8b5cf6' : node.color) + '80';
      ctx.lineWidth = isCenter ? 2 : 1.5;
      ctx.stroke();

      // Icon
      ctx.font = `${isCenter ? 22 : 18}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(node.icon, px, py - (isCenter ? 2 : 1));

      // Label
      ctx.font = `${isCenter ? 'bold 11' : '10'}px Inter, sans-serif`;
      ctx.fillStyle = isCenter ? '#e2e8f0' : node.color + 'dd';
      const lines = node.label.split('\n');
      lines.forEach((line, li) => {
        ctx.fillText(line, px, py + r + 12 + li * 13);
      });
      ctx.textAlign = 'start';

      // Selected ring
      if (selected && selected.id === node.id) {
        ctx.beginPath();
        ctx.arc(px, py, r + 6, 0, Math.PI * 2);
        ctx.strokeStyle = '#ffffff80';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.setLineDash([]);
      }
    }

    frameRef.current = requestAnimationFrame(draw);
  }, [selected]);

  useEffect(() => {
    frameRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frameRef.current);
  }, [draw]);

  const handleClick = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) / rect.width;
    const my = (e.clientY - rect.top) / rect.height;
    let closest = null, minD = Infinity;
    for (const n of MODALITIES) {
      const d = Math.hypot(n.x - mx, n.y - my);
      if (d < minD) { minD = d; closest = n; }
    }
    setSelected(minD < 0.08 ? closest : null);
  };

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[1600px] mx-auto">
            <div className="mb-6">
              <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
                Multi-Omics Integration Hub
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">8 data modalities converging into TissueShift's world model — live data flow visualization</p>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
              <div className="xl:col-span-3">
                <GlowCard glowColor="indigo" noPad className="overflow-hidden">
                  <canvas ref={canvasRef} className="w-full cursor-pointer" style={{ height: 520 }} onClick={handleClick} />
                </GlowCard>
              </div>

              <div className="space-y-4">
                {selected ? (
                  <GlowCard glowColor="violet" className="!p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-sm font-bold text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 w-8 h-8 rounded-lg flex items-center justify-center">{selected.icon}</span>
                      <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100">{selected.label.replace('\n', ' ')}</h3>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">{selected.desc}</p>
                    <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700/60 text-xs">
                      <span className="text-gray-400">Connections:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {EDGES.filter(e => e.from === selected.id || e.to === selected.id).map(e => {
                          const other = e.from === selected.id ? e.to : e.from;
                          const node = nodesMap[other];
                          return (
                            <span key={other} className="px-2 py-0.5 rounded-full text-[10px] font-medium" style={{ backgroundColor: node.color + '20', color: node.color }}>
                              {node.label.split('\n')[0]}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  </GlowCard>
                ) : (
                  <GlowCard glowColor="violet" className="!p-4">
                    <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-2">Click a node to explore</h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Each node represents a data modality. The central hub is the TissueShift World Model that integrates all signals.</p>
                  </GlowCard>
                )}

                {/* Model Outputs */}
                <GlowCard glowColor="emerald" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Integrated Outputs</h3>
                  <div className="space-y-2">
                    {OUTPUTS.map(o => (
                      <div key={o.label} className="flex items-center gap-2">
                        <div className="flex-1">
                          <div className="text-xs font-medium text-gray-700 dark:text-gray-200">{o.label}</div>
                          <div className="mt-1 h-1.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                            <div className="h-full rounded-full transition-all duration-1000" style={{ width: o.conf, backgroundColor: o.color }} />
                          </div>
                        </div>
                        <span className="text-xs font-bold tabular-nums" style={{ color: o.color }}>{o.conf}</span>
                      </div>
                    ))}
                  </div>
                </GlowCard>

                {/* Architecture */}
                <GlowCard glowColor="sky" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-2">Architecture</h3>
                  <div className="space-y-1 text-xs text-gray-500 dark:text-gray-400">
                    <div>Encoder: Multi-Resolution Attention</div>
                    <div>Integration: Cross-Modal Transformer</div>
                    <div>Dynamics: Neural ODE (torchdiffeq)</div>
                    <div>Uncertainty: Conformal + Ensemble</div>
                    <div>Parameters: 847M</div>
                    <div>Training: Federated (5 sites)</div>
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
