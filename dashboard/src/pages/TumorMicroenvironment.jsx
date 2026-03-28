import { useState, useEffect, useRef, useCallback } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import GlowCard from '../components/GlowCard';
import PulseRing from '../components/PulseRing';

/* ── Cell types & their visual properties ────────────────────────── */
const CELL_TYPES = {
  tumor:   { color: '#f43f5e', label: 'Tumor Cell', radius: 6 },
  tcell:   { color: '#10b981', label: 'T-Cell (CD8+)', radius: 4 },
  bcell:   { color: '#0ea5e9', label: 'B-Cell', radius: 3.5 },
  macro:   { color: '#f59e0b', label: 'Macrophage', radius: 5.5 },
  fibro:   { color: '#a78bfa', label: 'Fibroblast', radius: 5 },
  endo:    { color: '#ec4899', label: 'Endothelial', radius: 3 },
  normal:  { color: '#94a3b8', label: 'Normal Epithelial', radius: 5 },
};

function generateCells(count = 300) {
  const types = Object.keys(CELL_TYPES);
  const weights = [0.30, 0.15, 0.08, 0.10, 0.12, 0.07, 0.18]; // distribution
  const cells = [];
  for (let i = 0; i < count; i++) {
    let r = Math.random(), cum = 0, type = types[0];
    for (let j = 0; j < weights.length; j++) {
      cum += weights[j];
      if (r <= cum) { type = types[j]; break; }
    }
    const ct = CELL_TYPES[type];
    // Cluster tumor cells toward center
    let x, y;
    if (type === 'tumor') {
      const angle = Math.random() * Math.PI * 2;
      const dist = Math.random() * 0.25 + 0.05;
      x = 0.5 + Math.cos(angle) * dist;
      y = 0.5 + Math.sin(angle) * dist;
    } else if (type === 'tcell' || type === 'macro') {
      // Immune cells near tumor boundary
      const angle = Math.random() * Math.PI * 2;
      const dist = Math.random() * 0.15 + 0.22;
      x = 0.5 + Math.cos(angle) * dist;
      y = 0.5 + Math.sin(angle) * dist;
    } else {
      x = Math.random() * 0.9 + 0.05;
      y = Math.random() * 0.9 + 0.05;
    }
    cells.push({
      id: i,
      type,
      x, y,
      vx: (Math.random() - 0.5) * 0.0003,
      vy: (Math.random() - 0.5) * 0.0003,
      radius: ct.radius + (Math.random() - 0.5) * 2,
      phase: Math.random() * Math.PI * 2,
    });
  }
  return cells;
}

export default function TumorMicroenvironment() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const canvasRef = useRef(null);
  const cellsRef = useRef(generateCells(350));
  const [selected, setSelected] = useState(null);
  const [showLabels, setShowLabels] = useState(true);
  const [highlightType, setHighlightType] = useState(null);
  const frameRef = useRef(0);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const cw = canvas.offsetWidth;
    const ch = canvas.offsetHeight;
    canvas.width = cw * devicePixelRatio;
    canvas.height = ch * devicePixelRatio;
    ctx.scale(devicePixelRatio, devicePixelRatio);
    ctx.clearRect(0, 0, cw, ch);

    // Dark tissue background gradient
    const grad = ctx.createRadialGradient(cw / 2, ch / 2, 0, cw / 2, ch / 2, cw * 0.6);
    grad.addColorStop(0, 'rgba(244,63,94,0.06)');
    grad.addColorStop(0.5, 'rgba(139,92,246,0.03)');
    grad.addColorStop(1, 'rgba(15,23,42,0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, cw, ch);

    const t = performance.now() / 1000;

    for (const cell of cellsRef.current) {
      cell.x += cell.vx;
      cell.y += cell.vy;
      if (cell.x < 0.02 || cell.x > 0.98) cell.vx *= -1;
      if (cell.y < 0.02 || cell.y > 0.98) cell.vy *= -1;

      const px = cell.x * cw;
      const py = cell.y * ch;
      const ct = CELL_TYPES[cell.type];
      const breathing = 1 + Math.sin(t * 1.5 + cell.phase) * 0.12;
      const r = cell.radius * breathing;
      const dimmed = highlightType && highlightType !== cell.type;

      ctx.globalAlpha = dimmed ? 0.15 : 0.85;

      // Outer glow
      ctx.beginPath();
      ctx.arc(px, py, r + 3, 0, Math.PI * 2);
      ctx.fillStyle = ct.color + '22';
      ctx.fill();

      // Cell body
      ctx.beginPath();
      ctx.arc(px, py, r, 0, Math.PI * 2);
      ctx.fillStyle = ct.color + 'cc';
      ctx.fill();

      // Nucleus
      ctx.beginPath();
      ctx.arc(px + r * 0.15, py - r * 0.15, r * 0.4, 0, Math.PI * 2);
      ctx.fillStyle = ct.color;
      ctx.fill();

      // Mitotic spindle for dividing tumor cells
      if (cell.type === 'tumor' && cell.id % 12 === 0) {
        ctx.beginPath();
        ctx.ellipse(px, py, r * 1.3, r * 0.6, t * 0.3 + cell.phase, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(244,63,94,0.3)';
        ctx.lineWidth = 0.8;
        ctx.stroke();
      }

      ctx.globalAlpha = 1;
    }

    // Draw vasculature network (stylized)
    ctx.globalAlpha = 0.2;
    ctx.strokeStyle = '#ec4899';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (let i = 0; i < 5; i++) {
      const sx = cw * (0.1 + i * 0.2);
      ctx.moveTo(sx, 0);
      for (let y = 0; y < ch; y += 20) {
        ctx.lineTo(sx + Math.sin(y * 0.02 + t * 0.5 + i) * 25, y);
      }
    }
    ctx.stroke();
    ctx.globalAlpha = 1;

    frameRef.current = requestAnimationFrame(draw);
  }, [highlightType]);

  useEffect(() => {
    frameRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frameRef.current);
  }, [draw]);

  const handleCanvasClick = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) / rect.width;
    const my = (e.clientY - rect.top) / rect.height;
    let closest = null, minD = Infinity;
    for (const c of cellsRef.current) {
      const d = Math.hypot(c.x - mx, c.y - my);
      if (d < minD) { minD = d; closest = c; }
    }
    if (minD < 0.04) setSelected(closest);
    else setSelected(null);
  };

  const typeCounts = {};
  for (const c of cellsRef.current) {
    typeCounts[c.type] = (typeCounts[c.type] || 0) + 1;
  }

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[1600px] mx-auto">
            <div className="mb-6">
              <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
                Tumor Microenvironment
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Interactive cell-level visualization — immune infiltration, vasculature, and tumor architecture</p>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
              {/* Canvas */}
              <div className="xl:col-span-3">
                <GlowCard glowColor="rose" noPad className="overflow-hidden">
                  <canvas
                    ref={canvasRef}
                    className="w-full cursor-crosshair"
                    style={{ height: 520 }}
                    onClick={handleCanvasClick}
                  />
                </GlowCard>
              </div>

              {/* Side panel */}
              <div className="space-y-4">
                {/* Legend + filter */}
                <GlowCard glowColor="violet" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Cell Populations</h3>
                  <div className="space-y-2">
                    {Object.entries(CELL_TYPES).map(([key, ct]) => (
                      <button
                        key={key}
                        onClick={() => setHighlightType(highlightType === key ? null : key)}
                        className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left text-xs transition-colors ${highlightType === key ? 'bg-violet-50 dark:bg-violet-900/30' : 'hover:bg-gray-50 dark:hover:bg-gray-800'}`}
                      >
                        <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: ct.color }} />
                        <span className="flex-1 font-medium text-gray-700 dark:text-gray-200">{ct.label}</span>
                        <span className="text-gray-400 tabular-nums">{typeCounts[key] || 0}</span>
                      </button>
                    ))}
                  </div>
                </GlowCard>

                {/* Selected cell details */}
                {selected && (
                  <GlowCard glowColor="sky" className="!p-4">
                    <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-2">Selected Cell</h3>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between"><span className="text-gray-400">Type:</span><span className="font-semibold" style={{ color: CELL_TYPES[selected.type].color }}>{CELL_TYPES[selected.type].label}</span></div>
                      <div className="flex justify-between"><span className="text-gray-400">Position:</span><span>({(selected.x * 100).toFixed(1)}%, {(selected.y * 100).toFixed(1)}%)</span></div>
                      <div className="flex justify-between"><span className="text-gray-400">Radius:</span><span>{selected.radius.toFixed(1)} µm</span></div>
                      <div className="flex justify-between"><span className="text-gray-400">Cell ID:</span><span>#{selected.id}</span></div>
                    </div>
                  </GlowCard>
                )}

                {/* Microenvironment Metrics */}
                <GlowCard glowColor="emerald" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">TME Metrics</h3>
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between"><span className="text-gray-400">Tumor Purity</span><span className="font-bold text-rose-500">30.0%</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">TIL Score</span><span className="font-bold text-emerald-500">23.4%</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Stromal Fraction</span><span className="font-bold text-violet-500">12.0%</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Vasculature Density</span><span className="font-bold text-pink-500">7.1%</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">CD8/CD4 Ratio</span><span className="font-bold text-sky-500">1.82</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Immune Score</span><span className="font-bold text-indigo-500">HIGH</span></div>
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
