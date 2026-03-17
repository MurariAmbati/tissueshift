'use client';

import { useState, useMemo } from 'react';

interface Contributor {
  username: string;
  avatar: string;
  prs_merged: number;
  submissions: number;
  badge: 'gold' | 'silver' | 'bronze';
  contributions: string[];
  joined: string;
}

const DEMO_CONTRIBUTORS: Contributor[] = [
  {
    username: 'murariamarmath',
    avatar: 'https://github.com/murariamarmath.png',
    prs_merged: 12,
    submissions: 6,
    badge: 'gold',
    contributions: ['core', 'encoders', 'training', 'frontend'],
    joined: '2024-01-01',
  },
  {
    username: 'contributor_a',
    avatar: '',
    prs_merged: 3,
    submissions: 2,
    badge: 'gold',
    contributions: ['baselines', 'metrics'],
    joined: '2024-02-01',
  },
  {
    username: 'contributor_b',
    avatar: '',
    prs_merged: 1,
    submissions: 1,
    badge: 'silver',
    contributions: ['datasets'],
    joined: '2024-03-01',
  },
];

const CHALLENGES = [
  {
    id: 1,
    title: 'Beat Baseline on SubtypeCall',
    description: 'Submit a model that exceeds Macro-F1 > 0.85 on SubtypeCall track',
    difficulty: 'Medium',
    reward: '🥇 Gold Badge',
    status: 'open',
  },
  {
    id: 2,
    title: 'Add METABRIC Dataset',
    description: 'Integrate METABRIC cohort (2000+ samples) following the data card template',
    difficulty: 'Hard',
    reward: '🌟 Dataset Pioneer',
    status: 'open',
  },
  {
    id: 3,
    title: 'Implement CONCH Encoder',
    description: 'Add CONCH ViT as an alternative pathology encoder option',
    difficulty: 'Medium',
    reward: '🧠 Encoder Builder',
    status: 'open',
  },
  {
    id: 4,
    title: 'WSI Viewer Component',
    description: 'Build an OpenSeadragon-based WSI viewer with attention overlay',
    difficulty: 'Medium',
    reward: '🎨 UI Champion',
    status: 'open',
  },
  {
    id: 5,
    title: 'Improve Survival C-index',
    description: 'Submit a model that exceeds C-index > 0.70 on Survival track',
    difficulty: 'Hard',
    reward: '🥇 Gold Badge + ⏱️ Survival Expert',
    status: 'open',
  },
];

function getBadgeEmoji(badge: string): string {
  switch (badge) {
    case 'gold':
      return '🥇';
    case 'silver':
      return '🥈';
    case 'bronze':
      return '🥉';
    default:
      return '';
  }
}

export default function ContributorDashboard() {
  const [activeTab, setActiveTab] = useState<
    'contributors' | 'challenges' | 'registry'
  >('contributors');

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="mb-2 text-3xl font-bold">Community Dashboard</h1>
      <p className="mb-8 text-[var(--text-secondary)]">
        Track contributions, tackle challenges, and explore the model registry.
      </p>

      {/* Tabs */}
      <div className="mb-6 flex gap-2">
        {[
          { key: 'contributors' as const, label: 'Contributors' },
          { key: 'challenges' as const, label: 'Challenge Board' },
          { key: 'registry' as const, label: 'Model Registry' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? 'bg-[var(--accent-purple)] text-white'
                : 'bg-white/5 text-[var(--text-secondary)] hover:bg-white/10'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Contributors */}
      {activeTab === 'contributors' && (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard label="Total Contributors" value="3" />
            <StatCard label="PRs Merged" value="16" />
            <StatCard label="Leaderboard Submissions" value="9" />
          </div>

          <div className="glass-card overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10 text-left text-sm text-[var(--text-secondary)]">
                  <th className="px-4 py-3">Contributor</th>
                  <th className="px-4 py-3">Badge</th>
                  <th className="px-4 py-3 text-center">PRs</th>
                  <th className="px-4 py-3 text-center">Submissions</th>
                  <th className="px-4 py-3">Areas</th>
                  <th className="px-4 py-3">Joined</th>
                </tr>
              </thead>
              <tbody>
                {DEMO_CONTRIBUTORS.map((c) => (
                  <tr
                    key={c.username}
                    className="border-b border-white/5 hover:bg-white/5"
                  >
                    <td className="px-4 py-3 font-medium">{c.username}</td>
                    <td className="px-4 py-3 text-lg">
                      {getBadgeEmoji(c.badge)}
                    </td>
                    <td className="px-4 py-3 text-center">{c.prs_merged}</td>
                    <td className="px-4 py-3 text-center">{c.submissions}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {c.contributions.map((area) => (
                          <span
                            key={area}
                            className="rounded-full bg-white/10 px-2 py-0.5 text-xs"
                          >
                            {area}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-[var(--text-secondary)]">
                      {c.joined}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Challenges */}
      {activeTab === 'challenges' && (
        <div className="space-y-4">
          {CHALLENGES.map((challenge) => (
            <div key={challenge.id} className="glass-card p-6">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-semibold">{challenge.title}</h3>
                  <p className="mt-1 text-sm text-[var(--text-secondary)]">
                    {challenge.description}
                  </p>
                  <div className="mt-3 flex gap-3">
                    <span className="rounded-full bg-yellow-500/20 px-2 py-0.5 text-xs text-yellow-400">
                      {challenge.difficulty}
                    </span>
                    <span className="text-sm">{challenge.reward}</span>
                  </div>
                </div>
                <span className="rounded-full bg-green-500/20 px-3 py-1 text-xs text-green-400">
                  {challenge.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Model Registry */}
      {activeTab === 'registry' && (
        <div className="space-y-4">
          <div className="glass-card p-6">
            <h3 className="mb-2 font-semibold">TissueShift-Base v0.1.0</h3>
            <div className="grid gap-4 text-sm text-[var(--text-secondary)] sm:grid-cols-2">
              <div>
                <p>Pathology: UNI ViT-L/16 + LoRA + ABMIL</p>
                <p>Molecular: MLP (expr + pathway + prot)</p>
                <p>Fusion: 8-query cross-attention</p>
                <p>Parameters: ~15M trainable</p>
              </div>
              <div>
                <p>Training: TCGA-BRCA (1098 subjects)</p>
                <p>Validation: CPTAC-BRCA (198 subjects)</p>
                <p>Stage: 2-stage (pretrain → finetune)</p>
                <p>GPU: Single RTX 3090</p>
              </div>
            </div>
            <div className="mt-4 flex gap-2">
              <button className="rounded-lg bg-[var(--accent-blue)] px-4 py-2 text-sm text-white">
                Download Checkpoint
              </button>
              <button className="rounded-lg border border-white/20 px-4 py-2 text-sm">
                View Model Card
              </button>
            </div>
          </div>

          <div className="glass-card flex h-32 items-center justify-center text-[var(--text-secondary)]">
            <p>Community models will appear here as they are submitted</p>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="glass-card p-4 text-center">
      <div className="text-2xl font-bold text-[var(--accent-blue)]">{value}</div>
      <div className="mt-1 text-sm text-[var(--text-secondary)]">{label}</div>
    </div>
  );
}
