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

// Demo data
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

function getMedalEmoji(rank: number): string {
  if (rank === 1) return '🥇';
  if (rank === 2) return '🥈';
  if (rank === 3) return '🥉';
  return `${rank}`;
}

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
    <div className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="mb-2 text-3xl font-bold">Leaderboard</h1>
      <p className="mb-8 text-[var(--text-secondary)]">
        Compete across 6 benchmark tracks. Submit predictions via PR to{' '}
        <code className="rounded bg-white/10 px-1.5 py-0.5 text-xs">
          submissions/
        </code>
        .
      </p>

      {/* Track selector */}
      <div className="mb-6 flex flex-wrap gap-2">
        {TRACKS.map((track) => (
          <button
            key={track}
            onClick={() => setActiveTrack(track)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              activeTrack === track
                ? 'bg-[var(--accent-purple)] text-white'
                : 'bg-white/5 text-[var(--text-secondary)] hover:bg-white/10'
            }`}
          >
            {track}
          </button>
        ))}
      </div>

      {/* Track info */}
      <div className="mb-6 glass-card p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">{activeTrack}</h2>
            <p className="text-sm text-[var(--text-secondary)]">
              Primary metric: {TRACK_METRICS[activeTrack]}
            </p>
          </div>
          <button className="rounded-lg bg-[var(--accent-green)] px-4 py-2 text-sm font-medium text-white hover:bg-green-600 transition-colors">
            Submit Entry
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="glass-card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/10 text-left text-sm text-[var(--text-secondary)]">
              <th className="px-4 py-3">Rank</th>
              <th className="px-4 py-3">Team</th>
              <th className="px-4 py-3">Model</th>
              <th className="px-4 py-3 text-right">
                {TRACK_METRICS[activeTrack]}
              </th>
              <th className="px-4 py-3 text-right">Date</th>
            </tr>
          </thead>
          <tbody>
            {filteredEntries.map((entry) => (
              <tr
                key={`${entry.track}-${entry.rank}`}
                className="border-b border-white/5 hover:bg-white/5 transition-colors"
              >
                <td className="px-4 py-3 text-lg">
                  {getMedalEmoji(entry.rank)}
                </td>
                <td className="px-4 py-3 font-medium">{entry.team}</td>
                <td className="px-4 py-3 text-sm text-[var(--text-secondary)]">
                  {entry.model}
                </td>
                <td className="px-4 py-3 text-right font-mono text-[var(--accent-blue)]">
                  {entry.score.toFixed(3)}
                </td>
                <td className="px-4 py-3 text-right text-sm text-[var(--text-secondary)]">
                  {entry.date}
                </td>
              </tr>
            ))}
            {filteredEntries.length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  className="px-4 py-8 text-center text-[var(--text-secondary)]"
                >
                  No submissions yet for this track.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Submission guide */}
      <div className="mt-8 glass-card p-6">
        <h3 className="mb-3 text-lg font-semibold">How to Submit</h3>
        <ol className="list-inside list-decimal space-y-2 text-sm text-[var(--text-secondary)]">
          <li>Fork the TissueShift repository</li>
          <li>
            Run your model on the test split and save predictions as{' '}
            <code className="rounded bg-white/10 px-1 py-0.5 text-xs">
              submissions/&lt;track&gt;/&lt;team_name&gt;.json
            </code>
          </li>
          <li>Open a PR — our CI will automatically evaluate and post results</li>
          <li>
            Once verified, your entry appears on the leaderboard
          </li>
        </ol>
      </div>
    </div>
  );
}
