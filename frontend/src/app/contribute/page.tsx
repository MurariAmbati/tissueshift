'use client';

const CONTRIBUTIONS = [
  { label: 'LEADERBOARD', title: 'Submit to Benchmark', desc: 'Run your model on any of the 6 tracks and submit predictions via PR.', link: '/leaderboard' },
  { label: 'DATASETS', title: 'Add a Dataset', desc: 'Integrate a new histopathology cohort (METABRIC, AURORA, etc.) following our data card template.', link: 'https://github.com/MurariAmbati/tissueshift' },
  { label: 'ENCODERS', title: 'Build an Encoder', desc: 'Add a new pathology encoder (CONCH, Virchow, etc.) or molecular encoder variant.', link: 'https://github.com/MurariAmbati/tissueshift' },
  { label: 'HEADS', title: 'Add a Prediction Head', desc: 'Create a new prediction head for an existing or novel benchmark track.', link: 'https://github.com/MurariAmbati/tissueshift' },
  { label: 'METRICS', title: 'Propose New Metrics', desc: 'Add evaluation metrics or propose entirely new benchmark tracks.', link: 'https://github.com/MurariAmbati/tissueshift' },
  { label: 'FRONTEND', title: 'Improve the UI', desc: 'Build new visualizations, improve existing ones, or fix frontend issues.', link: 'https://github.com/MurariAmbati/tissueshift' },
];

const TIERS = [
  { tier: 'GOLD', requirement: '3+ merged PRs', color: 'text-amber-400' },
  { tier: 'SILVER', requirement: '1–2 merged PRs', color: 'text-[#999]' },
  { tier: 'BRONZE', requirement: 'Issues, reviews, docs', color: 'text-amber-700' },
];

export default function ContributePage() {
  return (
    <div className="mx-auto max-w-[1400px] px-6 sm:px-12 lg:px-24 py-16 lg:py-24">
      <p className="section-label mb-6">CONTRIBUTE</p>
      <h1 className="text-3xl sm:text-4xl font-bold leading-[1.1] tracking-[-0.01em] mb-3">
        Get Involved.
      </h1>
      <p className="mb-12 text-[15px] text-[#777] max-w-xl">
        Tissue Shift is an open collaborative project. There are many ways
        to contribute — from submitting to the benchmark to building new
        encoder backbones.
      </p>

      <div className="grid gap-px sm:grid-cols-2 lg:grid-cols-3 border border-[#1a1a1a]">
        {CONTRIBUTIONS.map((item) => (
          <a
            key={item.label}
            href={item.link}
            className="bg-[#080808] p-8 transition-colors hover:bg-[#0f0f0f] group"
          >
            <p className="font-mono text-[10px] tracking-[0.2em] text-[#444] mb-4">{item.label}</p>
            <h3 className="text-[16px] font-semibold mb-3 group-hover:text-white transition-colors">{item.title}</h3>
            <p className="text-[14px] leading-[1.7] text-[#666]">{item.desc}</p>
          </a>
        ))}
      </div>

      <div className="mt-16 border border-[#1a1a1a] bg-[#080808] p-8">
        <p className="font-mono text-[10px] tracking-[0.2em] text-[#444] mb-6">CONTRIBUTOR RECOGNITION</p>
        <div className="grid gap-px sm:grid-cols-3">
          {TIERS.map((t) => (
            <div key={t.tier} className="text-center py-4">
              <p className={`font-mono text-[14px] font-semibold ${t.color}`}>{t.tier}</p>
              <p className="text-[13px] text-[#555] mt-2">{t.requirement}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
