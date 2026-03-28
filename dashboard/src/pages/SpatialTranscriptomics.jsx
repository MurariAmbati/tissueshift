import { useState, useRef, useEffect, useCallback } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import GlowCard from '../components/GlowCard';
import AnimatedCounter from '../components/AnimatedCounter';

/* ── Tissue sample spots — simulated spatial data ──────────────── */
function generateSpots(n, width, height) {
  const spots = [];
  const genes = ['ESR1','PGR','ERBB2','MKI67','CD8A','CD4','FOXP3','CD68','PDCD1','VIM','CDH1','TP53','COL1A1','PECAM1','PTPRC','EPCAM'];
  const clusters = [
    { label: 'Tumor Core', cx: 0.35, cy: 0.4, r: 0.15, color: '#8b5cf6' },
    { label: 'Immune Hot', cx: 0.6, cy: 0.35, r: 0.1, color: '#10b981' },
    { label: 'Stroma', cx: 0.5, cy: 0.65, r: 0.18, color: '#f59e0b' },
    { label: 'Normal', cx: 0.2, cy: 0.7, r: 0.12, color: '#0ea5e9' },
    { label: 'Leading Edge', cx: 0.75, cy: 0.55, r: 0.1, color: '#f43f5e' },
  ];
  for (let i = 0; i < n; i++) {
    const cl = clusters[Math.floor(Math.random() * clusters.length)];
    const angle = Math.random() * Math.PI * 2;
    const dist = Math.random() * cl.r;
    const x = (cl.cx + Math.cos(angle) * dist) * width;
    const y = (cl.cy + Math.sin(angle) * dist) * height;
    const expr = {};
    genes.forEach(g => { expr[g] = Math.random(); });
    spots.push({ id: i, x, y, cluster: cl.label, color: cl.color, expression: expr, genes });
  }
  return { spots, clusters, genes };
}

/* ── The spatial canvas ──────────────────────────────────────── */
function SpatialCanvas({ width = 640, height = 480, gene, onSelectSpot }) {
  const canvasRef = useRef(null);
  const dataRef = useRef(null);
  const frameRef = useRef(0);
  const hoverRef = useRef(null);

  if (!dataRef.current) {
    dataRef.current = generateSpots(600, width, height);
  }
  const { spots, clusters } = dataRef.current;

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = devicePixelRatio;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    // Background — tissue-like wash
    const bg = ctx.createRadialGradient(width / 2, height / 2, 0, width / 2, height / 2, width * 0.6);
    bg.addColorStop(0, '#1a1028');
    bg.addColorStop(1, '#0a0a14');
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, width, height);

    // Grid lines (faint)
    ctx.strokeStyle = '#ffffff06';
    ctx.lineWidth = 0.5;
    for (let gx = 0; gx < width; gx += 40) {
      ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, height); ctx.stroke();
    }
    for (let gy = 0; gy < height; gy += 40) {
      ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(width, gy); ctx.stroke();
    }

    // Draw spots
    const t = performance.now() / 1000;
    spots.forEach(s => {
      const val = gene ? s.expression[gene] : 0.5;
      const r = 3 + val * 4;
      const alpha = 0.2 + val * 0.7;

      // Halo
      const glow = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, r * 3);
      glow.addColorStop(0, `${s.color}30`);
      glow.addColorStop(1, 'transparent');
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(s.x, s.y, r * 3, 0, Math.PI * 2);
      ctx.fill();

      // Spot
      ctx.beginPath();
      ctx.arc(s.x, s.y, r, 0, Math.PI * 2);
      ctx.fillStyle = gene
        ? `rgba(${Math.round(val * 255)}, ${Math.round((1 - val) * 100)}, ${Math.round((1 - val) * 255)}, ${alpha})`
        : `${s.color}${Math.round(alpha * 255).toString(16).padStart(2, '0')}`;
      ctx.fill();
    });

    // Cluster labels
    clusters.forEach(cl => {
      const cx = cl.cx * width, cy = cl.cy * height;
      ctx.font = '10px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillStyle = '#ffffff50';
      ctx.fillText(cl.label, cx, cy - cl.r * height - 8);
    });

    // Hover highlight
    const h = hoverRef.current;
    if (h) {
      ctx.beginPath();
      ctx.arc(h.x, h.y, 12, 0, Math.PI * 2);
      ctx.strokeStyle = '#ffffff80';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // Scale bar
    ctx.fillStyle = '#ffffff40';
    ctx.fillRect(width - 80, height - 20, 60, 2);
    ctx.font = '9px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('100 µm', width - 50, height - 8);

    frameRef.current = requestAnimationFrame(draw);
  }, [gene, width, height, spots, clusters]);

  useEffect(() => {
    frameRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frameRef.current);
  }, [draw]);

  const handleMove = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (width / rect.width);
    const my = (e.clientY - rect.top) * (height / rect.height);
    let found = null;
    for (const s of spots) {
      const dx = s.x - mx, dy = s.y - my;
      if (dx * dx + dy * dy < 100) { found = s; break; }
    }
    hoverRef.current = found;
  };

  const handleClick = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (width / rect.width);
    const my = (e.clientY - rect.top) * (height / rect.height);
    for (const s of spots) {
      const dx = s.x - mx, dy = s.y - my;
      if (dx * dx + dy * dy < 100) { onSelectSpot?.(s); break; }
    }
  };

  return (
    <canvas
      ref={canvasRef}
      className="w-full rounded-xl cursor-crosshair"
      style={{ height }}
      onMouseMove={handleMove}
      onClick={handleClick}
    />
  );
}

/* ── Mini expression heatmap row ─────────────────────────────── */
function GeneBar({ gene, value }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] font-mono text-gray-400 w-14 truncate">{gene}</span>
      <div className="flex-1 h-2 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${value * 100}%`, backgroundColor: `hsl(${(1 - value) * 240}, 80%, 55%)` }} />
      </div>
      <span className="text-[10px] text-gray-400 tabular-nums w-8 text-right">{(value * 100).toFixed(0)}%</span>
    </div>
  );
}

/* ── Full Page ────────────────────────────────────────────────── */
export default function SpatialTranscriptomics() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedGene, setSelectedGene] = useState(null);
  const [selectedSpot, setSelectedSpot] = useState(null);

  const genes = ['ESR1','PGR','ERBB2','MKI67','CD8A','CD4','FOXP3','CD68','PDCD1','VIM','CDH1','TP53','COL1A1','PECAM1','PTPRC','EPCAM'];

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[1600px] mx-auto">
            <div className="mb-6">
              <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
                Spatial Transcriptomics Atlas
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Click spots to inspect gene expression. Select a gene to color spots by expression magnitude.</p>
            </div>

            {/* Gene selector bar */}
            <div className="flex gap-1.5 flex-wrap mb-5">
              <button
                onClick={() => setSelectedGene(null)}
                className={`px-2 py-1 rounded text-[10px] font-semibold transition-colors ${
                  !selectedGene ? 'bg-violet-500 text-white' : 'bg-white dark:bg-gray-800 text-gray-500 border border-gray-200 dark:border-gray-700/60 hover:border-violet-300'
                }`}
              >
                Clusters
              </button>
              {genes.map(g => (
                <button
                  key={g}
                  onClick={() => setSelectedGene(g)}
                  className={`px-2 py-1 rounded text-[10px] font-mono font-semibold transition-colors ${
                    selectedGene === g ? 'bg-violet-500 text-white' : 'bg-white dark:bg-gray-800 text-gray-500 border border-gray-200 dark:border-gray-700/60 hover:border-violet-300'
                  }`}
                >
                  {g}
                </button>
              ))}
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              <div className="xl:col-span-2">
                <GlowCard glowColor="violet" noPad className="overflow-hidden">
                  <SpatialCanvas gene={selectedGene} onSelectSpot={setSelectedSpot} />
                </GlowCard>
              </div>

              <div className="space-y-4">
                {/* Spot detail */}
                {selectedSpot ? (
                  <>
                    <GlowCard glowColor="indigo" className="!p-4">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100">Spot #{selectedSpot.id}</h3>
                        <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold" style={{ backgroundColor: `${selectedSpot.color}20`, color: selectedSpot.color }}>
                          {selectedSpot.cluster}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 mb-3">
                        <div className="text-center p-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                          <div className="text-[10px] text-gray-400">X</div>
                          <div className="text-sm font-bold text-gray-800 dark:text-white">{selectedSpot.x.toFixed(1)}</div>
                        </div>
                        <div className="text-center p-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                          <div className="text-[10px] text-gray-400">Y</div>
                          <div className="text-sm font-bold text-gray-800 dark:text-white">{selectedSpot.y.toFixed(1)}</div>
                        </div>
                      </div>
                      <h4 className="text-[10px] uppercase tracking-wider text-gray-400 mb-2">Gene Expression Profile</h4>
                      <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
                        {selectedSpot.genes.map(g => (
                          <GeneBar key={g} gene={g} value={selectedSpot.expression[g]} />
                        ))}
                      </div>
                    </GlowCard>
                  </>
                ) : (
                  <GlowCard glowColor="violet" className="!p-6 text-center">

                    <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-1">Click a Spot</h3>
                    <p className="text-xs text-gray-400">Hover and click tissue spots on the spatial map to see the gene expression profile.</p>
                  </GlowCard>
                )}

                {/* Region Summary */}
                <GlowCard glowColor="emerald" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Region Summary</h3>
                  {['Tumor Core', 'Immune Hot', 'Stroma', 'Normal', 'Leading Edge'].map((r, i) => {
                    const colors = ['#8b5cf6', '#10b981', '#f59e0b', '#0ea5e9', '#f43f5e'];
                    const counts = [145, 92, 188, 108, 67];
                    return (
                      <div key={r} className="flex items-center gap-2 mb-2">
                        <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: colors[i] }} />
                        <span className="text-xs text-gray-600 dark:text-gray-300 flex-1">{r}</span>
                        <span className="text-xs font-bold text-gray-800 dark:text-white tabular-nums">{counts[i]} spots</span>
                      </div>
                    );
                  })}
                </GlowCard>

                {/* Legend when gene selected */}
                {selectedGene && (
                  <GlowCard glowColor="sky" className="!p-4">
                    <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Expression Scale — {selectedGene}</h3>
                    <div className="h-3 rounded-full overflow-hidden" style={{ background: 'linear-gradient(to right, hsl(240,80%,55%), hsl(120,80%,55%), hsl(0,80%,55%))' }} />
                    <div className="flex justify-between mt-1">
                      <span className="text-[10px] text-gray-400">Low</span>
                      <span className="text-[10px] text-gray-400">High</span>
                    </div>
                  </GlowCard>
                )}
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
