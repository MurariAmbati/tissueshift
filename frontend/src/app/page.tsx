'use client';

import Link from 'next/link';

const SUBTYPE_COLORS = {
  LumA: '#3b82f6',
  LumB: '#6366f1',
  Her2: '#ec4899',
  Basal: '#ef4444',
  Normal: '#10b981',
};

const TRACKS = [
  { name: 'SubtypeCall', metric: 'Macro-F1', target: '0.92', icon: '🎯' },
  { name: 'SubtypeDrift', metric: 'AUROC', target: '0.85', icon: '🔄' },
  { name: 'ProgressionStage', metric: 'QWK', target: '0.80', icon: '📈' },
  { name: 'Morph2Mol', metric: 'R²', target: '0.45', icon: '🧬' },
  { name: 'Survival', metric: 'C-index', target: '0.72', icon: '⏱️' },
  { name: 'SpatialPhenotype', metric: 'R²-TIL', target: '0.50', icon: '🗺️' },
];

export default function HomePage() {
  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section className="relative flex flex-col items-center justify-center px-4 py-24 text-center">
        <div className="absolute inset-0 bg-gradient-to-b from-purple-900/20 to-transparent" />
        <h1 className="relative z-10 text-5xl font-bold tracking-tight sm:text-6xl">
          Tissue
          <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            Shift
          </span>
        </h1>
        <p className="relative z-10 mt-4 max-w-2xl text-lg text-[var(--text-secondary)]">
          An open temporal histopathology-to-omics model for breast cancer
          subtype emergence and progression. Explore the tissue state manifold,
          predict molecular features from morphology, and track subtype transitions.
        </p>
        <div className="relative z-10 mt-8 flex gap-4">
          <Link
            href="/atlas"
            className="rounded-lg bg-[var(--accent-purple)] px-6 py-3 font-medium text-white transition-colors hover:bg-purple-500"
          >
            Explore Atlas
          </Link>
          <Link
            href="/leaderboard"
            className="rounded-lg border border-white/20 px-6 py-3 font-medium transition-colors hover:bg-white/10"
          >
            View Leaderboard
          </Link>
        </div>

        {/* Subtype dots animation */}
        <div className="relative z-10 mt-16 flex gap-8">
          {Object.entries(SUBTYPE_COLORS).map(([name, color]) => (
            <div key={name} className="flex flex-col items-center gap-2">
              <div
                className="h-4 w-4 rounded-full animate-pulse"
                style={{ backgroundColor: color }}
              />
              <span className="text-xs text-[var(--text-secondary)]">{name}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Leaderboard Tracks */}
      <section className="mx-auto max-w-5xl px-4 py-16">
        <h2 className="mb-8 text-center text-2xl font-bold">Benchmark Tracks</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {TRACKS.map((track) => (
            <div key={track.name} className="glass-card p-6">
              <div className="mb-2 text-2xl">{track.icon}</div>
              <h3 className="text-lg font-semibold">{track.name}</h3>
              <p className="mt-1 text-sm text-[var(--text-secondary)]">
                {track.metric} target: {track.target}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Architecture overview */}
      <section className="mx-auto max-w-4xl px-4 py-16">
        <h2 className="mb-8 text-center text-2xl font-bold">Architecture</h2>
        <div className="glass-card overflow-x-auto p-8 font-mono text-sm leading-relaxed text-[var(--text-secondary)]">
          <pre>{`
  WSI Patches ──▶ UNI ViT-L ──▶ Region Tokenizer ──▶ ABMIL ──▶ z_path (512d)
                                                                    │
  Expression ──▶ MLP Encoder ──────────────────────────▶ z_mol (256d)│
                                                                    │
  Spatial* ──▶ GNN Encoder ────────────────────────────▶ z_spat (128d)
                                                                    │
                      ┌─────────────────────────────────────────────┘
                      ▼
              Cross-Attention Fusion (8 queries)
                      │
                      ▼
              Tissue State z ∈ R^512
                      │
          ┌───────────┼───────────┐───────────┐
          ▼           ▼           ▼           ▼
      Subtype    Survival    Morph2Mol   Transition
      Head       Head        Head        Lattice
          `}</pre>
        </div>
      </section>
    </div>
  );
}
