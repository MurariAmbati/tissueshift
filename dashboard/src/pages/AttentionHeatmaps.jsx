import { useState, useEffect, useRef, useCallback } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import GlowCard from '../components/GlowCard';

/* ── Simulated tissue patches with attention weights ─────────────── */
const GRID = 12; // 12x12 patches
const PATCH_SIZE_UM = 256; // microns per patch at 20x

function generateAttention(seed = 42, mode = 'tumor') {
  const rng = (i) => { const s = Math.sin(i * 127.1 + seed) * 43758.5; return s - Math.floor(s); };
  const grid = [];
  for (let r = 0; r < GRID; r++) {
    const row = [];
    for (let c = 0; c < GRID; c++) {
      const dx = (c - GRID / 2 + 0.5) / (GRID / 2);
      const dy = (r - GRID / 2 + 0.5) / (GRID / 2);
      const dist = Math.sqrt(dx * dx + dy * dy);
      let base;
      if (mode === 'tumor') {
        base = Math.max(0, 1 - dist * 1.2) * 0.8 + rng(r * GRID + c) * 0.2;
      } else if (mode === 'margin') {
        const ring = Math.abs(dist - 0.5);
        base = Math.max(0, 1 - ring * 4) * 0.7 + rng(r * GRID + c + 100) * 0.2;
      } else {
        base = rng(r * GRID + c + 200) * 0.4;
        if (r > GRID * 0.3 && r < GRID * 0.7 && c > GRID * 0.4 && c < GRID * 0.8) base += 0.5;
      }
      row.push(Math.max(0, Math.min(1, base)));
    }
    grid.push(row);
  }
  return grid;
}

const ATTENTION_HEADS = [
  { key: 'tumor', label: 'Tumor Core', desc: 'Concentrates on central tumor mass', seed: 42 },
  { key: 'margin', label: 'Invasive Margin', desc: 'Attention at tumor-stroma boundary', seed: 88 },
  { key: 'til', label: 'TIL Infiltrate', desc: 'Highlights immune cell clusters', seed: 137 },
];

/* ── Model layers with attention viz ─────────────────────────────── */
const LAYERS = [
  { name: 'Patch Embedding', params: '3.2M', attn: false },
  { name: 'Transformer Block 1', params: '7.1M', attn: true },
  { name: 'Transformer Block 2', params: '7.1M', attn: true },
  { name: 'Transformer Block 3', params: '7.1M', attn: true },
  { name: 'Transformer Block 4', params: '7.1M', attn: true },
  { name: 'Global Attention Pool', params: '1.2M', attn: true },
  { name: 'Classification Head', params: '0.4M', attn: false },
];

/* ── Classification results ──────────────────────────────────────── */
const PREDICTIONS = [
  { label: 'Invasive Ductal Carcinoma', confidence: 0.847 },
  { label: 'Ductal Carcinoma In Situ', confidence: 0.098 },
  { label: 'Lobular Carcinoma', confidence: 0.031 },
  { label: 'Benign / Normal', confidence: 0.024 },
];

/* ── Patch-level statistics ──────────────────────────────────────── */
function computePatchStats(grid) {
  let sum = 0, max = 0, highCount = 0;
  const total = GRID * GRID;
  grid.forEach(row => row.forEach(v => {
    sum += v;
    if (v > max) max = v;
    if (v > 0.5) highCount++;
  }));
  return {
    mean: (sum / total).toFixed(3),
    max: max.toFixed(3),
    highFraction: ((highCount / total) * 100).toFixed(1),
    entropy: (-(sum / total) * Math.log2(sum / total + 0.001)).toFixed(3),
  };
}

export default function AttentionHeatmaps() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const canvasRef = useRef(null);
  const [activeHead, setActiveHead] = useState('tumor');
  const [opacity, setOpacity] = useState(0.7);
  const [colormap, setColormap] = useState('viridis');
  const [hoveredPatch, setHoveredPatch] = useState(null);
  const [selectedLayer, setSelectedLayer] = useState(1);

  const grid = generateAttention(ATTENTION_HEADS.find(h => h.key === activeHead)?.seed || 42, activeHead);
  const patchStats = computePatchStats(grid);

  /* ── Colormap functions ─────────────────────────────────── */
  const colormaps = {
    viridis: v => {
      const r = Math.round(68 + v * 185);
      const g = Math.round(1 + v * 205 * (1 - v * 0.3));
      const b = Math.round(84 + v * 60 - v * v * 140);
      return `rgb(${r},${g},${b})`;
    },
    hot: v => {
      const r = Math.round(Math.min(255, v * 3 * 255));
      const g = Math.round(Math.max(0, Math.min(255, (v - 0.33) * 3 * 255)));
      const b = Math.round(Math.max(0, Math.min(255, (v - 0.66) * 3 * 255)));
      return `rgb(${r},${g},${b})`;
    },
    coolwarm: v => {
      const r = Math.round(59 + v * 196);
      const g = Math.round(76 + Math.sin(v * Math.PI) * 120);
      const b = Math.round(227 - v * 186);
      return `rgb(${r},${g},${b})`;
    },
  };

  /* ── Canvas render ─────────────────────────────────────────── */
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width = canvas.offsetWidth * 2;
    const H = canvas.height = canvas.offsetHeight * 2;
    ctx.scale(2, 2);
    const w = W / 2, h = H / 2;
    ctx.clearRect(0, 0, w, h);

    const pad = 16;
    const size = Math.min(w - pad * 2, h - pad * 2);
    const ox = (w - size) / 2, oy = (h - size) / 2;
    const cellW = size / GRID, cellH = size / GRID;
    const cmFn = colormaps[colormap];

    // Background tissue simulation (pink for H&E)
    ctx.fillStyle = '#f9e8ee';
    ctx.fillRect(ox, oy, size, size);

    // Fake tissue texture
    for (let r = 0; r < GRID; r++) {
      for (let c = 0; c < GRID; c++) {
        const px = ox + c * cellW, py = oy + r * cellH;
        // tissue pattern
        ctx.fillStyle = r % 2 === c % 2 ? '#f5dce5' : '#f0d0db';
        ctx.fillRect(px, py, cellW, cellH);
      }
    }

    // Attention overlay
    for (let r = 0; r < GRID; r++) {
      for (let c = 0; c < GRID; c++) {
        const v = grid[r][c];
        const px = ox + c * cellW, py = oy + r * cellH;
        ctx.fillStyle = cmFn(v);
        ctx.globalAlpha = opacity * v;
        ctx.fillRect(px, py, cellW, cellH);
        ctx.globalAlpha = 1;
      }
    }

    // Grid lines
    ctx.strokeStyle = 'rgba(255,255,255,0.2)';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= GRID; i++) {
      ctx.beginPath(); ctx.moveTo(ox + i * cellW, oy); ctx.lineTo(ox + i * cellW, oy + size); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(ox, oy + i * cellH); ctx.lineTo(ox + size, oy + i * cellH); ctx.stroke();
    }

    // Hovered patch highlight
    if (hoveredPatch) {
      const { r, c } = hoveredPatch;
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.strokeRect(ox + c * cellW, oy + r * cellH, cellW, cellH);
      // Tooltip
      const v = grid[r][c];
      const label = `[${r},${c}] w=${v.toFixed(3)}`;
      ctx.font = '11px Inter, sans-serif';
      const tw = ctx.measureText(label).width;
      const ttx = Math.min(ox + c * cellW + cellW, w - tw - 12);
      const tty = oy + r * cellH - 6;
      ctx.fillStyle = 'rgba(0,0,0,0.8)';
      ctx.roundRect(ttx - 4, tty - 13, tw + 8, 18, 4);
      ctx.fill();
      ctx.fillStyle = '#fff';
      ctx.fillText(label, ttx, tty);
    }

    // Colorbar
    const cbX = ox + size + 12, cbY = oy, cbW = 12, cbH = size;
    for (let i = 0; i < cbH; i++) {
      const v = 1 - i / cbH;
      ctx.fillStyle = cmFn(v);
      ctx.fillRect(cbX, cbY + i, cbW, 1);
    }
    ctx.strokeStyle = '#9ca3af';
    ctx.lineWidth = 0.5;
    ctx.strokeRect(cbX, cbY, cbW, cbH);
    ctx.fillStyle = '#9ca3af';
    ctx.font = '9px Inter, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText('1.0', cbX + cbW + 4, cbY + 8);
    ctx.fillText('0.5', cbX + cbW + 4, cbY + cbH / 2 + 3);
    ctx.fillText('0.0', cbX + cbW + 4, cbY + cbH);
  }, [grid, opacity, colormap, hoveredPatch]);

  useEffect(() => { draw(); }, [draw]);

  const handleMouseMove = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const w = rect.width, h = rect.height;
    const pad = 16;
    const size = Math.min(w - pad * 2, h - pad * 2);
    const ox = (w - size) / 2, oy = (h - size) / 2;
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const c = Math.floor((mx - ox) / (size / GRID));
    const r = Math.floor((my - oy) / (size / GRID));
    if (r >= 0 && r < GRID && c >= 0 && c < GRID) {
      setHoveredPatch({ r, c });
    } else {
      setHoveredPatch(null);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
            <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-1">Attention Heatmaps</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
              Explainable AI &middot; Multi-head self-attention visualization &middot; {GRID}\u00d7{GRID} patch grid ({PATCH_SIZE_UM}\u00b5m per patch)
            </p>

            <div className="grid grid-cols-12 gap-6">
              {/* Heatmap canvas */}
              <div className="col-span-12 xl:col-span-8">
                <GlowCard>
                  <div className="p-4">
                    <div className="flex flex-wrap items-center gap-2 mb-3">
                      {ATTENTION_HEADS.map(h => (
                        <button
                          key={h.key}
                          onClick={() => setActiveHead(h.key)}
                          className={`px-3 py-1.5 rounded text-xs font-semibold transition ${
                            activeHead === h.key ? 'bg-violet-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200'
                          }`}
                        >{h.label}</button>
                      ))}
                      <div className="h-5 w-px bg-gray-300 dark:bg-gray-600 mx-1" />
                      <select
                        value={colormap}
                        onChange={e => setColormap(e.target.value)}
                        className="text-xs rounded border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 py-1 px-2"
                      >
                        {Object.keys(colormaps).map(cm => (
                          <option key={cm} value={cm}>{cm}</option>
                        ))}
                      </select>
                      <div className="flex items-center gap-1.5 ml-auto">
                        <span className="text-xs text-gray-500">Opacity</span>
                        <input type="range" min={0} max={100} value={opacity * 100} onChange={e => setOpacity(e.target.value / 100)} className="w-20 accent-violet-500" />
                        <span className="text-xs text-gray-600 dark:text-gray-400 w-8">{Math.round(opacity * 100)}%</span>
                      </div>
                    </div>
                    <canvas
                      ref={canvasRef}
                      className="w-full rounded-lg bg-gray-50 dark:bg-gray-900 cursor-crosshair"
                      style={{ height: 440 }}
                      onMouseMove={handleMouseMove}
                      onMouseLeave={() => setHoveredPatch(null)}
                    />
                    <p className="text-[10px] text-gray-400 mt-2">
                      {ATTENTION_HEADS.find(h => h.key === activeHead)?.desc} &middot; Hover patch for attention weight
                    </p>
                  </div>
                </GlowCard>
              </div>

              {/* Right panel */}
              <div className="col-span-12 xl:col-span-4 flex flex-col gap-4">
                {/* Classification output */}
                <GlowCard>
                  <div className="p-4">
                    <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3">Classification Output</h2>
                    <div className="space-y-2">
                      {PREDICTIONS.map((p, i) => (
                        <div key={p.label}>
                          <div className="flex justify-between text-xs mb-0.5">
                            <span className={`${i === 0 ? 'font-semibold text-gray-800 dark:text-gray-100' : 'text-gray-500 dark:text-gray-400'}`}>{p.label}</span>
                            <span className="font-semibold text-gray-700 dark:text-gray-300">{(p.confidence * 100).toFixed(1)}%</span>
                          </div>
                          <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${i === 0 ? 'bg-violet-500' : 'bg-gray-400'}`} style={{ width: `${p.confidence * 100}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </GlowCard>

                {/* Attention stats */}
                <GlowCard>
                  <div className="p-4">
                    <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3">Attention Statistics</h2>
                    <dl className="space-y-2">
                      {[
                        { label: 'Mean Attention', value: patchStats.mean },
                        { label: 'Max Attention', value: patchStats.max },
                        { label: 'High-Attention Patches', value: `${patchStats.highFraction}%` },
                        { label: 'Attention Entropy', value: patchStats.entropy },
                        { label: 'Total Patches', value: `${GRID * GRID}` },
                        { label: 'Patch Size', value: `${PATCH_SIZE_UM}\u00b5m \u00d7 ${PATCH_SIZE_UM}\u00b5m` },
                      ].map(row => (
                        <div key={row.label} className="flex justify-between">
                          <dt className="text-xs text-gray-500 dark:text-gray-400">{row.label}</dt>
                          <dd className="text-xs font-semibold text-gray-800 dark:text-gray-100">{row.value}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                </GlowCard>

                {/* Network architecture */}
                <GlowCard>
                  <div className="p-4">
                    <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3">Vision Transformer Architecture</h2>
                    <ol className="space-y-1.5">
                      {LAYERS.map((layer, i) => (
                        <li
                          key={i}
                          onClick={() => layer.attn && setSelectedLayer(i)}
                          className={`flex items-center gap-2 p-1.5 rounded cursor-pointer transition ${
                            i === selectedLayer ? 'bg-violet-50 dark:bg-violet-500/10' : 'hover:bg-gray-50 dark:hover:bg-gray-800'
                          }`}
                        >
                          <span className="flex items-center justify-center w-5 h-5 rounded bg-violet-100 dark:bg-violet-500/20 text-violet-600 dark:text-violet-400 text-[10px] font-bold shrink-0">{i + 1}</span>
                          <div className="flex-1 min-w-0">
                            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{layer.name}</span>
                          </div>
                          <span className="text-[10px] text-gray-400">{layer.params}</span>
                          {layer.attn && <span className="text-[9px] px-1 py-0.5 rounded bg-teal-50 dark:bg-teal-500/10 text-teal-600 dark:text-teal-400 font-medium">ATTN</span>}
                        </li>
                      ))}
                    </ol>
                    <p className="text-[10px] text-gray-400 mt-2">Total: 39.4M parameters &middot; ViT-Small</p>
                  </div>
                </GlowCard>

                {/* Head descriptions */}
                <GlowCard>
                  <div className="p-4">
                    <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3">Attention Heads</h2>
                    <div className="space-y-2">
                      {ATTENTION_HEADS.map(h => (
                        <div
                          key={h.key}
                          className={`p-2 rounded-lg border transition cursor-pointer ${
                            activeHead === h.key
                              ? 'border-violet-300 dark:border-violet-500/30 bg-violet-50 dark:bg-violet-500/5'
                              : 'border-gray-100 dark:border-gray-700'
                          }`}
                          onClick={() => setActiveHead(h.key)}
                        >
                          <span className="text-xs font-medium text-gray-800 dark:text-gray-100">{h.label}</span>
                          <p className="text-[10px] text-gray-500 mt-0.5">{h.desc}</p>
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
