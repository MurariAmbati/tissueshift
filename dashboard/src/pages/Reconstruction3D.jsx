import { useState, useEffect, useRef, useCallback } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import GlowCard from '../components/GlowCard';

/* ── Simulated serial section data ─────────────────────────────── */
const TOTAL_SLICES = 48;
function generateSlice(z) {
  const shapes = [];
  const seed = z * 1337;
  // Main tumor mass — ellipsoid cross-section grows then shrinks
  const t = z / TOTAL_SLICES;
  const r = Math.sin(t * Math.PI) * 0.35 + 0.05;
  const cx = 0.48 + Math.sin(seed) * 0.02;
  const cy = 0.50 + Math.cos(seed) * 0.02;
  shapes.push({ cx, cy, rx: r * 1.1, ry: r * 0.9, type: 'tumor', opacity: 0.7 });
  // Necrotic core
  if (t > 0.2 && t < 0.8) {
    const nr = (Math.sin((t - 0.2) / 0.6 * Math.PI)) * 0.12;
    shapes.push({ cx: cx + 0.01, cy: cy - 0.01, rx: nr, ry: nr * 0.85, type: 'necrosis', opacity: 0.5 });
  }
  // Vessels — small circles
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2 + z * 0.1;
    const d = r * 0.6 + (i % 3) * 0.04;
    shapes.push({
      cx: cx + Math.cos(a) * d,
      cy: cy + Math.sin(a) * d,
      rx: 0.015, ry: 0.015,
      type: 'vessel',
      opacity: 0.8,
    });
  }
  return shapes;
}

const COLORS = {
  tumor: '#f43f5e',
  necrosis: '#64748b',
  vessel: '#0ea5e9',
  stroma: '#a78bfa',
};

/* ── Volume stats ─────────────────────────────────────────────── */
function computeStats() {
  let tumorVol = 0, necVol = 0, vesselCount = 0;
  for (let z = 0; z < TOTAL_SLICES; z++) {
    const shapes = generateSlice(z);
    shapes.forEach(s => {
      if (s.type === 'tumor') tumorVol += s.rx * s.ry;
      if (s.type === 'necrosis') necVol += s.rx * s.ry;
      if (s.type === 'vessel') vesselCount++;
    });
  }
  return {
    tumorVol: (tumorVol * 1000).toFixed(1),
    necVol: (necVol * 1000).toFixed(1),
    necPercent: ((necVol / tumorVol) * 100).toFixed(1),
    vesselDensity: (vesselCount / TOTAL_SLICES).toFixed(1),
    sliceThickness: '5 \u00b5m',
    totalDepth: `${TOTAL_SLICES * 5} \u00b5m`,
  };
}

export default function Reconstruction3D() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const canvasRef = useRef(null);
  const [currentSlice, setCurrentSlice] = useState(0);
  const [viewMode, setViewMode] = useState('3d'); // '3d' | 'slice' | 'mip'
  const [rotationY, setRotationY] = useState(-25);
  const [rotationX, setRotationX] = useState(20);
  const [autoRotate, setAutoRotate] = useState(true);
  const [showVessels, setShowVessels] = useState(true);
  const [showNecrosis, setShowNecrosis] = useState(true);
  const animRef = useRef(null);
  const dragRef = useRef(null);
  const stats = computeStats();

  /* ── 3D isometric renderer ───────────────────────────────── */
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width = canvas.offsetWidth * 2;
    const H = canvas.height = canvas.offsetHeight * 2;
    ctx.scale(2, 2);
    const w = W / 2, h = H / 2;
    ctx.clearRect(0, 0, w, h);

    const radY = (rotationY * Math.PI) / 180;
    const radX = (rotationX * Math.PI) / 180;
    const cosY = Math.cos(radY), sinY = Math.sin(radY);
    const cosX = Math.cos(radX), sinX = Math.sin(radX);

    const project = (x3, y3, z3) => {
      // Center in [0,1] → [-0.5, 0.5]
      const px = x3 - 0.5, py = y3 - 0.5, pz = z3 - 0.5;
      // Rotate Y
      const rx = px * cosY - pz * sinY;
      const rz = px * sinY + pz * cosY;
      // Rotate X
      const ry = py * cosX - rz * sinX;
      const rz2 = py * sinX + rz * cosX;
      const scale = 0.7 * Math.min(w, h);
      return {
        x: w / 2 + rx * scale,
        y: h / 2 + ry * scale,
        z: rz2,
      };
    };

    if (viewMode === '3d') {
      // Draw all slices stacked
      const sliceStep = Math.max(1, Math.floor(TOTAL_SLICES / 24));
      const elements = [];
      for (let z = 0; z < TOTAL_SLICES; z += sliceStep) {
        const shapes = generateSlice(z);
        const zNorm = z / TOTAL_SLICES;
        shapes.forEach(s => {
          if (s.type === 'vessel' && !showVessels) return;
          if (s.type === 'necrosis' && !showNecrosis) return;
          const p = project(s.cx, s.cy, zNorm);
          elements.push({ ...s, px: p.x, py: p.y, pz: p.z, zNorm });
        });
      }
      // Sort by depth
      elements.sort((a, b) => a.pz - b.pz);
      elements.forEach(e => {
        ctx.globalAlpha = e.opacity * 0.6;
        ctx.fillStyle = COLORS[e.type];
        const baseR = e.type === 'vessel' ? 3 : e.rx * 0.7 * Math.min(w, h) * 0.5;
        ctx.beginPath();
        ctx.ellipse(e.px, e.py, Math.max(2, baseR), Math.max(2, baseR * 0.7), 0, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.globalAlpha = 1;

      // Draw bounding box wireframe
      ctx.strokeStyle = '#6b7280';
      ctx.lineWidth = 0.5;
      ctx.globalAlpha = 0.3;
      const corners = [
        [0,0,0],[1,0,0],[1,1,0],[0,1,0],
        [0,0,1],[1,0,1],[1,1,1],[0,1,1],
      ];
      const edges = [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];
      const proj = corners.map(c => project(c[0], c[1], c[2]));
      edges.forEach(([a, b]) => {
        ctx.beginPath();
        ctx.moveTo(proj[a].x, proj[a].y);
        ctx.lineTo(proj[b].x, proj[b].y);
        ctx.stroke();
      });
      ctx.globalAlpha = 1;

      // Axis labels
      ctx.font = '11px Inter, sans-serif';
      ctx.fillStyle = '#9ca3af';
      const xEnd = project(1.05, 0.5, 0.5);
      const yEnd = project(0.5, 1.05, 0.5);
      const zEnd = project(0.5, 0.5, 1.05);
      ctx.fillText('X', xEnd.x, xEnd.y);
      ctx.fillText('Y', yEnd.x, yEnd.y);
      ctx.fillText('Z', zEnd.x, zEnd.y);

    } else if (viewMode === 'slice') {
      // Single slice 2D view
      const shapes = generateSlice(currentSlice);
      // Background tissue
      ctx.fillStyle = '#fce7f3';
      ctx.fillRect(w * 0.1, h * 0.1, w * 0.8, h * 0.8);
      ctx.strokeStyle = '#d1d5db';
      ctx.lineWidth = 1;
      ctx.strokeRect(w * 0.1, h * 0.1, w * 0.8, h * 0.8);

      shapes.forEach(s => {
        if (s.type === 'vessel' && !showVessels) return;
        if (s.type === 'necrosis' && !showNecrosis) return;
        ctx.globalAlpha = s.opacity;
        ctx.fillStyle = COLORS[s.type];
        ctx.beginPath();
        ctx.ellipse(
          w * 0.1 + s.cx * w * 0.8,
          h * 0.1 + s.cy * h * 0.8,
          s.rx * w * 0.8,
          s.ry * h * 0.8,
          0, 0, Math.PI * 2
        );
        ctx.fill();
      });
      ctx.globalAlpha = 1;

      // Slice label
      ctx.font = '12px Inter, sans-serif';
      ctx.fillStyle = '#6b7280';
      ctx.fillText(`Section ${currentSlice + 1} / ${TOTAL_SLICES}  (z = ${currentSlice * 5} \u00b5m)`, w * 0.1, h * 0.1 - 8);

    } else if (viewMode === 'mip') {
      // Maximum intensity projection
      const resolution = 200;
      const grid = Array.from({ length: resolution }, () => new Float32Array(resolution));
      for (let z = 0; z < TOTAL_SLICES; z++) {
        const shapes = generateSlice(z);
        shapes.forEach(s => {
          if (s.type !== 'tumor') return;
          // Rasterize ellipse onto grid
          const cxPx = Math.floor(s.cx * resolution);
          const cyPx = Math.floor(s.cy * resolution);
          const rxPx = Math.ceil(s.rx * resolution);
          const ryPx = Math.ceil(s.ry * resolution);
          for (let dy = -ryPx; dy <= ryPx; dy++) {
            for (let dx = -rxPx; dx <= rxPx; dx++) {
              const nx = dx / (rxPx || 1), ny = dy / (ryPx || 1);
              if (nx * nx + ny * ny <= 1) {
                const gx = cxPx + dx, gy = cyPx + dy;
                if (gx >= 0 && gx < resolution && gy >= 0 && gy < resolution) {
                  grid[gy][gx] = Math.max(grid[gy][gx], s.opacity);
                }
              }
            }
          }
        });
      }
      // Render the MIP
      const cellW = (w * 0.8) / resolution;
      const cellH = (h * 0.8) / resolution;
      for (let y = 0; y < resolution; y++) {
        for (let x = 0; x < resolution; x++) {
          if (grid[y][x] > 0) {
            const v = grid[y][x];
            ctx.fillStyle = `rgba(244, 63, 94, ${v * 0.8})`;
            ctx.fillRect(w * 0.1 + x * cellW, h * 0.1 + y * cellH, cellW + 0.5, cellH + 0.5);
          }
        }
      }
      ctx.strokeStyle = '#d1d5db';
      ctx.lineWidth = 1;
      ctx.strokeRect(w * 0.1, h * 0.1, w * 0.8, h * 0.8);
      ctx.font = '12px Inter, sans-serif';
      ctx.fillStyle = '#6b7280';
      ctx.fillText('Maximum Intensity Projection (Tumor)', w * 0.1, h * 0.1 - 8);
    }
  }, [viewMode, currentSlice, rotationX, rotationY, showVessels, showNecrosis]);

  /* ── Auto-rotate ──────────────────────────────────────────── */
  useEffect(() => {
    let frameId;
    const tick = () => {
      if (autoRotate && viewMode === '3d') {
        setRotationY(prev => prev + 0.3);
      }
      draw();
      frameId = requestAnimationFrame(tick);
    };
    frameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameId);
  }, [draw, autoRotate, viewMode]);

  /* ── Mouse drag rotation ──────────────────────────────────── */
  const handleMouseDown = (e) => {
    if (viewMode !== '3d') return;
    setAutoRotate(false);
    dragRef.current = { x: e.clientX, y: e.clientY, ry: rotationY, rx: rotationX };
  };
  const handleMouseMove = (e) => {
    if (!dragRef.current) return;
    const dx = e.clientX - dragRef.current.x;
    const dy = e.clientY - dragRef.current.y;
    setRotationY(dragRef.current.ry + dx * 0.5);
    setRotationX(Math.max(-60, Math.min(60, dragRef.current.rx + dy * 0.5)));
  };
  const handleMouseUp = () => { dragRef.current = null; };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
            {/* Title */}
            <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-1">3D Tissue Reconstruction</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
              Volumetric reconstruction from {TOTAL_SLICES} serial histology sections &middot; {stats.sliceThickness} per section &middot; {stats.totalDepth} total depth
            </p>

            <div className="grid grid-cols-12 gap-6">
              {/* Main 3D viewport */}
              <div className="col-span-12 xl:col-span-8">
                <GlowCard>
                  <div className="p-4">
                    {/* Toolbar */}
                    <div className="flex flex-wrap items-center gap-2 mb-3">
                      {['3d', 'slice', 'mip'].map(m => (
                        <button
                          key={m}
                          onClick={() => setViewMode(m)}
                          className={`px-3 py-1.5 rounded text-xs font-semibold transition ${
                            viewMode === m
                              ? 'bg-violet-600 text-white'
                              : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                          }`}
                        >
                          {m === '3d' ? '3D Volume' : m === 'slice' ? 'Slice View' : 'MIP'}
                        </button>
                      ))}
                      <div className="h-5 w-px bg-gray-300 dark:bg-gray-600 mx-1" />
                      <label className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
                        <input type="checkbox" checked={showVessels} onChange={() => setShowVessels(!showVessels)} className="rounded text-violet-500" />
                        Vessels
                      </label>
                      <label className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
                        <input type="checkbox" checked={showNecrosis} onChange={() => setShowNecrosis(!showNecrosis)} className="rounded text-violet-500" />
                        Necrosis
                      </label>
                      {viewMode === '3d' && (
                        <label className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400 ml-auto">
                          <input type="checkbox" checked={autoRotate} onChange={() => setAutoRotate(!autoRotate)} className="rounded text-violet-500" />
                          Auto-rotate
                        </label>
                      )}
                    </div>

                    {/* Canvas */}
                    <canvas
                      ref={canvasRef}
                      className="w-full rounded-lg bg-gray-950 cursor-grab active:cursor-grabbing"
                      style={{ height: 420, touchAction: 'none' }}
                      onMouseDown={handleMouseDown}
                      onMouseMove={handleMouseMove}
                      onMouseUp={handleMouseUp}
                      onMouseLeave={handleMouseUp}
                    />

                    {/* Slice slider */}
                    {viewMode === 'slice' && (
                      <div className="mt-3 flex items-center gap-3">
                        <span className="text-xs text-gray-500 w-8">z=0</span>
                        <input
                          type="range" min={0} max={TOTAL_SLICES - 1} value={currentSlice}
                          onChange={e => setCurrentSlice(Number(e.target.value))}
                          className="flex-1 accent-violet-500"
                        />
                        <span className="text-xs text-gray-500 w-16 text-right">z={stats.totalDepth}</span>
                      </div>
                    )}
                  </div>
                </GlowCard>
              </div>

              {/* Stats & controls panel */}
              <div className="col-span-12 xl:col-span-4 flex flex-col gap-4">
                {/* Volume metrics */}
                <GlowCard>
                  <div className="p-4">
                    <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3">Volume Metrics</h2>
                    <dl className="space-y-2.5">
                      {[
                        { label: 'Total Tumor Volume', value: `${stats.tumorVol} mm\u00b3` },
                        { label: 'Necrotic Core', value: `${stats.necVol} mm\u00b3 (${stats.necPercent}%)` },
                        { label: 'Vessel Density', value: `${stats.vesselDensity} / section` },
                        { label: 'Serial Sections', value: `${TOTAL_SLICES}` },
                        { label: 'Section Thickness', value: stats.sliceThickness },
                        { label: 'Z-Stack Depth', value: stats.totalDepth },
                      ].map(row => (
                        <div key={row.label} className="flex justify-between">
                          <dt className="text-xs text-gray-500 dark:text-gray-400">{row.label}</dt>
                          <dd className="text-xs font-semibold text-gray-800 dark:text-gray-100">{row.value}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                </GlowCard>

                {/* Legend */}
                <GlowCard>
                  <div className="p-4">
                    <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3">Tissue Legend</h2>
                    <div className="space-y-2">
                      {Object.entries(COLORS).map(([type, color]) => (
                        <div key={type} className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: color }} />
                          <span className="text-xs text-gray-600 dark:text-gray-400 capitalize">{type}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </GlowCard>

                {/* Reconstruction pipeline */}
                <GlowCard>
                  <div className="p-4">
                    <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3">Reconstruction Pipeline</h2>
                    <ol className="space-y-2">
                      {[
                        'Serial sectioning (microtome)',
                        'H&E staining & scanning',
                        'Rigid registration (SIFT)',
                        'Non-rigid alignment (B-spline)',
                        'Tissue segmentation (U-Net)',
                        'Surface mesh extraction',
                        'Volumetric rendering',
                      ].map((step, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="flex items-center justify-center w-5 h-5 rounded bg-violet-100 dark:bg-violet-500/20 text-violet-600 dark:text-violet-400 text-[10px] font-bold shrink-0 mt-0.5">{i + 1}</span>
                          <span className="text-xs text-gray-600 dark:text-gray-400">{step}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                </GlowCard>

                {/* Cross-section profiles */}
                <GlowCard>
                  <div className="p-4">
                    <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3">Cross-Section Profile</h2>
                    <div className="flex items-end gap-0.5" style={{ height: 60 }}>
                      {Array.from({ length: TOTAL_SLICES }, (_, z) => {
                        const shapes = generateSlice(z);
                        const tumorR = shapes.find(s => s.type === 'tumor')?.rx || 0;
                        const h = (tumorR / 0.45) * 100;
                        return (
                          <div
                            key={z}
                            className={`flex-1 rounded-t transition-colors ${z === currentSlice && viewMode === 'slice' ? 'bg-violet-500' : 'bg-rose-400/60'}`}
                            style={{ height: `${h}%` }}
                            title={`Section ${z + 1}`}
                          />
                        );
                      })}
                    </div>
                    <p className="text-[10px] text-gray-400 mt-1">Tumor cross-sectional radius across z-stack</p>
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
