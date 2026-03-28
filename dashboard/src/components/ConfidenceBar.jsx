import { classNames, confidenceLevel } from '../utils/Utils';

export default function ConfidenceBar({ score, showLabel = true, height = 'h-2', className = '' }) {
  const { label, color } = confidenceLevel(score);
  const pct = Math.round(score * 100);

  const barColors = {
    emerald: 'bg-emerald-500',
    amber: 'bg-amber-500',
    rose: 'bg-rose-500',
    gray: 'bg-gray-400',
  };

  return (
    <div className={classNames('flex items-center gap-3', className)}>
      <div className={classNames('flex-1 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden', height)}>
        <div
          className={classNames('h-full rounded-full transition-all duration-500', barColors[color] || barColors.gray)}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-medium text-gray-600 dark:text-gray-300 whitespace-nowrap w-14 text-right">
          {pct}% {label}
        </span>
      )}
    </div>
  );
}
