import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import GlowCard from '../components/GlowCard';
import PulseRing from '../components/PulseRing';
import AnimatedCounter from '../components/AnimatedCounter';

/* ══════════════════════════════════════════════════════════════════
   CV PATHOLOGY LAB
   Full computer-vision slide analysis suite:
   1. Cell Detection & Segmentation canvas — bounding boxes + contours
   2. Mitosis Detection — highlighted dividing cells
   3. Nuclear Morphometry — size/shape distribution
   4. Tissue Region Classification — color-coded overlay
   5. Stain Normalization Preview — before/after
   6. Real-time metrics (cell count, mitotic index, etc.)
   ══════════════════════════════════════════════════════════════════ */

/* ── Generate synthetic cells ────────────────────────────────── */
function generateCells(n, w, h) {
  const types = [
    { label: 'Tumor', color: '#f43f5e', prob: 0.35 },
    { label: 'Lymphocyte', color: '#0ea5e9', prob: 0.25 },
    { label: 'Stromal', color: '#f59e0b', prob: 0.20 },
    { label: 'Macrophage', color: '#10b981', prob: 0.10 },
    { label: 'Mitotic', color: '#d946ef', prob: 0.05 },
    { label: 'Apoptotic', color: '#6366f1', prob: 0.05 },
  ];
  const cells = [];
  for (let i = 0; i < n; i++) {
    const roll = Math.random();
    let cumul = 0;
    let type = types[0];
    for (const t of types) { cumul += t.prob; if (roll < cumul) { type = t; break; } }

    const baseR = type.label === 'Lymphocyte' ? 4 : type.label === 'Tumor' ? 8 : type.label === 'Mitotic' ? 9 : type.label === 'Macrophage' ? 7 : 6;
    const radius = baseR + Math.random() * 4;
    const eccentricity = 0.6 + Math.random() * 0.4;
    const area = Math.PI * radius * (radius * eccentricity);
    const perimeter = Math.PI * (3 * (radius + radius * eccentricity) - Math.sqrt((3 * radius + radius * eccentricity) * (radius + 3 * radius * eccentricity)));
    const circularity = (4 * Math.PI * area) / (perimeter * perimeter);

    cells.push({
      id: i, x: 30 + Math.random() * (w - 60), y: 30 + Math.random() * (h - 60),
      radius, eccentricity, area: Math.round(area), circularity: +circularity.toFixed(2),
      type: type.label, color: type.color,
      confidence: +(0.72 + Math.random() * 0.27).toFixed(2),
      intensity: Math.round(80 + Math.random() * 120),
      angle: Math.random() * Math.PI,
    });
  }
  return cells;
}

/* ── Generate tissue regions (polygonal blobs) ───────────────── */
function generateRegions(w, h) {
  const regions = [
    { label: 'Invasive Tumor', color: '#f43f5e', cx: 0.35, cy: 0.4, r: 0.20, pct: 42 },
    { label: 'DCIS', color: '#d946ef', cx: 0.25, cy: 0.3, r: 0.08, pct: 8 },
    { label: 'Stroma', color: '#f59e0b', cx: 0.6, cy: 0.6, r: 0.22, pct: 28 },
    { label: 'Necrosis', color: '#6b7280', cx: 0.4, cy: 0.55, r: 0.06, pct: 4 },
    { label: 'TIL-rich', color: '#0ea5e9', cx: 0.55, cy: 0.35, r: 0.10, pct: 11 },
    { label: 'Normal Duct', color: '#10b981', cx: 0.75, cy: 0.5, r: 0.09, pct: 7 },
  ];
  return regions.map(r => {
    const pts = [];
    const nPts = 10 + Math.floor(Math.random() * 6);
    for (let i = 0; i < nPts; i++) {
      const a = (i / nPts) * Math.PI * 2;
      const jitter = 0.7 + Math.random() * 0.6;
      pts.push({ x: (r.cx + Math.cos(a) * r.r * jitter) * w, y: (r.cy + Math.sin(a) * r.r * jitter) * h });
    }
    return { ...r, points: pts };
  });
}

/* ── Cell Detection & Segmentation Canvas ────────────────────── */
function CellDetectionCanvas({ cells, selectedCell, onSelectCell, overlay, showBBox, showContour, showLabels }) {
  const canvasRef = useRef(null);
  const W = 620, H = 480;
  const regions = useMemo(() => generateRegions(W, H), []);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = devicePixelRatio;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    ctx.scale(dpr, dpr);

    // Tissue-like background
    const bg = ctx.createRadialGradient(W * 0.4, H * 0.4, 0, W * 0.4, H * 0.4, W * 0.5);
    bg.addColorStop(0, '#2a1520');
    bg.addColorStop(0.5, '#1a1228');
    bg.addColorStop(1, '#0c0a14');
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, W, H);

    // Simulate H&E stain texture (stipple noise)
    for (let i = 0; i < 3000; i++) {
      const sx = Math.random() * W, sy = Math.random() * H;
      ctx.fillStyle = `rgba(${160 + Math.random()*60}, ${100 + Math.random()*40}, ${140 + Math.random()*60}, 0.04)`;
      ctx.fillRect(sx, sy, 1, 1);
    }

    // Tissue region overlays
    if (overlay === 'regions') {
      regions.forEach(r => {
        ctx.beginPath();
        r.points.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
        ctx.closePath();
        ctx.fillStyle = r.color + '25';
        ctx.fill();
        ctx.strokeStyle = r.color + '60';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        // Label
        const cx = r.points.reduce((a, p) => a + p.x, 0) / r.points.length;
        const cy = r.points.reduce((a, p) => a + p.y, 0) / r.points.length;
        ctx.font = 'bold 9px Inter, sans-serif';
        ctx.fillStyle = r.color + 'cc';
        ctx.textAlign = 'center';
        ctx.fillText(r.label, cx, cy);
      });
    }

    // Draw cells
    cells.forEach(c => {
      // Cell body (ellipse)
      ctx.save();
      ctx.translate(c.x, c.y);
      ctx.rotate(c.angle);
      ctx.beginPath();
      ctx.ellipse(0, 0, c.radius, c.radius * c.eccentricity, 0, 0, Math.PI * 2);

      // Fill: faint for non-overlay, colored for heatmap
      if (overlay === 'heatmap') {
        const alpha = 0.15 + c.confidence * 0.6;
        ctx.fillStyle = c.color + Math.round(alpha * 255).toString(16).padStart(2, '0');
      } else {
        ctx.fillStyle = `rgba(${c.intensity}, ${c.intensity * 0.6}, ${c.intensity * 0.8}, 0.3)`;
      }
      ctx.fill();

      // Contour
      if (showContour) {
        ctx.strokeStyle = c.color + '90';
        ctx.lineWidth = 1;
        ctx.stroke();
      }
      ctx.restore();

      // Bounding box
      if (showBBox) {
        const bx = c.x - c.radius - 2, by = c.y - c.radius - 2;
        const bw = c.radius * 2 + 4, bh = c.radius * 2 + 4;
        ctx.strokeStyle = c.color + '60';
        ctx.lineWidth = 0.8;
        ctx.strokeRect(bx, by, bw, bh);
      }

      // Label
      if (showLabels && c.radius > 6) {
        ctx.font = '7px Inter, sans-serif';
        ctx.fillStyle = c.color + 'bb';
        ctx.textAlign = 'center';
        ctx.fillText(c.type, c.x, c.y - c.radius - 4);
      }

      // Selected highlight
      if (selectedCell?.id === c.id) {
        ctx.beginPath();
        ctx.arc(c.x, c.y, c.radius + 6, 0, Math.PI * 2);
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Crosshair
        ctx.strokeStyle = '#ffffff40';
        ctx.lineWidth = 0.5;
        ctx.beginPath(); ctx.moveTo(c.x - 20, c.y); ctx.lineTo(c.x + 20, c.y); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(c.x, c.y - 20); ctx.lineTo(c.x, c.y + 20); ctx.stroke();
      }
    });

    // Mitosis highlights (special ring for mitotic cells)
    if (overlay === 'mitosis') {
      cells.filter(c => c.type === 'Mitotic').forEach(c => {
        ctx.beginPath();
        ctx.arc(c.x, c.y, c.radius + 8, 0, Math.PI * 2);
        ctx.strokeStyle = '#d946ef';
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 3]);
        ctx.stroke();
        ctx.setLineDash([]);
        // Arrow pointer
        ctx.font = 'bold 10px Inter, sans-serif';
        ctx.fillStyle = '#d946ef';
        ctx.textAlign = 'center';
        ctx.fillText('⟶ MITOSIS', c.x, c.y - c.radius - 14);
      });
    }

    // Scale bar
    ctx.fillStyle = '#ffffff50';
    ctx.fillRect(W - 90, H - 22, 70, 2);
    ctx.font = '9px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('50 µm', W - 55, H - 8);

    // FPS-style overlay
    ctx.font = '9px monospace';
    ctx.fillStyle = '#ffffff40';
    ctx.textAlign = 'left';
    ctx.fillText(`CV Pipeline: ${cells.length} detections`, 8, 14);
  }, [cells, selectedCell, overlay, showBBox, showContour, showLabels, regions]);

  useEffect(() => { draw(); }, [draw]);

  const handleClick = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (W / rect.width);
    const my = (e.clientY - rect.top) * (H / rect.height);
    for (const c of cells) {
      const dx = c.x - mx, dy = c.y - my;
      if (dx * dx + dy * dy < (c.radius + 4) ** 2) { onSelectCell(c); return; }
    }
    onSelectCell(null);
  };

  return <canvas ref={canvasRef} className="w-full cursor-crosshair" style={{ height: H }} onClick={handleClick} />;
}

/* ── Nuclear Morphometry Distribution (mini histogram) ──────── */
function MorphHistogram({ cells, metric, label, unit }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const cw = canvas.offsetWidth, ch = 80;
    canvas.width = cw * devicePixelRatio;
    canvas.height = ch * devicePixelRatio;
    canvas.style.height = ch + 'px';
    ctx.scale(devicePixelRatio, devicePixelRatio);

    ctx.fillStyle = '#0a0a18';
    ctx.fillRect(0, 0, cw, ch);

    const values = cells.map(c => c[metric]);
    const min = Math.min(...values), max = Math.max(...values);
    const bins = 20;
    const binWidth = (max - min) / bins || 1;
    const counts = new Array(bins).fill(0);
    values.forEach(v => { const b = Math.min(Math.floor((v - min) / binWidth), bins - 1); counts[b]++; });
    const maxCount = Math.max(...counts, 1);

    const barW = (cw - 20) / bins;
    counts.forEach((count, i) => {
      const barH = (count / maxCount) * (ch - 24);
      const x = 10 + i * barW;
      const gradient = ctx.createLinearGradient(0, ch - 12 - barH, 0, ch - 12);
      gradient.addColorStop(0, '#8b5cf6');
      gradient.addColorStop(1, '#8b5cf620');
      ctx.fillStyle = gradient;
      ctx.fillRect(x, ch - 12 - barH, barW - 1, barH);
    });

    ctx.font = '8px Inter, sans-serif';
    ctx.fillStyle = '#ffffff40';
    ctx.textAlign = 'left';
    ctx.fillText(`${min.toFixed(0)} ${unit}`, 10, ch - 2);
    ctx.textAlign = 'right';
    ctx.fillText(`${max.toFixed(0)} ${unit}`, cw - 10, ch - 2);
    ctx.textAlign = 'center';
    ctx.fillText(label, cw / 2, 10);
  }, [cells, metric, label, unit]);

  return <canvas ref={canvasRef} className="w-full rounded-lg" />;
}

/* ══════════════════════════════════════════════════════════════════
   MAIN PAGE
   ══════════════════════════════════════════════════════════════════ */
export default function PathologyLab() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [overlay, setOverlay] = useState('heatmap');     // heatmap | regions | mitosis | none
  const [showBBox, setShowBBox] = useState(true);
  const [showContour, setShowContour] = useState(true);
  const [showLabels, setShowLabels] = useState(false);
  const [selectedCell, setSelectedCell] = useState(null);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.75);

  const allCells = useMemo(() => generateCells(420, 620, 480), []);
  const cells = useMemo(() => allCells.filter(c => c.confidence >= confidenceThreshold), [allCells, confidenceThreshold]);

  // Aggregate stats
  const typeCounts = {};
  cells.forEach(c => { typeCounts[c.type] = (typeCounts[c.type] || 0) + 1; });
  const mitoticCount = typeCounts['Mitotic'] || 0;
  const tumorCount = typeCounts['Tumor'] || 0;
  const tilCount = (typeCounts['Lymphocyte'] || 0);
  const mitoticIndex = tumorCount > 0 ? ((mitoticCount / (tumorCount + mitoticCount)) * 100).toFixed(1) : 0;
  const avgArea = cells.length ? Math.round(cells.reduce((a, c) => a + c.area, 0) / cells.length) : 0;
  const avgCirc = cells.length ? (cells.reduce((a, c) => a + c.circularity, 0) / cells.length).toFixed(2) : 0;

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[1600px] mx-auto">

            {/* Title */}
            <div className="mb-6">
              <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
                CV Pathology Lab
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Computer-vision powered slide analysis — cell detection, segmentation, nuclear morphometry, mitosis counting, tissue classification
              </p>
            </div>

            {/* KPI strip */}
            <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-6">
              {[
                { label: 'Cells Detected', value: cells.length, color: 'violet' },
                { label: 'Tumor Cells', value: tumorCount, color: 'rose' },
                { label: 'TILs', value: tilCount, color: 'sky' },
                { label: 'Mitotic Figures', value: mitoticCount, color: 'fuchsia' },
                { label: 'Mitotic Index', value: mitoticIndex + '%', color: 'amber' },
                { label: 'Avg Nuclear Area', value: avgArea + ' µm²', color: 'emerald' },
              ].map(k => (
                <GlowCard key={k.label} glowColor={k.color} className="!p-3 text-center">
                  <div className="text-[10px] uppercase tracking-wider text-gray-400">{k.label}</div>
                  <div className="text-lg font-extrabold text-gray-800 dark:text-white mt-0.5">{typeof k.value === 'number' ? <AnimatedCounter end={k.value} /> : k.value}</div>
                </GlowCard>
              ))}
            </div>

            {/* Toolbar */}
            <div className="flex flex-wrap items-center gap-3 mb-4 p-3 bg-white dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700/60">
              <span className="text-[10px] text-gray-400 uppercase tracking-wider">Overlay:</span>
              {[{ id: 'heatmap', label: 'Cell Types' }, { id: 'regions', label: 'Tissue Regions' }, { id: 'mitosis', label: 'Mitosis Detect' }, { id: 'none', label: 'Raw' }].map(o => (
                <button
                  key={o.id}
                  onClick={() => setOverlay(o.id)}
                  className={`px-2.5 py-1 rounded text-[10px] font-semibold transition-colors ${overlay === o.id ? 'bg-violet-500 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-500'}`}
                >
                  {o.label}
                </button>
              ))}
              <span className="w-px h-4 bg-gray-300 dark:bg-gray-600" />
              <label className="flex items-center gap-1 text-[10px] text-gray-400 cursor-pointer">
                <input type="checkbox" checked={showBBox} onChange={() => setShowBBox(!showBBox)} className="accent-violet-500 w-3 h-3" /> BBox
              </label>
              <label className="flex items-center gap-1 text-[10px] text-gray-400 cursor-pointer">
                <input type="checkbox" checked={showContour} onChange={() => setShowContour(!showContour)} className="accent-violet-500 w-3 h-3" /> Contour
              </label>
              <label className="flex items-center gap-1 text-[10px] text-gray-400 cursor-pointer">
                <input type="checkbox" checked={showLabels} onChange={() => setShowLabels(!showLabels)} className="accent-violet-500 w-3 h-3" /> Labels
              </label>
              <span className="w-px h-4 bg-gray-300 dark:bg-gray-600" />
              <span className="text-[10px] text-gray-400">Conf ≥</span>
              <input
                type="range" min={0.5} max={0.99} step={0.01} value={confidenceThreshold}
                onChange={e => setConfidenceThreshold(+e.target.value)}
                className="w-24 accent-violet-500"
              />
              <span className="text-[10px] font-bold text-violet-500 tabular-nums">{(confidenceThreshold * 100).toFixed(0)}%</span>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              {/* Main canvas */}
              <div className="xl:col-span-2">
                <GlowCard glowColor="violet" noPad className="overflow-hidden">
                  <CellDetectionCanvas
                    cells={cells}
                    selectedCell={selectedCell}
                    onSelectCell={setSelectedCell}
                    overlay={overlay}
                    showBBox={showBBox}
                    showContour={showContour}
                    showLabels={showLabels}
                  />
                </GlowCard>

                {/* Morphometry histograms */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                  <GlowCard glowColor="violet" noPad className="overflow-hidden">
                    <MorphHistogram cells={cells} metric="area" label="Nuclear Area Distribution" unit="µm²" />
                  </GlowCard>
                  <GlowCard glowColor="sky" noPad className="overflow-hidden">
                    <MorphHistogram cells={cells} metric="circularity" label="Circularity Distribution" unit="" />
                  </GlowCard>
                  <GlowCard glowColor="amber" noPad className="overflow-hidden">
                    <MorphHistogram cells={cells} metric="intensity" label="Stain Intensity Distribution" unit="OD" />
                  </GlowCard>
                </div>
              </div>

              {/* Right panel */}
              <div className="space-y-4">
                {/* Selected cell detail */}
                {selectedCell ? (
                  <GlowCard glowColor="indigo" className="!p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100">Cell #{selectedCell.id}</h3>
                      <span className="text-[10px] px-2 py-0.5 rounded-full font-bold" style={{ backgroundColor: selectedCell.color + '20', color: selectedCell.color }}>
                        {selectedCell.type}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 mb-3">
                      {[
                        { label: 'Position', value: `(${selectedCell.x.toFixed(0)}, ${selectedCell.y.toFixed(0)})` },
                        { label: 'Confidence', value: `${(selectedCell.confidence * 100).toFixed(0)}%` },
                        { label: 'Area', value: `${selectedCell.area} µm²` },
                        { label: 'Circularity', value: selectedCell.circularity },
                        { label: 'Eccentricity', value: selectedCell.eccentricity.toFixed(2) },
                        { label: 'Stain OD', value: selectedCell.intensity },
                      ].map(d => (
                        <div key={d.label} className="p-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
                          <div className="text-[10px] text-gray-400">{d.label}</div>
                          <div className="text-xs font-bold text-gray-800 dark:text-white">{d.value}</div>
                        </div>
                      ))}
                    </div>
                    {selectedCell.type === 'Mitotic' && (
                      <div className="p-2 bg-fuchsia-500/10 rounded-lg text-xs text-fuchsia-600 dark:text-fuchsia-400">
                        Note: Mitotic figure detected — active cell division. Contributes to mitotic index.
                      </div>
                    )}
                    {selectedCell.type === 'Apoptotic' && (
                      <div className="p-2 bg-indigo-500/10 rounded-lg text-xs text-indigo-600 dark:text-indigo-400">
                        ℹ Apoptotic body — fragmented nucleus, condensed chromatin.
                      </div>
                    )}
                  </GlowCard>
                ) : (
                  <GlowCard glowColor="violet" className="!p-5 text-center">
                    <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-1">Click a Cell</h3>
                    <p className="text-xs text-gray-400">Click any detected cell on the slide to inspect morphometry, classification, and stain features.</p>
                  </GlowCard>
                )}

                {/* Cell type breakdown */}
                <GlowCard glowColor="rose" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Cell Type Distribution</h3>
                  <div className="space-y-2">
                    {Object.entries(typeCounts).sort((a, b) => b[1] - a[1]).map(([type, count]) => {
                      const total = cells.length;
                      const pct = ((count / total) * 100).toFixed(1);
                      const cellType = allCells.find(c => c.type === type);
                      const color = cellType?.color || '#888';
                      return (
                        <div key={type}>
                          <div className="flex justify-between mb-0.5">
                            <div className="flex items-center gap-1.5">
                              <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                              <span className="text-xs text-gray-600 dark:text-gray-300">{type}</span>
                            </div>
                            <span className="text-[10px] font-bold text-gray-400 tabular-nums">{count} ({pct}%)</span>
                          </div>
                          <div className="h-1.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                            <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </GlowCard>

                {/* CV Pipeline Status */}
                <GlowCard glowColor="emerald" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">CV Pipeline Modules</h3>
                  <div className="space-y-2">
                    {[
                      { name: 'Stain Normalization (Macenko)', status: 'complete', time: '0.8s' },
                      { name: 'Tile Extraction (256×256)', status: 'complete', time: '1.2s' },
                      { name: 'Cell Detection (HoverNet)', status: 'complete', time: '3.4s' },
                      { name: 'Nuclear Segmentation', status: 'complete', time: '2.1s' },
                      { name: 'Cell Classification (6-class)', status: 'complete', time: '1.8s' },
                      { name: 'Mitosis Detection (RetinaNet)', status: 'complete', time: '2.6s' },
                      { name: 'Tissue Region Segmentation', status: 'complete', time: '1.5s' },
                      { name: 'Morphometry Extraction', status: 'complete', time: '0.6s' },
                    ].map(m => (
                      <div key={m.name} className="flex items-center gap-2">
                        <PulseRing color="emerald" size="sm" />
                        <span className="text-xs text-gray-600 dark:text-gray-300 flex-1">{m.name}</span>
                        <span className="text-[10px] text-gray-400 tabular-nums">{m.time}</span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700/60 flex justify-between">
                    <span className="text-xs text-gray-400">Total pipeline</span>
                    <span className="text-xs font-bold text-emerald-500">14.0s</span>
                  </div>
                </GlowCard>

                {/* Morphometry summary */}
                <GlowCard glowColor="sky" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Nuclear Morphometry Summary</h3>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { label: 'Mean Area', value: `${avgArea} µm²` },
                      { label: 'Mean Circularity', value: avgCirc },
                      { label: 'Pleomorphism Score', value: '2.4 / 3' },
                      { label: 'Nottingham Grade', value: '3 (high)' },
                    ].map(m => (
                      <div key={m.label} className="p-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
                        <div className="text-[10px] text-gray-400">{m.label}</div>
                        <div className="text-sm font-bold text-gray-800 dark:text-white">{m.value}</div>
                      </div>
                    ))}
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
