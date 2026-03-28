import { useState, useEffect, useRef, useCallback } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import GlowCard from '../components/GlowCard';

/* ── Generate spatial cell graph ─────────────────────────────────── */
const CELL_COLORS = {
  tumor:  '#f43f5e',
  cd8:    '#10b981',
  cd4:    '#22d3ee',
  macro:  '#f59e0b',
  fibro:  '#a78bfa',
  treg:   '#fb923c',
  bcell:  '#3b82f6',
};

const CELL_LABELS = {
  tumor: 'Tumor', cd8: 'CD8+ T', cd4: 'CD4+ T', macro: 'Macrophage',
  fibro: 'Fibroblast', treg: 'T-reg', bcell: 'B Cell',
};

function generateGraph(nodeCount = 120, seed = 7) {
  const rng = (i) => { const s = Math.sin(i * 127.1 + seed) * 43758.5; return s - Math.floor(s); };
  const types = Object.keys(CELL_COLORS);
  const weights = [0.28, 0.15, 0.10, 0.12, 0.15, 0.08, 0.12];

  const nodes = [];
  for (let i = 0; i < nodeCount; i++) {
    let r = rng(i * 3), cum = 0, type = types[0];
    for (let j = 0; j < weights.length; j++) { cum += weights[j]; if (r <= cum) { type = types[j]; break; } }
    // Cluster tumor cells
    let x, y;
    if (type === 'tumor') {
      const a = rng(i * 5) * Math.PI * 2;
      const d = rng(i * 7) * 0.22 + 0.03;
      x = 0.45 + Math.cos(a) * d; y = 0.48 + Math.sin(a) * d;
    } else if (type === 'cd8' || type === 'cd4') {
      const a = rng(i * 11) * Math.PI * 2;
      const d = rng(i * 13) * 0.12 + 0.22;
      x = 0.45 + Math.cos(a) * d; y = 0.48 + Math.sin(a) * d;
    } else {
      x = 0.05 + rng(i * 17) * 0.9; y = 0.05 + rng(i * 19) * 0.9;
    }
    nodes.push({ id: i, type, x, y });
  }

  // kNN edges (k=4)
  const edges = [];
  const K = 4;
  nodes.forEach((n, i) => {
    const dists = nodes.map((m, j) => ({ j, d: Math.hypot(n.x - m.x, n.y - m.y) }))
      .filter(d => d.j !== i)
      .sort((a, b) => a.d - b.d);
    for (let k = 0; k < K; k++) {
      const j = dists[k].j;
      if (!edges.some(e => (e.s === i && e.t === j) || (e.s === j && e.t === i))) {
        const sType = nodes[i].type, tType = nodes[j].type;
        const interacting = (sType === 'cd8' && tType === 'tumor') || (sType === 'tumor' && tType === 'cd8')
          || (sType === 'macro' && tType === 'tumor') || (sType === 'tumor' && tType === 'macro');
        edges.push({ s: i, t: j, dist: dists[k].d, interacting });
      }
    }
  });

  return { nodes, edges };
}

/* ── GNN layer definitions ───────────────────────────────────────── */
const GNN_ARCH = [
  { name: 'Node Features', dim: '7-dim one-hot', desc: 'Cell type encoding' },
  { name: 'GATConv Layer 1', dim: '64', desc: '4-head attention, LeakyReLU' },
  { name: 'GATConv Layer 2', dim: '64', desc: '4-head attention, LeakyReLU' },
  { name: 'GATConv Layer 3', dim: '32', desc: '2-head attention' },
  { name: 'Global Pool', dim: '32', desc: 'Mean + Max pooling' },
  { name: 'MLP Head', dim: '3', desc: 'Softmax classification' },
];

/* ── Interaction stats ───────────────────────────────────────────── */
function computeGraphStats(graph) {
  const typeCounts = {};
  graph.nodes.forEach(n => { typeCounts[n.type] = (typeCounts[n.type] || 0) + 1; });
  const interactionCount = graph.edges.filter(e => e.interacting).length;
  const avgDegree = (graph.edges.length * 2 / graph.nodes.length).toFixed(1);
  const avgDist = (graph.edges.reduce((s, e) => s + e.dist, 0) / graph.edges.length * 1000).toFixed(0);
  return { typeCounts, interactionCount, avgDegree, avgDist, totalEdges: graph.edges.length };
}

export default function CellGraphNetwork() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const canvasRef = useRef(null);
  const [graph] = useState(() => generateGraph());
  const [hovered, setHovered] = useState(null);
  const [selectedType, setSelectedType] = useState(null);
  const [showEdges, setShowEdges] = useState(true);
  const [showInteractions, setShowInteractions] = useState(true);
  const [highlightNeighbors, setHighlightNeighbors] = useState(true);
  const stats = computeGraphStats(graph);

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

    // Background grid
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 0.3;
    for (let i = 0; i <= 10; i++) {
      ctx.beginPath(); ctx.moveTo((i / 10) * w, 0); ctx.lineTo((i / 10) * w, h); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, (i / 10) * h); ctx.lineTo(w, (i / 10) * h); ctx.stroke();
    }

    const neighbors = new Set();
    if (hovered !== null && highlightNeighbors) {
      graph.edges.forEach(e => {
        if (e.s === hovered) neighbors.add(e.t);
        if (e.t === hovered) neighbors.add(e.s);
      });
    }

    // Edges
    if (showEdges) {
      graph.edges.forEach(e => {
        if (selectedType && graph.nodes[e.s].type !== selectedType && graph.nodes[e.t].type !== selectedType) return;
        if (!showInteractions && !e.interacting) return;
        const ns = graph.nodes[e.s], nt = graph.nodes[e.t];
        ctx.strokeStyle = e.interacting ? '#f43f5e' : '#d1d5db';
        ctx.lineWidth = e.interacting ? 1.2 : 0.4;
        ctx.globalAlpha = (hovered !== null && !neighbors.has(e.s) && !neighbors.has(e.t) && e.s !== hovered && e.t !== hovered) ? 0.08 : (e.interacting ? 0.6 : 0.3);
        ctx.beginPath();
        ctx.moveTo(ns.x * w, ns.y * h);
        ctx.lineTo(nt.x * w, nt.y * h);
        ctx.stroke();
      });
      ctx.globalAlpha = 1;
    }

    // Nodes
    graph.nodes.forEach(n => {
      if (selectedType && n.type !== selectedType) { ctx.globalAlpha = 0.1; } else if (hovered !== null && n.id !== hovered && !neighbors.has(n.id)) { ctx.globalAlpha = 0.15; } else { ctx.globalAlpha = 1; }
      ctx.fillStyle = CELL_COLORS[n.type];
      const r = n.id === hovered ? 6 : 4;
      ctx.beginPath();
      ctx.arc(n.x * w, n.y * h, r, 0, Math.PI * 2);
      ctx.fill();
      if (n.id === hovered) {
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    });
    ctx.globalAlpha = 1;

    // Tooltip
    if (hovered !== null) {
      const n = graph.nodes[hovered];
      const tx = n.x * w + 10, ty = n.y * h - 10;
      const deg = graph.edges.filter(e => e.s === hovered || e.t === hovered).length;
      const label = `${CELL_LABELS[n.type]} (deg: ${deg})`;
      ctx.font = '11px Inter, sans-serif';
      const tw = ctx.measureText(label).width;
      ctx.fillStyle = 'rgba(0,0,0,0.75)';
      ctx.roundRect(tx - 4, ty - 14, tw + 8, 18, 4);
      ctx.fill();
      ctx.fillStyle = '#fff';
      ctx.fillText(label, tx, ty);
    }
  }, [graph, hovered, selectedType, showEdges, showInteractions, highlightNeighbors]);

  useEffect(() => { draw(); }, [draw]);

  const handleMouseMove = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) / rect.width;
    const my = (e.clientY - rect.top) / rect.height;
    let closest = null, minD = 0.03;
    graph.nodes.forEach(n => {
      const d = Math.hypot(n.x - mx, n.y - my);
      if (d < minD) { minD = d; closest = n.id; }
    });
    setHovered(closest);
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
            <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-1">Cell Graph Network</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
              Spatial graph neural network for cell-cell interaction analysis &middot; {graph.nodes.length} nodes &middot; {graph.edges.length} edges
            </p>

            <div className="grid grid-cols-12 gap-6">
              {/* Graph canvas */}
              <div className="col-span-12 xl:col-span-8">
                <GlowCard>
                  <div className="p-4">
                    <div className="flex flex-wrap items-center gap-2 mb-3">
                      <label className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
                        <input type="checkbox" checked={showEdges} onChange={() => setShowEdges(!showEdges)} className="rounded text-violet-500" /> Edges
                      </label>
                      <label className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
                        <input type="checkbox" checked={showInteractions} onChange={() => setShowInteractions(!showInteractions)} className="rounded text-violet-500" /> Interactions only
                      </label>
                      <label className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
                        <input type="checkbox" checked={highlightNeighbors} onChange={() => setHighlightNeighbors(!highlightNeighbors)} className="rounded text-violet-500" /> Neighbor highlight
                      </label>
                      <div className="h-5 w-px bg-gray-300 dark:bg-gray-600 mx-1" />
                      <button
                        onClick={() => setSelectedType(null)}
                        className={`px-2 py-1 rounded text-xs font-medium transition ${!selectedType ? 'bg-violet-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'}`}
                      >All</button>
                      {Object.entries(CELL_LABELS).map(([type, label]) => (
                        <button
                          key={type}
                          onClick={() => setSelectedType(selectedType === type ? null : type)}
                          className={`px-2 py-1 rounded text-xs font-medium transition ${selectedType === type ? 'text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'}`}
                          style={selectedType === type ? { backgroundColor: CELL_COLORS[type] } : {}}
                        >{label}</button>
                      ))}
                    </div>
                    <canvas
                      ref={canvasRef}
                      className="w-full rounded-lg bg-white dark:bg-gray-950 border border-gray-200 dark:border-gray-700 cursor-crosshair"
                      style={{ height: 440 }}
                      onMouseMove={handleMouseMove}
                      onMouseLeave={() => setHovered(null)}
                    />
                  </div>
                </GlowCard>
              </div>

              {/* Right panel */}
              <div className="col-span-12 xl:col-span-4 flex flex-col gap-4">
                {/* Cell composition */}
                <GlowCard>
                  <div className="p-4">
                    <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3">Cell Composition</h2>
                    <div className="space-y-2">
                      {Object.entries(stats.typeCounts).sort((a, b) => b[1] - a[1]).map(([type, count]) => (
                        <div key={type}>
                          <div className="flex justify-between text-xs mb-0.5">
                            <span className="text-gray-600 dark:text-gray-400">{CELL_LABELS[type]}</span>
                            <span className="font-semibold text-gray-800 dark:text-gray-100">{count} ({((count / graph.nodes.length) * 100).toFixed(0)}%)</span>
                          </div>
                          <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                            <div className="h-full rounded-full" style={{ width: `${(count / graph.nodes.length) * 100}%`, backgroundColor: CELL_COLORS[type] }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </GlowCard>

                {/* Graph metrics */}
                <GlowCard>
                  <div className="p-4">
                    <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3">Graph Metrics</h2>
                    <dl className="space-y-2">
                      {[
                        { label: 'Total Nodes', value: graph.nodes.length },
                        { label: 'Total Edges', value: stats.totalEdges },
                        { label: 'Avg Degree', value: stats.avgDegree },
                        { label: 'Avg Edge Distance', value: `${stats.avgDist} \u00b5m` },
                        { label: 'Immune-Tumor Interactions', value: stats.interactionCount },
                        { label: 'Graph Density', value: (2 * stats.totalEdges / (graph.nodes.length * (graph.nodes.length - 1))).toFixed(4) },
                      ].map(row => (
                        <div key={row.label} className="flex justify-between">
                          <dt className="text-xs text-gray-500 dark:text-gray-400">{row.label}</dt>
                          <dd className="text-xs font-semibold text-gray-800 dark:text-gray-100">{row.value}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                </GlowCard>

                {/* GNN architecture */}
                <GlowCard>
                  <div className="p-4">
                    <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3">GNN Architecture (GAT)</h2>
                    <ol className="space-y-2">
                      {GNN_ARCH.map((layer, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="flex items-center justify-center w-5 h-5 rounded bg-violet-100 dark:bg-violet-500/20 text-violet-600 dark:text-violet-400 text-[10px] font-bold shrink-0 mt-0.5">{i + 1}</span>
                          <div>
                            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{layer.name}</span>
                            <span className="text-[10px] text-gray-400 ml-1">({layer.dim})</span>
                            <p className="text-[10px] text-gray-500">{layer.desc}</p>
                          </div>
                        </li>
                      ))}
                    </ol>
                  </div>
                </GlowCard>

                {/* Interaction matrix hint */}
                <GlowCard>
                  <div className="p-4">
                    <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3">Interaction Matrix</h2>
                    <div className="overflow-x-auto">
                      <table className="w-full text-[9px]">
                        <thead>
                          <tr>
                            <th className="text-left p-0.5"></th>
                            {Object.keys(CELL_LABELS).slice(0, 5).map(t => (
                              <th key={t} className="p-0.5 text-center font-medium" style={{ color: CELL_COLORS[t] }}>{t.slice(0, 2).toUpperCase()}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {Object.keys(CELL_LABELS).slice(0, 5).map((row, ri) => (
                            <tr key={row}>
                              <td className="p-0.5 font-medium" style={{ color: CELL_COLORS[row] }}>{row.slice(0, 2).toUpperCase()}</td>
                              {Object.keys(CELL_LABELS).slice(0, 5).map((col, ci) => {
                                const count = graph.edges.filter(e =>
                                  (graph.nodes[e.s].type === row && graph.nodes[e.t].type === col) ||
                                  (graph.nodes[e.s].type === col && graph.nodes[e.t].type === row)
                                ).length;
                                const intensity = Math.min(count / 15, 1);
                                return (
                                  <td key={col} className="p-0.5 text-center rounded" style={{ backgroundColor: `rgba(124, 58, 237, ${intensity * 0.4})` }}>
                                    <span className="text-gray-700 dark:text-gray-300">{count}</span>
                                  </td>
                                );
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
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
