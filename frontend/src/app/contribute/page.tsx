'use client';

export default function ContributePage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="mb-2 text-3xl font-bold">Contribute</h1>
      <p className="mb-8 text-[var(--text-secondary)]">
        TissueShift is an open collaborative project. There are many ways to
        contribute.
      </p>

      <div className="grid gap-6 sm:grid-cols-2">
        <ContributionCard
          emoji="🏆"
          title="Submit to Leaderboard"
          description="Run your model on any of the 6 benchmark tracks and submit predictions via PR."
          link="/leaderboard"
        />
        <ContributionCard
          emoji="📊"
          title="Add a Dataset"
          description="Integrate a new histopathology cohort (METABRIC, AURORA, etc.) following our data card template."
          link="https://github.com/tissueshift/tissueshift/blob/main/CONTRIBUTING.md#datasets"
        />
        <ContributionCard
          emoji="🧠"
          title="Build an Encoder"
          description="Add a new pathology encoder (CONCH, Virchow, etc.) or molecular encoder variant."
          link="https://github.com/tissueshift/tissueshift/blob/main/CONTRIBUTING.md#encoders"
        />
        <ContributionCard
          emoji="📐"
          title="Add a Prediction Head"
          description="Create a new prediction head for an existing or novel benchmark track."
          link="https://github.com/tissueshift/tissueshift/blob/main/CONTRIBUTING.md#heads"
        />
        <ContributionCard
          emoji="📏"
          title="Propose New Metrics"
          description="Add evaluation metrics or propose entirely new benchmark tracks."
          link="https://github.com/tissueshift/tissueshift/blob/main/CONTRIBUTING.md#metrics"
        />
        <ContributionCard
          emoji="🎨"
          title="Improve the UI"
          description="Build new visualizations, improve existing ones, or fix frontend issues."
          link="https://github.com/tissueshift/tissueshift/blob/main/CONTRIBUTING.md#frontend"
        />
      </div>

      <div className="mt-12 glass-card p-6">
        <h2 className="mb-4 text-xl font-bold">Contributor Recognition</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="text-center">
            <div className="text-3xl">🥇</div>
            <div className="mt-1 font-medium">Gold</div>
            <p className="text-xs text-[var(--text-secondary)]">
              3+ merged PRs
            </p>
          </div>
          <div className="text-center">
            <div className="text-3xl">🥈</div>
            <div className="mt-1 font-medium">Silver</div>
            <p className="text-xs text-[var(--text-secondary)]">
              1-2 merged PRs
            </p>
          </div>
          <div className="text-center">
            <div className="text-3xl">🥉</div>
            <div className="mt-1 font-medium">Bronze</div>
            <p className="text-xs text-[var(--text-secondary)]">
              Issues, reviews, docs
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function ContributionCard({
  emoji,
  title,
  description,
  link,
}: {
  emoji: string;
  title: string;
  description: string;
  link: string;
}) {
  return (
    <a
      href={link}
      className="glass-card block p-6 transition-colors hover:bg-white/10"
    >
      <div className="mb-2 text-2xl">{emoji}</div>
      <h3 className="mb-1 font-semibold">{title}</h3>
      <p className="text-sm text-[var(--text-secondary)]">{description}</p>
    </a>
  );
}
