import { useState, useRef, useEffect, useCallback } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import GlowCard from '../components/GlowCard';

/* ── Drug data ────────────────────────────────────────────────── */
const DRUGS = [
  {
    id: 'trastuzumab', name: 'Trastuzumab', brand: 'Herceptin', class: 'Monoclonal Antibody',
    target: 'HER2 (ERBB2)', mechanism: 'Binds Domain IV of HER2 ECD, blocks ligand-independent HER2 homodimerization, induces ADCC, inhibits downstream PI3K/AKT and RAS/MAPK signaling.',
    molecularWeight: '148 kDa', route: 'IV', halfLife: '28.5 days',
    approvedIndications: ['HER2+ Breast Cancer (adj, neo-adj, metastatic)', 'HER2+ Gastric Cancer'],
    pathways: [
      { name: 'HER2/ERBB2', role: 'Primary target — receptor blockade' },
      { name: 'PI3K/AKT/mTOR', role: 'Downstream inhibition via HER2 blockade' },
      { name: 'RAS/MAPK', role: 'Downstream inhibition' },
      { name: 'ADCC / NK cell', role: 'Fc-mediated immune-dependent killing' },
    ],
    interactions: ['Pertuzumab (synergistic — dual HER2 blockade)', 'T-DM1 (ADC derivative)', 'Lapatinib (additive HER2 inhibition)'],
    resistance: ['PIK3CA mutation (activating) — bypasses HER2 blockade', 'PTEN loss — constitutive PI3K activation', 'HER2 ECD shedding (p95 truncated form)', 'MET amplification — alternative RTK signaling'],
    adverseEvents: ['Cardiotoxicity (LVEF decline 3-7%)', 'Infusion reactions', 'Diarrhea', 'Fatigue'],
    color: '#8b5cf6',
  },
  {
    id: 'pembrolizumab', name: 'Pembrolizumab', brand: 'Keytruda', class: 'Immune Checkpoint Inhibitor',
    target: 'PD-1', mechanism: 'Blocks PD-1/PD-L1 interaction, restoring anti-tumor T cell activity. Reverses T cell exhaustion in the tumor microenvironment.',
    molecularWeight: '149 kDa', route: 'IV', halfLife: '26 days',
    approvedIndications: ['TNBC (neoadjuvant + adjuvant)', 'NSCLC', 'Melanoma', 'MSI-H/dMMR solid tumors'],
    pathways: [
      { name: 'PD-1/PD-L1', role: 'Primary checkpoint blockade' },
      { name: 'T cell activation', role: 'Restores CD8+ cytotoxic function' },
      { name: 'IFN-γ signaling', role: 'Upregulated upon immune activation' },
    ],
    interactions: ['Chemotherapy (enhanced antigen release)', 'PARP inhibitors (synergistic DNA damage + immune response)', 'Lenvatinib (anti-angiogenic + immune)'],
    resistance: ['B2M loss — MHC-I downregulation', 'JAK1/2 mutations — impaired IFN-γ response', 'WNT/β-catenin activation — T cell exclusion', 'Low TMB — insufficient neoantigen load'],
    adverseEvents: ['Immune-mediated hepatitis', 'Pneumonitis', 'Thyroiditis', 'Colitis', 'Adrenal insufficiency'],
    color: '#10b981',
  },
  {
    id: 'olaparib', name: 'Olaparib', brand: 'Lynparza', class: 'PARP Inhibitor',
    target: 'PARP1/2', mechanism: 'Traps PARP at sites of SSBs, converting to lethal DSBs in HRD tumors (BRCA1/2-deficient). Synthetic lethality: cells cannot repair DSBs via HR, leading to genomic catastrophe and apoptosis.',
    molecularWeight: '434.5 Da', route: 'Oral', halfLife: '11.9 hours',
    approvedIndications: ['BRCA+ HER2- Breast Cancer (adj, metastatic)', 'BRCA+ Ovarian Cancer', 'HRD+ Prostate Cancer'],
    pathways: [
      { name: 'PARP1/2 trapping', role: 'Primary — prevents SSB repair' },
      { name: 'Homologous Recombination', role: 'Synthetic lethality in HRD tumors' },
      { name: 'DNA Damage Response', role: 'Overwhelms cell repair machinery' },
      { name: 'STING / cGAS', role: 'Cytoplasmic DNA triggers innate immune activation' },
    ],
    interactions: ['Platinum chemotherapy (overlapping DNA damage)', 'Pembrolizumab (STING pathway activation)', 'CDK4/6 inhibitors (preclinical synergy)'],
    resistance: ['BRCA reversion mutations — restores HR', '53BP1 / REV7 loss — partial HR restoration', 'Drug efflux (P-gp upregulation)', 'PARP1 mutations — reduced trapping'],
    adverseEvents: ['Anemia (40%)', 'Nausea', 'Fatigue', 'MDS/AML (< 1.5%)', 'Neutropenia'],
    color: '#f59e0b',
  },
];

/* ── Pathway network canvas ───────────────────────────────────── */
function PathwayCanvas({ drug }) {
  const canvasRef = useRef(null);
  const frameRef = useRef(0);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const cw = canvas.offsetWidth;
    const ch = 340;
    canvas.width = cw * devicePixelRatio;
    canvas.height = ch * devicePixelRatio;
    ctx.scale(devicePixelRatio, devicePixelRatio);

    ctx.fillStyle = '#0a0a18';
    ctx.fillRect(0, 0, cw, ch);

    const t = performance.now() / 1000;

    // Drug node center
    const cx = cw / 2, cy = 60;
    // Target node
    const tx = cw / 2, ty = 140;
    // Pathway nodes in arc below
    const pathways = drug.pathways;
    const pw = cw - 80;
    const py = 250;

    // Draw edges: drug → target
    ctx.strokeStyle = drug.color + '60';
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(cx, cy + 20); ctx.lineTo(tx, ty - 15); ctx.stroke();
    ctx.setLineDash([]);

    // Draw edges: target → pathways
    pathways.forEach((p, i) => {
      const px2 = 40 + (i / (pathways.length - 1 || 1)) * pw;
      ctx.strokeStyle = drug.color + '30';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(tx, ty + 15);
      ctx.quadraticCurveTo((tx + px2) / 2, py - 40, px2, py - 15);
      ctx.stroke();

      // Flowing dot
      const progress = ((t * 0.3 + i * 0.2) % 1);
      const dotX = (1 - progress) * (1 - progress) * tx + 2 * (1 - progress) * progress * ((tx + px2) / 2) + progress * progress * px2;
      const dotY = (1 - progress) * (1 - progress) * (ty + 15) + 2 * (1 - progress) * progress * (py - 40) + progress * progress * (py - 15);
      ctx.beginPath();
      ctx.arc(dotX, dotY, 3, 0, Math.PI * 2);
      ctx.fillStyle = drug.color;
      ctx.fill();
    });

    // Drug node
    const drugGlow = ctx.createRadialGradient(cx, cy, 0, cx, cy, 40);
    drugGlow.addColorStop(0, drug.color + '40');
    drugGlow.addColorStop(1, 'transparent');
    ctx.fillStyle = drugGlow;
    ctx.beginPath(); ctx.arc(cx, cy, 40, 0, Math.PI * 2); ctx.fill();

    ctx.beginPath(); ctx.arc(cx, cy, 18, 0, Math.PI * 2);
    ctx.fillStyle = drug.color;
    ctx.fill();
    ctx.font = 'bold 8px Inter, sans-serif';
    ctx.fillStyle = '#fff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('DRUG', cx, cy);

    // Target node
    ctx.beginPath(); ctx.arc(tx, ty, 14, 0, Math.PI * 2);
    ctx.fillStyle = '#f43f5e';
    ctx.fill();
    ctx.font = 'bold 7px Inter, sans-serif';
    ctx.fillStyle = '#fff';
    ctx.fillText(drug.target.length > 8 ? drug.target.slice(0, 8) : drug.target, tx, ty);

    // Pathway nodes
    pathways.forEach((p, i) => {
      const px2 = 40 + (i / (pathways.length - 1 || 1)) * pw;
      ctx.beginPath(); ctx.arc(px2, py, 12, 0, Math.PI * 2);
      ctx.fillStyle = '#1e293b';
      ctx.strokeStyle = drug.color + '60';
      ctx.lineWidth = 1.5;
      ctx.fill(); ctx.stroke();

      ctx.font = '7px Inter, sans-serif';
      ctx.fillStyle = '#ffffffaa';
      ctx.textAlign = 'center';
      const label = p.name.length > 12 ? p.name.slice(0, 12) + '…' : p.name;
      ctx.fillText(label, px2, py + 24);
    });

    // Labels
    ctx.font = 'bold 10px Inter, sans-serif';
    ctx.fillStyle = drug.color;
    ctx.textAlign = 'center';
    ctx.fillText(drug.name, cx, cy - 28);
    ctx.font = '9px Inter, sans-serif';
    ctx.fillStyle = '#f43f5e';
    ctx.fillText(drug.target, tx, ty - 22);

    frameRef.current = requestAnimationFrame(draw);
  }, [drug]);

  useEffect(() => {
    frameRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frameRef.current);
  }, [draw]);

  return <canvas ref={canvasRef} className="w-full" style={{ height: 340 }} />;
}

export default function DrugMechanisms() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeDrug, setActiveDrug] = useState(DRUGS[0]);

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[1600px] mx-auto">
            <div className="mb-6">
              <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
                Drug Mechanism Explorer
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Interactive pharmacology — MoA, pathway targets, resistance mechanisms, and drug interactions</p>
            </div>

            <div className="flex gap-2 mb-6">
              {DRUGS.map(d => (
                <button
                  key={d.id}
                  onClick={() => setActiveDrug(d)}
                  className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                    activeDrug.id === d.id
                      ? 'text-white shadow-lg' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700/60'
                  }`}
                  style={activeDrug.id === d.id ? { backgroundColor: d.color, boxShadow: `0 8px 24px ${d.color}40` } : {}}
                >
                  {d.name} ({d.brand})
                </button>
              ))}
            </div>

            {/* Summary strip */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
              {[{ label: 'Class', value: activeDrug.class }, { label: 'Target', value: activeDrug.target }, { label: 'MW', value: activeDrug.molecularWeight }, { label: 'Route', value: activeDrug.route }, { label: 'Half-life', value: activeDrug.halfLife }].map(s => (
                <GlowCard key={s.label} glowColor="amber" className="!p-3 text-center">
                  <div className="text-[10px] uppercase tracking-wider text-gray-400">{s.label}</div>
                  <div className="text-sm font-bold text-gray-800 dark:text-white mt-0.5">{s.value}</div>
                </GlowCard>
              ))}
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              {/* Pathway canvas */}
              <div className="xl:col-span-2">
                <GlowCard glowColor="amber" noPad className="overflow-hidden">
                  <PathwayCanvas drug={activeDrug} />
                </GlowCard>

                {/* Mechanism text */}
                <GlowCard glowColor="violet" className="!p-4 mt-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-2">Mechanism of Action</h3>
                  <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">{activeDrug.mechanism}</p>
                </GlowCard>
              </div>

              {/* Right column */}
              <div className="space-y-4">
                {/* Pathways */}
                <GlowCard glowColor="sky" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Target Pathways</h3>
                  <div className="space-y-2">
                    {activeDrug.pathways.map(p => (
                      <div key={p.name} className="p-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                        <div className="text-xs font-bold text-gray-800 dark:text-gray-100">{p.name}</div>
                        <div className="text-[10px] text-gray-400">{p.role}</div>
                      </div>
                    ))}
                  </div>
                </GlowCard>

                {/* Resistance */}
                <GlowCard glowColor="rose" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Resistance Mechanisms</h3>
                  <div className="space-y-1.5">
                    {activeDrug.resistance.map(r => (
                      <div key={r} className="text-xs text-rose-600 dark:text-rose-400 flex items-start gap-1.5">
                        <span className="mt-0.5 flex-shrink-0 text-gray-400">•</span> {r}
                      </div>
                    ))}
                  </div>
                </GlowCard>

                {/* Drug interactions */}
                <GlowCard glowColor="emerald" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Key Interactions</h3>
                  <div className="space-y-1.5">
                    {activeDrug.interactions.map(i => (
                      <div key={i} className="text-xs text-emerald-600 dark:text-emerald-400 flex items-start gap-1.5">
                        <span className="mt-0.5 flex-shrink-0 text-gray-400">•</span> {i}
                      </div>
                    ))}
                  </div>
                </GlowCard>

                {/* Adverse events */}
                <GlowCard glowColor="amber" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Adverse Events</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {activeDrug.adverseEvents.map(ae => (
                      <span key={ae} className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400">{ae}</span>
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
