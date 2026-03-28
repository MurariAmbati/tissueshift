import { useState, useEffect, useRef, useCallback } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import GlowCard from '../components/GlowCard';

/* ── Stain colour profiles ──────────────────────────────────────── */
const STAIN_PROFILES = {
  'H&E':     { tissue: '#e8b4c8', nuclei: '#4a1a6b', stroma: '#f5d5e0', bg: '#fef2f7' },
  'IHC-Ki67': { tissue: '#f0e0d0', nuclei: '#8B4513', stroma: '#e8d5c0', bg: '#faf5ef', marker: '#6f2da8' },
  'IHC-CD3':  { tissue: '#e8ddd0', nuclei: '#5a3e2e', stroma: '#d8c8b5', bg: '#f5efe8', marker: '#c0392b' },
  'PAS':      { tissue: '#d8c0d8', nuclei: '#2c1a4a', stroma: '#e8d0e8', bg: '#f5eef5', marker: '#e74c9e' },
  'Masson':   { tissue: '#c8e0c8', nuclei: '#1a3a1a', stroma: '#88b8e8', bg: '#f0f5f0', marker: '#2980b9' },
  'Silver':   { tissue: '#d8d0c0', nuclei: '#1a1a1a', stroma: '#c0b8a8', bg: '#f0ece0', marker: '#2c3e50' },
};

/* ── Synthetic tissue patch generator ────────────────────────────── */
const PATCH_SIZE = 180;
function generateCellMap(seed = 42) {
  const cells = [];
  const rng = (s) => { s = Math.sin(s) * 43758.5453; return s - Math.floor(s); };
  // Glandular structures
  for (let g = 0; g < 5; g++) {
    const gcx = 30 + rng(seed + g * 7) * (PATCH_SIZE - 60);
    const gcy = 30 + rng(seed + g * 13) * (PATCH_SIZE - 60);
    const gr = 15 + rng(seed + g * 19) * 15;
    const nCells = 12 + Math.floor(rng(seed + g * 31) * 10);
    for (let i = 0; i < nCells; i++) {
      const a = (i / nCells) * Math.PI * 2;
      const dr = gr + (rng(seed + g * 37 + i) - 0.5) * 6;
      cells.push({
        x: gcx + Math.cos(a) * dr,
        y: gcy + Math.sin(a) * dr,
        r: 3 + rng(seed + g * 41 + i) * 2,
        type: rng(seed + g * 43 + i) > 0.7 ? 'marker' : 'nuclei',
      });
    }
    // Lumen
    cells.push({ x: gcx, y: gcy, r: gr * 0.5, type: 'lumen' });
  }
  // Scattered stromal cells
  for (let i = 0; i < 40; i++) {
    cells.push({
      x: 10 + rng(seed + 200 + i) * (PATCH_SIZE - 20),
      y: 10 + rng(seed + 300 + i) * (PATCH_SIZE - 20),
      r: 2 + rng(seed + 400 + i) * 1.5,
      type: rng(seed + 500 + i) > 0.6 ? 'marker' : 'stroma',
    });
  }
  return cells;
}

/* ── GAN architecture layers ─────────────────────────────────────── */
const GAN_LAYERS = [
  { name: 'Input H&E', size: '256\u00d7256\u00d73', type: 'input' },
  { name: 'Encoder Block 1', size: '128\u00d7128\u00d764', type: 'encoder' },
  { name: 'Encoder Block 2', size: '64\u00d764\u00d7128', type: 'encoder' },
  { name: 'Encoder Block 3', size: '32\u00d732\u00d7256', type: 'encoder' },
  { name: 'Bottleneck', size: '16\u00d716\u00d7512', type: 'bottleneck' },
  { name: 'Decoder Block 1', size: '32\u00d732\u00d7256', type: 'decoder' },
  { name: 'Decoder Block 2', size: '64\u00d764\u00d7128', type: 'decoder' },
  { name: 'Decoder Block 3', size: '128\u00d7128\u00d764', type: 'decoder' },
  { name: 'Output IHC', size: '256\u00d7256\u00d73', type: 'output' },
];

const LAYER_COLORS = {
  input: '#10b981',
  encoder: '#0ea5e9',
  bottleneck: '#f59e0b',
  decoder: '#a78bfa',
  output: '#f43f5e',
};

/* ── Quality metrics ─────────────────────────────────────────────── */
const METRICS = [
  { stain: 'IHC-Ki67', ssim: 0.934, psnr: 31.2, fid: 18.7, pearson: 0.961 },
  { stain: 'IHC-CD3', ssim: 0.918, psnr: 29.8, fid: 22.3, pearson: 0.943 },
  { stain: 'PAS', ssim: 0.951, psnr: 33.1, fid: 14.2, pearson: 0.972 },
  { stain: 'Masson', ssim: 0.927, psnr: 30.5, fid: 19.8, pearson: 0.955 },
  { stain: 'Silver', ssim: 0.911, psnr: 28.9, fid: 24.1, pearson: 0.938 },
];

export default function VirtualStaining() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sourceStain] = useState('H&E');
  const [targetStain, setTargetStain] = useState('IHC-Ki67');
  const [transferProgress, setTransferProgress] = useState(100);
  const [sliderPos, setSliderPos] = useState(50);
  const sourceCanvasRef = useRef(null);
  const targetCanvasRef = useRef(null);
  const cellMap = useRef(generateCellMap());
  const dragging = useRef(false);

  /* ── Render a stained tissue patch ──────────────────────── */
  const renderPatch = useCallback((canvas, stainKey, progress = 100) => {
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width = PATCH_SIZE * 2;
    const H = canvas.height = PATCH_SIZE * 2;
    ctx.scale(2, 2);
    const profile = STAIN_PROFILES[stainKey];

    // Background
    ctx.fillStyle = profile.bg;
    ctx.fillRect(0, 0, PATCH_SIZE, PATCH_SIZE);

    // Tissue base
    ctx.fillStyle = profile.tissue;
    ctx.globalAlpha = 0.3;
    ctx.fillRect(5, 5, PATCH_SIZE - 10, PATCH_SIZE - 10);
    ctx.globalAlpha = 1;

    cellMap.current.forEach(cell => {
      if (cell.type === 'lumen') {
        ctx.fillStyle = profile.bg;
        ctx.globalAlpha = 0.8;
        ctx.beginPath();
        ctx.arc(cell.x, cell.y, cell.r, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
      } else if (cell.type === 'stroma') {
        ctx.fillStyle = profile.stroma;
        ctx.globalAlpha = 0.6;
        ctx.beginPath();
        ctx.arc(cell.x, cell.y, cell.r, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
      } else if (cell.type === 'marker' && profile.marker) {
        ctx.fillStyle = profile.marker;
        ctx.globalAlpha = progress / 100;
        ctx.beginPath();
        ctx.arc(cell.x, cell.y, cell.r + 0.5, 0, Math.PI * 2);
        ctx.fill();
        // Nuclear halo
        ctx.strokeStyle = profile.marker;
        ctx.lineWidth = 0.5;
        ctx.globalAlpha = (progress / 100) * 0.3;
        ctx.beginPath();
        ctx.arc(cell.x, cell.y, cell.r + 3, 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = 1;
      } else {
        ctx.fillStyle = profile.nuclei;
        ctx.globalAlpha = 0.8;
        ctx.beginPath();
        ctx.arc(cell.x, cell.y, cell.r, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
      }
    });
  }, []);

  useEffect(() => {
    renderPatch(sourceCanvasRef.current, sourceStain);
    renderPatch(targetCanvasRef.current, targetStain, transferProgress);
  }, [sourceStain, targetStain, transferProgress, renderPatch]);

  /* ── Simulate stain transfer ──────────────────────────────── */
  const runTransfer = () => {
    setTransferProgress(0);
    let p = 0;
    const iv = setInterval(() => {
      p += 2;
      setTransferProgress(Math.min(p, 100));
      if (p >= 100) clearInterval(iv);
    }, 30);
  };

  const currentMetric = METRICS.find(m => m.stain === targetStain);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
            <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-1">Virtual Staining</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
              GAN-based digital stain transfer &middot; Pix2Pix architecture &middot; No physical re-staining required
            </p>

            <div className="grid grid-cols-12 gap-6">
              {/* Before / After comparison */}
              <div className="col-span-12 lg:col-span-8">
                <GlowCard>
                  <div className="p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100">Stain Comparison</h2>
                      <div className="flex items-center gap-2">
                        <select
                          value={targetStain}
                          onChange={e => { setTargetStain(e.target.value); runTransfer(); }}
                          className="text-xs rounded border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 py-1 px-2"
                        >
                          {Object.keys(STAIN_PROFILES).filter(s => s !== 'H&E').map(s => (
                            <option key={s} value={s}>{s}</option>
                          ))}
                        </select>
                        <button
                          onClick={runTransfer}
                          className="px-3 py-1.5 rounded text-xs font-semibold bg-violet-600 text-white hover:bg-violet-700 transition"
                        >
                          Re-run Transfer
                        </button>
                      </div>
                    </div>

                    {/* Side by side */}
                    <div
                      className="relative overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700"
                      style={{ height: PATCH_SIZE + 32 }}
                      onMouseMove={e => {
                        if (!dragging.current) return;
                        const rect = e.currentTarget.getBoundingClientRect();
                        setSliderPos(Math.max(5, Math.min(95, ((e.clientX - rect.left) / rect.width) * 100)));
                      }}
                      onMouseUp={() => { dragging.current = false; }}
                      onMouseLeave={() => { dragging.current = false; }}
                    >
                      {/* Source */}
                      <div className="absolute inset-0 flex items-center justify-center bg-gray-50 dark:bg-gray-900" style={{ clipPath: `inset(0 ${100 - sliderPos}% 0 0)` }}>
                        <canvas ref={sourceCanvasRef} style={{ width: PATCH_SIZE, height: PATCH_SIZE, imageRendering: 'pixelated' }} />
                      </div>
                      {/* Target */}
                      <div className="absolute inset-0 flex items-center justify-center bg-gray-50 dark:bg-gray-900" style={{ clipPath: `inset(0 0 0 ${sliderPos}%)` }}>
                        <canvas ref={targetCanvasRef} style={{ width: PATCH_SIZE, height: PATCH_SIZE, imageRendering: 'pixelated' }} />
                      </div>
                      {/* Slider handle */}
                      <div
                        className="absolute top-0 bottom-0 w-0.5 bg-white cursor-col-resize z-10"
                        style={{ left: `${sliderPos}%` }}
                        onMouseDown={() => { dragging.current = true; }}
                      >
                        <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-6 h-6 rounded-full bg-white border-2 border-violet-500 flex items-center justify-center">
                          <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M3 2L1 5l2 3M7 2l2 3-2 3" stroke="#7c3aed" strokeWidth="1.5" strokeLinecap="round" /></svg>
                        </div>
                      </div>
                      {/* Labels */}
                      <div className="absolute top-2 left-3 px-2 py-0.5 rounded bg-gray-900/60 text-white text-[10px] font-medium">{sourceStain}</div>
                      <div className="absolute top-2 right-3 px-2 py-0.5 rounded bg-gray-900/60 text-white text-[10px] font-medium">{targetStain}</div>
                    </div>

                    {/* Progress bar */}
                    {transferProgress < 100 && (
                      <div className="mt-3">
                        <div className="flex justify-between text-[10px] text-gray-500 mb-1">
                          <span>Transfer in progress...</span>
                          <span>{transferProgress}%</span>
                        </div>
                        <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                          <div className="h-full bg-violet-500 rounded-full transition-all" style={{ width: `${transferProgress}%` }} />
                        </div>
                      </div>
                    )}
                  </div>
                </GlowCard>

                {/* GAN Architecture */}
                <GlowCard className="mt-6">
                  <div className="p-4">
                    <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-4">Generator Architecture (U-Net + Pix2Pix)</h2>
                    <div className="flex items-end gap-1 justify-center" style={{ height: 120 }}>
                      {GAN_LAYERS.map((layer, i) => {
                        const sizes = layer.size.split('\u00d7');
                        const dim = parseInt(sizes[0]);
                        const h = (dim / 256) * 100;
                        return (
                          <div key={i} className="flex flex-col items-center gap-1" style={{ flex: 1 }}>
                            <div
                              className="w-full rounded-t"
                              style={{ height: `${h}%`, minHeight: 12, backgroundColor: LAYER_COLORS[layer.type], opacity: 0.8 }}
                            />
                            <span className="text-[8px] text-gray-500 text-center leading-tight">{layer.name}</span>
                            <span className="text-[7px] text-gray-400 text-center">{layer.size}</span>
                          </div>
                        );
                      })}
                    </div>
                    {/* Skip connections */}
                    <div className="flex justify-center gap-6 mt-2">
                      {Object.entries(LAYER_COLORS).map(([type, color]) => (
                        <div key={type} className="flex items-center gap-1">
                          <div className="w-2.5 h-2.5 rounded" style={{ backgroundColor: color }} />
                          <span className="text-[10px] text-gray-500 capitalize">{type}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </GlowCard>
              </div>

              {/* Right panel */}
              <div className="col-span-12 lg:col-span-4 flex flex-col gap-4">
                {/* Quality metrics */}
                <GlowCard>
                  <div className="p-4">
                    <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3">Transfer Quality ({targetStain})</h2>
                    {currentMetric && (
                      <div className="space-y-3">
                        {[
                          { label: 'SSIM', value: currentMetric.ssim, max: 1, fmt: v => v.toFixed(3) },
                          { label: 'PSNR', value: currentMetric.psnr, max: 40, fmt: v => `${v.toFixed(1)} dB` },
                          { label: 'FID', value: currentMetric.fid, max: 50, fmt: v => v.toFixed(1), inverted: true },
                          { label: 'Pearson r', value: currentMetric.pearson, max: 1, fmt: v => v.toFixed(3) },
                        ].map(m => (
                          <div key={m.label}>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-gray-500 dark:text-gray-400">{m.label}</span>
                              <span className="font-semibold text-gray-800 dark:text-gray-100">{m.fmt(m.value)}</span>
                            </div>
                            <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full ${m.inverted ? 'bg-amber-500' : 'bg-teal-500'}`}
                                style={{ width: `${(m.inverted ? 1 - m.value / m.max : m.value / m.max) * 100}%` }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </GlowCard>

                {/* All stains comparison table */}
                <GlowCard>
                  <div className="p-4">
                    <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3">Cross-Stain Performance</h2>
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-gray-500 dark:text-gray-400">
                          <th className="text-left pb-2 font-medium">Stain</th>
                          <th className="text-right pb-2 font-medium">SSIM</th>
                          <th className="text-right pb-2 font-medium">FID</th>
                        </tr>
                      </thead>
                      <tbody>
                        {METRICS.map(m => (
                          <tr key={m.stain} className={`border-t border-gray-100 dark:border-gray-700/50 ${m.stain === targetStain ? 'bg-violet-50 dark:bg-violet-500/10' : ''}`}>
                            <td className="py-1.5 font-medium text-gray-700 dark:text-gray-300">{m.stain}</td>
                            <td className="py-1.5 text-right text-gray-600 dark:text-gray-400">{m.ssim.toFixed(3)}</td>
                            <td className="py-1.5 text-right text-gray-600 dark:text-gray-400">{m.fid.toFixed(1)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </GlowCard>

                {/* Stain color palette */}
                <GlowCard>
                  <div className="p-4">
                    <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3">Stain Color Profiles</h2>
                    <div className="space-y-2">
                      {Object.entries(STAIN_PROFILES).map(([name, p]) => (
                        <div key={name} className="flex items-center gap-2">
                          <div className="flex gap-0.5">
                            {[p.bg, p.tissue, p.nuclei, p.stroma, p.marker].filter(Boolean).map((c, i) => (
                              <div key={i} className="w-4 h-4 rounded border border-gray-200 dark:border-gray-600" style={{ backgroundColor: c }} />
                            ))}
                          </div>
                          <span className="text-xs text-gray-600 dark:text-gray-400">{name}</span>
                        </div>
                      ))}
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
