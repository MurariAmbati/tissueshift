'use client';

import { useState, useMemo } from 'react';

interface LeaderboardEntry {
  rank: number;
  team: string;
  model: string;
  score: number;
  date: string;
  track: string;
}

const TRACKS = [
  'SubtypeCall',
  'SubtypeDrift',
  'ProgressionStage',
  'Morph2Mol',
  'Survival',
  'SpatialPhenotype',
];

const TRACK_METRICS: Record<string, string> = {
  SubtypeCall: 'Macro-F1',
  SubtypeDrift: 'AUROC',
  ProgressionStage: 'QWK',
  Morph2Mol: 'R²',
  Survival: 'C-index',
  SpatialPhenotype: 'R²-TIL',
};

const DEMO_ENTRIES: LeaderboardEntry[] = [
  { rank: 1, team: 'TissueShift-Base', model: 'UNI+ABMIL+CrossAttn', score: 0.891, date: '2024-01-15', track: 'SubtypeCall' },
  { rank: 2, team: 'Baseline-MIL', model: 'ResNet50+CLAM', score: 0.842, date: '2024-01-10', track: 'SubtypeCall' },
  { rank: 3, team: 'Baseline-Linear', model: 'UNI+MeanPool+LR', score: 0.781, date: '2024-01-08', track: 'SubtypeCall' },
  { rank: 1, team: 'TissueShift-Base', model: 'UNI+ABMIL+CrossAttn', score: 0.712, date: '2024-01-15', track: 'Survival' },
  { rank: 2, team: 'Baseline-Cox', model: 'Clinical+CoxPH', score: 0.654, date: '2024-01-10', track: 'Survival' },
  { rank: 1, team: 'TissueShift-Base', model: 'UNI+ABMIL+CrossAttn', score: 0.423, date: '2024-01-15', track: 'Morph2Mol' },
  { rank: 1, team: 'TissueShift-Base', model: 'UNI+ABMIL+CrossAttn', score: 0.783, date: '2024-01-15', track: 'ProgressionStage' },
  { rank: 1, team: 'TissueShift-Base', model: 'UNI+ABMIL+CrossAttn', score: 0.821, date: '2024-01-15', track: 'SubtypeDrift' },
  { rank: 1, team: 'TissueShift-Base', model: 'UNI+ABMIL+CrossAttn', score: 0.387, date: '2024-01-15', track: 'SpatialPhenotype' },
];

export default function LeaderboardPage() {
  const [activeTrack, setActiveTrack] = useState('SubtypeCall');

  const filteredEntries = useMemo(
    () =>
      DEMO_ENTRIES.filter((e) => e.track === activeTrack).sort(
        (a, b) => a.rank - b.rank
      ),
    [activeTrack]
  );

  return (
    <div className="mx-auto max-w-[1400px] px-6 sm:px-12 lg:px-24 py-16 lg:py-24">
      <p className="section-label mb-6">BENCHMARK</p>
      <h1 className="text-3xl sm:text-4xl font-bold leading-[1.1] tracking-[-0.01em] mb-3">
        Leaderboard
      </h1>
      <p className="mb-10 text-[15px] text-[#777] max-w-xl">
        Compete across 6 benchmark tracks. Submit predictions via PR to{' '}
        <code className="font-mono text-[12px] text-[#555]">submissions/</code>.
      </p>

      {/* Track selector */}
      <div className="mb-8 flex flex-wrap gap-2">
        {TRACKS.map((track) => (
          <button
            key={track}
            onClick={() => setActiveTrack(track)}
            className={`font-mono text-[11px] tracking-[0.1em] px-4 py-2 border transition-colors ${
              activeTrack === track
                ? 'border-white/40 text-white bg-white/[0.04]'
                : 'border-[#1a1a1a] text-[#555] hover:border-white/20 hover:text-white/70'
            }`}
          >
            {track}
          </button>
        ))}
      </div>

      {/* Track info */}
      <div className="mb-6 border border-[#1a1a1a] bg-[#080808] p-6 flex items-center justify-between">
        <div>
          <h2 className="font-mono text-[13px] font-medium">{activeTrack}</h2>
          <p className="text-[13px] text-[#555] mt-1">
            Primary metric: {TRACK_METRICS[activeTrack]}
          </p>
        </div>
        <span className="badge badge-active">ACCEPTING SUBMISSIONS</span>
      </div>

      {/* Table */}
      <div className="border border-[#1a1a1a] overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[#1a1a1a] text-left font-mono text-[10px] tracking-[0.15em] text-[#444]">
              <th className="px-6 py-4">RANK</th>
              <th className="px-6 py-4">TEAM</th>
              <th className="px-6 py-4">MODEL</th>
              <th className="px-6 py-4 text-right">{TRACK_METRICS[activeTrack]}</th>
              <th className="px-6 py-4 text-right">DATE</th>
            </tr>
          </thead>
          <tbody>
            {filteredEntries.map((entry) => (
              <tr
                key={`${entry.track}-${entry.rank}`}
                className="border-b border-[#111] hover:bg-white/[0.02] transition-colors"
              >
                <td className="px-6 py-4 font-mono text-[13px] text-[#555]">
                  {String(entry.rank).padStart(2, '0')}
                </td>
                <td className="px-6 py-4 text-[14px] font-medium">{entry.team}</td>
                <td className="px-6 py-4 text-[13px] text-[#666]">{entry.model}</td>
                <td className="px-6 py-4 text-right font-mono text-[14px] text-white">
                  {entry.score.toFixed(3)}
                </td>
                <td className="px-6 py-4 text-right font-mono text-[12px] text-[#444]">
                  {entry.date}
                </td>
              </tr>
            ))}
            {filteredEntries.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-[14px] text-[#555]">
                  No submissions yet for this track.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Submission guide */}
      <div className="mt-10 border border-[#1a1a1a] bg-[#080808] p-8">
        <h3 className="font-mono text-[11px] tracking-[0.15em] text-[#444] mb-4">HOW TO SUBMIT</h3>
        <ol className="list-decimal list-inside space-y-3 text-[14px] text-[#777]">
          <li>Fork the TissueShift repository</li>
          <li>
            Run your model on the test split and save predictions as{' '}
            <code className="font-mono text-[12px] text-[#555]">
              submissions/&lt;track&gt;/&lt;team_name&gt;.json
            </code>
          </li>
          <li>Open a PR — CI will automatically evaluate and post results</li>
          <li>Once verified, your entry appears on the leaderboard</li>
        </ol>
      </div>
    </div>
  );
}
