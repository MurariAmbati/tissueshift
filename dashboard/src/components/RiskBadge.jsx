import { classNames, riskColor } from '../utils/Utils';

const sizeClasses = {
  sm: 'text-xs px-2 py-0.5',
  md: 'text-sm px-2.5 py-1',
  lg: 'text-base px-3 py-1.5',
};

const colorMap = {
  low: 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400',
  moderate: 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400',
  high: 'bg-rose-100 dark:bg-rose-500/20 text-rose-700 dark:text-rose-400',
  unknown: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300',
};

export default function RiskBadge({ level, size = 'md', className = '' }) {
  const resolvedLevel = level || 'unknown';
  return (
    <span className={classNames(
      'inline-flex items-center font-semibold rounded-full whitespace-nowrap',
      sizeClasses[size] || sizeClasses.md,
      colorMap[resolvedLevel] || colorMap.unknown,
      className,
    )}>
      {resolvedLevel === 'high' && (
        <svg className="shrink-0 mr-1 fill-current" width="10" height="10" viewBox="0 0 16 16">
          <path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0Zm.93 12.588h-1.9V10.7h1.9v1.888Zm-.09-3.166H7.12l-.27-5.072h2.26l-.27 5.072Z" />
        </svg>
      )}
      {resolvedLevel.charAt(0).toUpperCase() + resolvedLevel.slice(1)} Risk
    </span>
  );
}
