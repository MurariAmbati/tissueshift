'use client';

import { useState } from 'react';

interface Contributor {
  username: string;
  prs_merged: number;
  submissions: number;
  badge: 'gold' | 'silver' | 'bronze';
  contributions: string[];
  joined: string;
}

const DEMO_CONTRIBUTORS: Contributor[] = [
  {
    username: 'murariamarmath',
    prs_merged: 12,
    submissions: 6,
    badge: 'gold',
    contributions: ['core', 'encoders', 'training', 'frontend'],
    joined: '2024-01-01',
  },
  {
    username: 'contributor_a',
    prs_merged: 3,
    submissions: 2,
    badge: 'gold',
    contributions: ['baselines', 'metrics'],
    joined: '2024-02-01',
  },
  {
    username: 'contributor_b',
    prs_merged: 1,
    submissions: 1,
    badge: 'silver',
    contributions: ['datasets'],
    joined: '2024-03-01',
  },
];

const CHALLENGES = [
  { id: 1, title: 'Beat Baseline on SubtypeCall', desc: 'Submit a model that exceeds Macro-F1 > 0.85 on SubtypeCall track', difficulty: 'Medium', reward: 'Gold Badge' },
  { id: 2, title: 'Add METABRIC Dataset', desc: 'Integrate METABRIC cohort (2000+ samples) following the data card template', difficulty: 'Hard', reward: 'Dataset Pioneer' },
  { id: 3, title: 'Implement CONCH Encoder', desc: 'Add CONCH ViT as an alternative pathology encoder option', difficulty: 'Medium', reward: 'Encoder Builder' },
  { id: 4, title: 'WSI Viewer Component', desc: 'Build an OpenSeadragon-based WSI viewer with attention overlay', difficulty: 'Medium', reward: 'UI Champion' },
  { id: 5, title: 'Improve Survival C-index', desc: 'Submit a model that exceeds C-index > 0.70 on Survival track', difficulty: 'Hard', reward: 'Survival Expert' },
];

export default function ContributorDashboard() {
  const [activeTab, setActiveTab] = useState<'contributors' | 'challenges' | 'registry'>('contributors');

  return (
    <div className="mx-auto max-w-[1400px] px-6 sm:px-12 lg:px-24 py-16 lg:py-24">
      <p className="section-label mb-6">COMMUNITY</p>
      <h1 className="text-3xl sm:text-4xl font-bold leading-[1.1] tracking-[-0.01em] mb-3">
        Dashboard
      </h1>
      <p className="mb-10 text-[15px] text-[#777] max-w-xl">
        Track contributions, tackle challenges, and explore the model registry.
      </p>

      {/* Tabs */}
      <div className="mb-8 flex flex-wrap gap-2">
        {([
          { key: 'contributors' as const, label: 'CONTRIBUTORS' },
          { key: 'challenges' as const, label: 'CHALLENGES' },
          { key: 'registry' as const, label: 'MODEL REGISTRY' },
        ]).map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`font-mono text-[11px] tracking-[0.1em] px-4 py-2 border transition-colors ${
              activeTab === tab.key
                ? 'border-white/40 text-white bg-white/[0.04]'
                : 'border-[#1a1a1a] text-[#555] hover:border-white/20 hover:text-white/70'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Contributors */}
      {activeTab === 'contributors' && (
        <div className="space-y-6">
          <div className="grid gap-px sm:grid-cols-3 border border-[#1a1a1a]">
            {[
              { label: 'TOTAL CONTRIBUTORS', value: '3' },
              { label: 'PRS MERGED', value: '16' },
              { label: 'SUBMISSIONS', value: '9' },
            ].map((stat) => (
              <div key={stat.label} className="bg-[#080808] p-6 text-center">
                <p className="text-2xl font-bold">{stat.value}</p>
                <p className="font-mono text-[10px] tracking-[0.15em] text-[#444] mt-2">{stat.label}</p>
              </div>
            ))}
          </div>

          <div className="border border-[#1a1a1a] overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#1a1a1a] font-mono text-[10px] tracking-[0.15em] text-[#444] text-left">
                  <th className="px-6 py-4">CONTRIBUTOR</th>
                  <th className="px-6 py-4">TIER</th>
                  <th className="px-6 py-4 text-center">PRS</th>
                  <th className="px-6 py-4 text-center">SUBMISSIONS</th>
                  <th className="px-6 py-4">AREAS</th>
                  <th className="px-6 py-4">JOINED</th>
                </tr>
              </thead>
              <tbody>
                {DEMO_CONTRIBUTORS.map((c) => (
                  <tr key={c.username} className="border-b border-[#111] hover:bg-white/[0.02] transition-colors">
                    <td className="px-6 py-4 text-[14px] font-medium">{c.username}</td>
                    <td className="px-6 py-4">
                      <span className={`font-mono text-[11px] tracking-[0.1em] ${
                        c.badge === 'gold' ? 'text-amber-400' : c.badge === 'silver' ? 'text-[#999]' : 'text-amber-700'
                      }`}>
                        {c.badge.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-center text-[14px] text-[#777]">{c.prs_merged}</td>
                    <td className="px-6 py-4 text-center text-[14px] text-[#777]">{c.submissions}</td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-1.5">
                        {c.contributions.map((area) => (
                          <span key={area} className="font-mono text-[10px] tracking-[0.1em] text-[#555] border border-[#222] px-2 py-0.5">
                            {area}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-6 py-4 font-mono text-[12px] text-[#444]">{c.joined}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Challenges */}
      {activeTab === 'challenges' && (
        <div className="space-y-px border border-[#1a1a1a]">
          {CHALLENGES.map((challenge) => (
            <div key={challenge.id} className="bg-[#080808] p-8">
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                <div className="max-w-2xl">
                  <h3 className="text-[16px] font-semibold mb-2">{challenge.title}</h3>
                  <p className="text-[14px] leading-[1.7] text-[#666]">{challenge.desc}</p>
                  <div className="mt-4 flex gap-3">
                    <span className="badge badge-dev">{challenge.difficulty}</span>
                    <span className="font-mono text-[11px] text-[#555]">{challenge.reward}</span>
                  </div>
                </div>
                <span className="badge badge-active shrink-0">OPEN</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Model Registry */}
      {activeTab === 'registry' && (
        <div className="space-y-6">
          <div className="border border-[#1a1a1a] bg-[#080808] p-8">
            <div className="flex items-start justify-between mb-6">
              <div>
                <h3 className="text-[16px] font-semibold">TissueShift-Base v0.1.0</h3>
                <p className="font-mono text-[11px] text-[#444] mt-1">BASELINE MODEL</p>
              </div>
              <span className="badge badge-active">LATEST</span>
            </div>
            <div className="grid gap-8 sm:grid-cols-2 text-[14px] text-[#666]">
              <div className="space-y-1.5">
                <p>Pathology: UNI ViT-L/16 + LoRA + ABMIL</p>
                <p>Molecular: MLP (expr + pathway + prot)</p>
                <p>Fusion: 8-query cross-attention</p>
                <p>Parameters: ~15M trainable</p>
              </div>
              <div className="space-y-1.5">
                <p>Training: TCGA-BRCA (1098 subjects)</p>
                <p>Validation: CPTAC-BRCA (198 subjects)</p>
                <p>Stage: 2-stage (pretrain → finetune)</p>
                <p>GPU: Single RTX 3090</p>
              </div>
            </div>
            <div className="mt-6 flex gap-3">
              <button className="font-mono text-[11px] tracking-[0.1em] bg-white text-black px-5 py-2.5 hover:bg-white/90 transition-colors">
                DOWNLOAD CHECKPOINT
              </button>
              <button className="font-mono text-[11px] tracking-[0.1em] border border-white/20 text-white/70 px-5 py-2.5 hover:border-white/40 hover:text-white transition-colors">
                VIEW MODEL CARD
              </button>
            </div>
          </div>

          <div className="border border-[#1a1a1a] bg-[#080808] flex h-32 items-center justify-center">
            <p className="text-[14px] text-[#444]">Community models will appear here as they are submitted</p>
          </div>
        </div>
      )}
    </div>
  );
}
