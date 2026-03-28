import { useState, useEffect, useRef, useCallback } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import GlowCard from '../components/GlowCard';

/* ── Genomic aberrations as 'stars' ──────────────────────────────── */
const ABERRATIONS = [
  { gene: 'TP53', chr: '17p13.1', type: 'mutation', freq: 0.37, impact: 'Pathogenic', drugs: [], cluster: 0 },
  { gene: 'PIK3CA', chr: '3q26.32', type: 'mutation', freq: 0.28, impact: 'Actionable', drugs: ['Alpelisib'], cluster: 1 },
  { gene: 'ERBB2', chr: '17q12', type: 'amplification', freq: 0.18, impact: 'Actionable', drugs: ['Trastuzumab', 'T-DXd'], cluster: 2 },
  { gene: 'GATA3', chr: '10p14', type: 'mutation', freq: 0.14, impact: 'Pathogenic', drugs: [], cluster: 0 },
  { gene: 'CDH1', chr: '16q22.1', type: 'loss', freq: 0.12, impact: 'Pathogenic', drugs: [], cluster: 3 },
  { gene: 'MYC', chr: '8q24.21', type: 'amplification', freq: 0.16, impact: 'Oncogenic', drugs: [], cluster: 2 },
  { gene: 'BRCA1', chr: '17q21.31', type: 'mutation', freq: 0.05, impact: 'Actionable', drugs: ['Olaparib'], cluster: 4 },
  { gene: 'BRCA2', chr: '13q13.1', type: 'mutation', freq: 0.04, impact: 'Actionable', drugs: ['Olaparib'], cluster: 4 },
  { gene: 'ESR1', chr: '6q25.1', type: 'mutation', freq: 0.08, impact: 'Resistance', drugs: ['Fulvestrant'], cluster: 1 },
  { gene: 'PTEN', chr: '10q23.31', type: 'loss', freq: 0.10, impact: 'Pathogenic', drugs: [], cluster: 1 },
  { gene: 'AKT1', chr: '14q32.33', type: 'mutation', freq: 0.06, impact: 'Actionable', drugs: ['Capivasertib'], cluster: 1 },
  { gene: 'FGFR1', chr: '8p11.23', type: 'amplification', freq: 0.09, impact: 'Emerging', drugs: ['Futibatinib'], cluster: 3 },
  { gene: 'CCND1', chr: '11q13.3', type: 'amplification', freq: 0.15, impact: 'Oncogenic', drugs: ['Palbociclib'], cluster: 5 },
  { gene: 'RB1', chr: '13q14.2', type: 'loss', freq: 0.06, impact: 'Pathogenic', drugs: [], cluster: 5 },
  { gene: 'MAP3K1', chr: '5q11.2', type: 'mutation', freq: 0.08, impact: 'Pathogenic', drugs: [], cluster: 0 },
  { gene: 'NTRK1', chr: '1q23.1', type: 'fusion', freq: 0.02, impact: 'Actionable', drugs: ['Larotrectinib'], cluster: 3 },
  { gene: 'MDM2', chr: '12q15', type: 'amplification', freq: 0.04, impact: 'Emerging', drugs: [], cluster: 0 },
  { gene: 'CDKN2A', chr: '9p21.3', type: 'loss', freq: 0.07, impact: 'Pathogenic', drugs: [], cluster: 5 },
  { gene: 'NF1', chr: '17q11.2', type: 'mutation', freq: 0.05, impact: 'Pathogenic', drugs: [], cluster: 2 },
  { gene: 'ATM', chr: '11q22.3', type: 'mutation', freq: 0.04, impact: 'Actionable', drugs: ['Olaparib'], cluster: 4 },
];

const TYPE_COLORS = {
  mutation: '#8b5cf6',
  amplification: '#f59e0b',
  loss: '#0ea5e9',
  fusion: '#f43f5e',
};

const IMPACT_COLOR = {
  Actionable: '#10b981',
  Pathogenic: '#f43f5e',
  Oncogenic: '#f59e0b',
  Resistance: '#ec4899',
  Emerging: '#6366f1',
};

const CLUSTER_CENTERS = [
  { x: 0.5, y: 0.35 },
  { x: 0.25, y: 0.55 },
  { x: 0.75, y: 0.55 },
  { x: 0.3, y: 0.25 },
  { x: 0.7, y: 0.25 },
  { x: 0.5, y: 0.7 },
];

function positionStars(aberrations) {
  return aberrations.map((a, i) => {
    const center = CLUSTER_CENTERS[a.cluster] || { x: 0.5, y: 0.5 };
    const angle = (i / aberrations.length) * Math.PI * 2 + a.cluster;
    const dist = 0.06 + a.freq * 0.4;
    return {
      ...a,
      x: center.x + Math.cos(angle) * dist * 0.5 + (Math.random() - 0.5) * 0.06,
      y: center.y + Math.sin(angle) * dist * 0.5 + (Math.random() - 0.5) * 0.06,
      size: 3 + a.freq * 25,
      twinklePhase: Math.random() * Math.PI * 2,
    };
  });
}

const CONSTELLATIONS = [
  { name: 'PI3K/AKT/mTOR', genes: ['PIK3CA', 'AKT1', 'PTEN'], color: '#8b5cf6' },
  { name: 'HER2 Amplicon', genes: ['ERBB2', 'MYC', 'NF1'], color: '#f59e0b' },
  { name: 'DNA Repair', genes: ['BRCA1', 'BRCA2', 'ATM'], color: '#0ea5e9' },
  { name: 'Cell Cycle', genes: ['CCND1', 'RB1', 'CDKN2A'], color: '#10b981' },
];

export default function GenomicConstellation() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const canvasRef = useRef(null);
  const starsRef = useRef(positionStars(ABERRATIONS));
  const [selected, setSelected] = useState(null);
  const [showConstellations, setShowConstellations] = useState(true);
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

    // Deep space background
    ctx.fillStyle = '#0a0a1a';
    ctx.fillRect(0, 0, cw, ch);

    // Background nebula
    const neb = ctx.createRadialGradient(cw * 0.3, ch * 0.4, 0, cw * 0.3, ch * 0.4, cw * 0.4);
    neb.addColorStop(0, 'rgba(139,92,246,0.08)');
    neb.addColorStop(0.5, 'rgba(99,102,241,0.04)');
    neb.addColorStop(1, 'transparent');
    ctx.fillStyle = neb;
    ctx.fillRect(0, 0, cw, ch);

    const neb2 = ctx.createRadialGradient(cw * 0.7, ch * 0.6, 0, cw * 0.7, ch * 0.6, cw * 0.3);
    neb2.addColorStop(0, 'rgba(14,165,233,0.06)');
    neb2.addColorStop(1, 'transparent');
    ctx.fillStyle = neb2;
    ctx.fillRect(0, 0, cw, ch);

    const t = performance.now() / 1000;
    const stars = starsRef.current;

    // Constellation lines
    if (showConstellations) {
      for (const c of CONSTELLATIONS) {
        const cStars = c.genes.map(g => stars.find(s => s.gene === g)).filter(Boolean);
        if (cStars.length < 2) continue;
        ctx.strokeStyle = c.color + '40';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        for (let i = 0; i < cStars.length; i++) {
          const s = cStars[i];
          if (i === 0) ctx.moveTo(s.x * cw, s.y * ch);
          else ctx.lineTo(s.x * cw, s.y * ch);
        }
        ctx.stroke();
        ctx.setLineDash([]);

        // Label
        const mid = cStars[Math.floor(cStars.length / 2)];
        ctx.fillStyle = c.color + '80';
        ctx.font = '9px Inter, sans-serif';
        ctx.fillText(c.name, mid.x * cw + 10, mid.y * ch - 10);
      }
    }

    // Draw stars
    for (const star of stars) {
      const px = star.x * cw;
      const py = star.y * ch;
      const twinkle = 0.6 + Math.sin(t * 2 + star.twinklePhase) * 0.4;
      const r = star.size * twinkle;
      const color = TYPE_COLORS[star.type] || '#fff';

      // Outer glow
      const glow = ctx.createRadialGradient(px, py, 0, px, py, r * 3);
      glow.addColorStop(0, color + '40');
      glow.addColorStop(1, 'transparent');
      ctx.fillStyle = glow;
      ctx.fillRect(px - r * 3, py - r * 3, r * 6, r * 6);

      // Cross flare
      ctx.strokeStyle = color + '30';
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(px - r * 2, py); ctx.lineTo(px + r * 2, py);
      ctx.moveTo(px, py - r * 2); ctx.lineTo(px, py + r * 2);
      ctx.stroke();

      // Star body
      ctx.beginPath();
      ctx.arc(px, py, r * 0.6, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.shadowColor = color;
      ctx.shadowBlur = 15;
      ctx.fill();
      ctx.shadowBlur = 0;

      // Actionable ring
      if (star.impact === 'Actionable') {
        ctx.beginPath();
        ctx.arc(px, py, r * 0.9, 0, Math.PI * 2);
        ctx.strokeStyle = '#10b981' + '80';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // Label
      ctx.fillStyle = '#e2e8f060';
      ctx.font = '10px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(star.gene, px, py + r + 12);
      ctx.textAlign = 'start';

      // Selected highlight
      if (selected && selected.gene === star.gene) {
        ctx.beginPath();
        ctx.arc(px, py, r * 1.5, 0, Math.PI * 2);
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([3, 3]);
        ctx.stroke();
        ctx.setLineDash([]);
      }
    }

    frameRef.current = requestAnimationFrame(draw);
  }, [showConstellations, selected]);

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
    for (const s of starsRef.current) {
      const d = Math.hypot(s.x - mx, s.y - my);
      if (d < minD) { minD = d; closest = s; }
    }
    setSelected(minD < 0.05 ? closest : null);
  };

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[1600px] mx-auto">
            <div className="mb-6 flex items-end justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
                  Genomic Constellation
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">20 key aberrations mapped as a starfield — size = frequency, color = alteration type</p>
              </div>
              <label className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 cursor-pointer">
                <input type="checkbox" checked={showConstellations} onChange={() => setShowConstellations(!showConstellations)} className="rounded text-violet-500" />
                Show Pathways
              </label>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
              <div className="xl:col-span-3">
                <GlowCard glowColor="indigo" noPad className="overflow-hidden">
                  <canvas ref={canvasRef} className="w-full cursor-crosshair" style={{ height: 540 }} onClick={handleClick} />
                </GlowCard>
              </div>

              <div className="space-y-4">
                {/* Legend */}
                <GlowCard glowColor="violet" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Alteration Types</h3>
                  {Object.entries(TYPE_COLORS).map(([k, c]) => (
                    <div key={k} className="flex items-center gap-2 mb-1.5">
                      <span className="w-3 h-3 rounded-full" style={{ backgroundColor: c }} />
                      <span className="text-xs text-gray-600 dark:text-gray-300 capitalize">{k}</span>
                    </div>
                  ))}
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mt-4 mb-3">Impact</h3>
                  {Object.entries(IMPACT_COLOR).map(([k, c]) => (
                    <div key={k} className="flex items-center gap-2 mb-1.5">
                      <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: c }} />
                      <span className="text-xs text-gray-600 dark:text-gray-300">{k}</span>
                    </div>
                  ))}
                </GlowCard>

                {/* Selected star detail */}
                {selected && (
                  <GlowCard glowColor="sky" className="!p-4">
                    <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-2">{selected.gene}</h3>
                    <div className="space-y-1.5 text-xs">
                      <div className="flex justify-between"><span className="text-gray-400">Locus:</span><span>{selected.chr}</span></div>
                      <div className="flex justify-between"><span className="text-gray-400">Alteration:</span><span className="capitalize" style={{ color: TYPE_COLORS[selected.type] }}>{selected.type}</span></div>
                      <div className="flex justify-between"><span className="text-gray-400">Frequency:</span><span>{(selected.freq * 100).toFixed(0)}%</span></div>
                      <div className="flex justify-between"><span className="text-gray-400">Impact:</span><span style={{ color: IMPACT_COLOR[selected.impact] }}>{selected.impact}</span></div>
                      {selected.drugs.length > 0 && (
                        <div>
                          <span className="text-gray-400">Targeted Therapies:</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {selected.drugs.map(d => (
                              <span key={d} className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[10px] font-semibold">{d}</span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </GlowCard>
                )}

                {/* Summary stats */}
                <GlowCard glowColor="emerald" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-2">Summary</h3>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex justify-between"><span className="text-gray-400">Total Aberrations</span><span className="font-bold">{ABERRATIONS.length}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Actionable</span><span className="font-bold text-emerald-500">{ABERRATIONS.filter(a => a.impact === 'Actionable').length}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Pathogenic</span><span className="font-bold text-rose-500">{ABERRATIONS.filter(a => a.impact === 'Pathogenic').length}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Targeted Drugs</span><span className="font-bold text-sky-500">{new Set(ABERRATIONS.flatMap(a => a.drugs)).size}</span></div>
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
