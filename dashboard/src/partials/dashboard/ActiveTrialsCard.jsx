import { classNames } from '../../utils/Utils';

const trials = [
  { name: 'BRCA-AI-2024', phase: 'Phase II', enrolled: 342, target: 500, status: 'Recruiting' },
  { name: 'SUBTYPE-PRED', phase: 'Phase III', enrolled: 890, target: 1000, status: 'Active' },
];

export default function ActiveTrialsCard({ className = '' }) {
  return (
    <div className={classNames('bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5', className)}>
      <header className="mb-3">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Active Trials</h2>
      </header>
      <ul className="space-y-4">
        {trials.map((t) => (
          <li key={t.name}>
            <div className="flex justify-between items-center mb-1">
              <span className="text-sm font-medium text-gray-800 dark:text-gray-100">{t.name}</span>
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-violet-100 dark:bg-violet-500/20 text-violet-700 dark:text-violet-400">{t.status}</span>
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1.5">{t.phase} — {t.enrolled}/{t.target} enrolled</div>
            <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div className="h-full bg-violet-500 rounded-full" style={{ width: `${(t.enrolled / t.target * 100).toFixed(0)}%` }} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
