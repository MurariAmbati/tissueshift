'use client';

import Link from 'next/link';
import ArchitectureDiagram from '@/components/ArchitectureDiagram';

const MODALITIES = [
  { label: 'PATHOLOGY', desc: 'UNI ViT-L/16 encoder with LoRA adaptation. Region tokenization with attention pooling + ABMIL slide aggregation.', dim: '512d' },
  { label: 'MOLECULAR', desc: 'Gene expression, pathway activity (ssGSEA), and proteomic encoders with learned modality dropout.', dim: '256d' },
  { label: 'SPATIAL', desc: 'Graph neural network over cell-level neighborhoods. Encodes microenvironment structure and TIL infiltration.', dim: '128d' },
  { label: 'TEMPORAL', desc: 'Subtype lattice transition model with learned adjacency. Captures drift probability across progression states.', dim: 'lattice' },
];

const TRACKS = [
  { name: 'SubtypeCall', task: 'PAM50 subtype from H&E', metric: 'Macro-F1', target: '0.92', status: 'active' as const },
  { name: 'SubtypeDrift', task: 'Predict subtype change primary → met', metric: 'AUROC', target: '0.85', status: 'active' as const },
  { name: 'ProgressionStage', task: 'Pre-invasive → metastatic stage', metric: 'QWK', target: '0.80', status: 'active' as const },
  { name: 'Morph2Mol', task: 'Predict expression from morphology', metric: 'R²', target: '0.45', status: 'active' as const },
  { name: 'Survival', task: 'Overall survival risk prediction', metric: 'C-index', target: '0.72', status: 'active' as const },
  { name: 'SpatialPhenotype', task: 'Spatial cell neighborhood prediction', metric: 'R²-TIL', target: '0.50', status: 'dev' as const },
];

const ROADMAP = [
  {
    phase: 'CORE MODEL',
    title: 'Pathology Encoder + Subtype Heads',
    desc: 'UNI ViT backbone, region tokenization, ABMIL aggregation, cross-attention fusion, and primary prediction heads. Validated on TCGA-BRCA.',
    status: 'active' as const,
    badge: 'COMPLETE',
  },
  {
    phase: 'MOLECULAR BRIDGE',
    title: 'Morph2Mol & Expression Encoders',
    desc: 'Gene expression encoder, pathway-level encoder (ssGSEA), proteomic encoder. Morphology-to-molecule prediction with spatial grounding.',
    status: 'active' as const,
    badge: 'COMPLETE',
  },
  {
    phase: 'TEMPORAL DYNAMICS',
    title: 'Transition Lattice & Drift Detection',
    desc: 'Subtype transition model with learned lattice adjacency. Drift probability estimation. Progression stage ordinal regression.',
    status: 'dev' as const,
    badge: 'IN DEVELOPMENT',
  },
  {
    phase: 'SPATIAL & VALIDATION',
    title: 'Graph Encoder & Multi-Cohort Testing',
    desc: 'Cell-graph spatial encoder (PyG). CPTAC external validation. HTAN spatial atlas integration. Multi-institution generalization.',
    status: 'dev' as const,
    badge: 'IN DEVELOPMENT',
  },
];

const DATA_SOURCES = [
  { name: 'TCGA-BRCA', subjects: '1,098', role: 'Primary training', access: 'Open' },
  { name: 'CPTAC-BRCA', subjects: '198', role: 'External validation', access: 'Open' },
  { name: 'Human Protein Atlas', subjects: '—', role: 'Protein grounding', access: 'Open' },
  { name: 'HTAN Breast', subjects: '60+', role: 'Spatial atlases', access: 'Open' },
];

function StatusBadge({ status, label }: { status: 'active' | 'dev' | 'planned'; label?: string }) {
  const cls = status === 'active' ? 'badge-active' : status === 'dev' ? 'badge-dev' : 'badge-planned';
  const text = label || (status === 'active' ? 'ACTIVE' : status === 'dev' ? 'IN DEVELOPMENT' : 'PLANNED');
  return <span className={`badge ${cls}`}>{text}</span>;
}

export default function HomePage() {
  return (
    <div className="min-h-screen">

      {/* ── HERO ── */}
      <section className="relative flex min-h-[92vh] flex-col justify-center px-6 sm:px-12 lg:px-24">
        <div className="mx-auto w-full max-w-[1400px]">
          <p className="section-label mb-8">
            Open Temporal Histopathology-to-Omics
          </p>
          <h1 className="text-[clamp(2.5rem,7vw,5.5rem)] font-bold leading-[1.05] tracking-[-0.02em]">
            Subtype Is Not<br />
            a Label. It&apos;s a<br />
            <span className="text-[#555]">Trajectory.</span>
          </h1>
          <p className="mt-8 max-w-xl text-[17px] leading-[1.7] text-[#777]">
            TissueShift fuses histopathology, transcriptomics, proteomics, and
            spatial context to model how breast cancer subtypes emerge, drift,
            and progress over time. Open-source. Consumer-GPU trainable.
          </p>
          <div className="mt-10 flex flex-wrap items-center gap-4">
            <Link
              href="/atlas"
              className="font-mono text-[11px] tracking-[0.15em] bg-white text-black px-6 py-3 hover:bg-white/90 transition-colors"
            >
              EXPLORE ATLAS &rarr;
            </Link>
            <a
              href="#model"
              className="font-mono text-[11px] tracking-[0.15em] border border-white/20 text-white/70 px-6 py-3 hover:border-white/40 hover:text-white transition-colors"
            >
              VIEW ARCHITECTURE
            </a>
          </div>
          <div className="mt-16 flex flex-wrap gap-3">
            {DATA_SOURCES.map((d) => (
              <span key={d.name} className="badge badge-active">
                {d.name} {d.subjects !== '—' ? `· ${d.subjects}` : ''}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── 01 · THE PROBLEM ── */}
      <section id="problem" className="border-t border-[#1a1a1a]">
        <div className="mx-auto max-w-[1400px] px-6 sm:px-12 lg:px-24 py-24 lg:py-32">
          <p className="section-label mb-6">01 &middot; THE PROBLEM</p>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold leading-[1.1] tracking-[-0.01em] max-w-3xl">
            Static Subtyping Misses<br />
            Cancer Evolution.
          </h2>
          <div className="mt-10 grid gap-10 lg:grid-cols-2 max-w-5xl">
            <p className="text-[15px] leading-[1.8] text-[#777]">
              Most breast-cancer AI assigns a single subtype label from a single
              biopsy and stops. But receptor discordance between primary and
              metastatic disease is well-documented. Subtypes shift. Tumors
              evolve. Treatment strategies built on static labels miss the
              trajectory entirely.
            </p>
            <p className="text-[15px] leading-[1.8] text-[#777]">
              Paired primary&ndash;metastatic studies show intrinsic subtype
              conversion rates of 20&ndash;40%. ER/PR loss, HER2 gain, basal
              emergence&nbsp;&mdash; these transitions reshape treatment options.
              The window to detect them from morphology alone is narrow but
              measurable.
            </p>
          </div>
        </div>
      </section>

      {/* ── 02 · THE MODEL ── */}
      <section id="model" className="border-t border-[#1a1a1a]">
        <div className="mx-auto max-w-[1400px] px-6 sm:px-12 lg:px-24 py-24 lg:py-32">
          <p className="section-label mb-6">02 &middot; THE MODEL</p>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold leading-[1.1] tracking-[-0.01em] max-w-3xl">
            Read Morphology.<br />
            <span className="text-[#555]">Predict Molecular Trajectory.</span>
          </h2>
          <p className="mt-8 max-w-xl text-[15px] leading-[1.8] text-[#777]">
            TissueShift builds a shared latent tissue manifold from four input
            modalities, then models subtype transitions as paths through that
            space. All modalities fuse through 8 learned tissue-state queries.
          </p>

          {/* Modality cards */}
          <div className="mt-16 grid gap-px sm:grid-cols-2 lg:grid-cols-4 border border-[#1a1a1a]">
            {MODALITIES.map((mod) => (
              <div key={mod.label} className="bg-[#080808] p-8">
                <p className="font-mono text-[10px] tracking-[0.2em] text-[#444] mb-4">{mod.label}</p>
                <p className="text-[14px] leading-[1.7] text-[#888]">{mod.desc}</p>
                <p className="font-mono text-[12px] text-white/30 mt-4">{mod.dim}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Architecture Diagram ── */}
      <section className="border-t border-[#1a1a1a]">
        <div className="mx-auto max-w-[1400px] px-6 sm:px-12 lg:px-24 py-24 lg:py-32">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold leading-[1.1] tracking-[-0.01em] max-w-3xl">
            Eight Cross-Attention Queries.<br />
            <span className="text-[#555]">One Tissue State.</span>
          </h2>
          <p className="mt-8 max-w-xl text-[15px] leading-[1.8] text-[#777]">
            The fused tissue state lives on a VICReg-regularized manifold in
            R&#8309;&#185;&#178; with contrastive subtype separation. Six
            prediction heads decode clinical and molecular outputs.
          </p>

          <div className="mt-12">
            <ArchitectureDiagram />
          </div>

          {/* Stats row */}
          <div className="mt-16 grid gap-px sm:grid-cols-3 border border-[#1a1a1a]">
            {[
              { value: '30min', sub: 'DEPLOY TIME', desc: 'Docker pull to inference-ready' },
              { value: '1×', sub: 'RTX 3090/4090', desc: 'Consumer GPU training with pre-extracted features' },
              { value: '6', sub: 'PREDICTION HEADS', desc: 'Subtype · drift · stage · survival · morph2mol · microenv' },
            ].map((stat) => (
              <div key={stat.sub} className="bg-[#080808] p-8 text-center">
                <p className="text-3xl sm:text-4xl font-bold">{stat.value}</p>
                <p className="font-mono text-[10px] tracking-[0.2em] text-[#444] mt-2">{stat.sub}</p>
                <p className="text-[13px] text-[#666] mt-3">{stat.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 03 · BENCHMARK ── */}
      <section id="benchmark" className="border-t border-[#1a1a1a]">
        <div className="mx-auto max-w-[1400px] px-6 sm:px-12 lg:px-24 py-24 lg:py-32">
          <p className="section-label mb-6">03 &middot; BENCHMARK</p>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold leading-[1.1] tracking-[-0.01em] max-w-3xl">
            Six-Track Public<br />
            <span className="text-[#555]">Leaderboard.</span>
          </h2>
          <p className="mt-8 max-w-xl text-[15px] leading-[1.8] text-[#777]">
            Submit predictions via PR. CI evaluates automatically. Results post
            to the public leaderboard. Compete, collaborate, push the field.
          </p>

          {/* Track cards */}
          <div className="mt-12 space-y-px border border-[#1a1a1a]">
            {TRACKS.map((track) => (
              <div key={track.name} className="bg-[#080808] px-8 py-6 flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-8">
                <div className="sm:w-48 shrink-0">
                  <p className="font-mono text-[13px] font-medium text-white">{track.name}</p>
                </div>
                <p className="flex-1 text-[14px] text-[#777]">{track.task}</p>
                <div className="flex items-center gap-4 shrink-0">
                  <span className="font-mono text-[12px] text-[#555]">{track.metric} &ge; {track.target}</span>
                  <StatusBadge status={track.status} />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-8">
            <Link
              href="/leaderboard"
              className="font-mono text-[11px] tracking-[0.15em] border border-white/20 text-white/70 px-6 py-3 hover:border-white/40 hover:text-white transition-colors inline-block"
            >
              VIEW FULL LEADERBOARD &rarr;
            </Link>
          </div>
        </div>
      </section>

      {/* ── 04 · ROADMAP ── */}
      <section id="roadmap" className="border-t border-[#1a1a1a]">
        <div className="mx-auto max-w-[1400px] px-6 sm:px-12 lg:px-24 py-24 lg:py-32">
          <p className="section-label mb-6">04 &middot; ROADMAP</p>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold leading-[1.1] tracking-[-0.01em] max-w-3xl">
            Development<br />
            Roadmap.
          </h2>
          <p className="mt-8 max-w-xl text-[15px] leading-[1.8] text-[#777]">
            Core model and molecular encoders are validated. Temporal dynamics
            and spatial modules are in active development.
          </p>

          <div className="mt-12 space-y-px border border-[#1a1a1a]">
            {ROADMAP.map((phase) => (
              <div key={phase.phase} className="bg-[#080808] p-8">
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                  <div className="max-w-2xl">
                    <p className="font-mono text-[10px] tracking-[0.2em] text-[#444] mb-3">{phase.phase}</p>
                    <h3 className="text-xl font-semibold mb-3">{phase.title}</h3>
                    <p className="text-[14px] leading-[1.7] text-[#777]">{phase.desc}</p>
                  </div>
                  <div className="shrink-0">
                    <StatusBadge status={phase.status} label={phase.badge} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Closing statement ── */}
      <section className="border-t border-[#1a1a1a]">
        <div className="mx-auto max-w-[1400px] px-6 sm:px-12 lg:px-24 py-24 lg:py-32">
          <p className="text-xl sm:text-2xl lg:text-3xl font-medium leading-[1.5] text-[#555] max-w-3xl">
            The constraint isn&apos;t data or compute.<br />
            It&apos;s how long we keep treating a tumor&apos;s<br />
            subtype as fixed when the biology says<br />
            <span className="text-white">it&apos;s already changing.</span>
          </p>
        </div>
      </section>

      {/* ── 05 · CONTACT ── */}
      <section id="contact" className="border-t border-[#1a1a1a]">
        <div className="mx-auto max-w-[1400px] px-6 sm:px-12 lg:px-24 py-24 lg:py-32">
          <p className="section-label mb-6">05 &middot; CONTACT</p>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold leading-[1.1] tracking-[-0.01em] max-w-3xl">
            Get in Touch.
          </h2>
          <p className="mt-8 max-w-xl text-[15px] leading-[1.8] text-[#777]">
            For research collaborations, dataset contributions, benchmark
            submissions, and deployment partnerships.
          </p>
          <div className="mt-10 flex flex-wrap gap-4">
            <Link
              href="/contribute"
              className="font-mono text-[11px] tracking-[0.15em] bg-white text-black px-6 py-3 hover:bg-white/90 transition-colors"
            >
              CONTRIBUTE &rarr;
            </Link>
            <a
              href="https://github.com/tissueshift/tissueshift"
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-[11px] tracking-[0.15em] border border-white/20 text-white/70 px-6 py-3 hover:border-white/40 hover:text-white transition-colors"
            >
              GITHUB
            </a>
            <Link
              href="/dashboard"
              className="font-mono text-[11px] tracking-[0.15em] border border-white/20 text-white/70 px-6 py-3 hover:border-white/40 hover:text-white transition-colors"
            >
              COMMUNITY DASHBOARD
            </Link>
          </div>

          {/* ASCII-style logo */}
          <div className="mt-20">
            <pre className="font-mono text-[10px] sm:text-[12px] leading-[1.4] text-[#333] select-none">
{`    ████████╗██╗███████╗███████╗██╗   ██╗███████╗
    ╚══██╔══╝██║██╔════╝██╔════╝██║   ██║██╔════╝
       ██║   ██║███████╗███████╗██║   ██║█████╗  
       ██║   ██║╚════██║╚════██║██║   ██║██╔══╝  
       ██║   ██║███████║███████║╚██████╔╝███████╗
       ╚═╝   ╚═╝╚══════╝╚══════╝ ╚═════╝ ╚══════╝
    ███████╗██╗  ██╗██╗███████╗████████╗
    ██╔════╝██║  ██║██║██╔════╝╚══██╔══╝
    ███████╗███████║██║█████╗     ██║   
    ╚════██║██╔══██║██║██╔══╝     ██║   
    ███████║██║  ██║██║██║        ██║   
    ╚══════╝╚═╝  ╚═╝╚═╝╚═╝        ╚═╝`}
            </pre>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="border-t border-[#1a1a1a]">
        <div className="mx-auto max-w-[1400px] px-6 sm:px-12 lg:px-24 py-8">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <p className="font-mono text-[11px] tracking-[0.1em] text-[#333]">
              TISSUESHIFT
            </p>
            <p className="font-mono text-[11px] tracking-[0.1em] text-[#333]">
              OPEN SOURCE &middot; APACHE 2.0 &middot; &copy; 2026
            </p>
          </div>
        </div>
      </footer>

    </div>
  );
}
