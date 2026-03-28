/**
 * Live pulse ring indicator — shows a system is alive and active.
 * Used on status dots, real-time feeds, and live data indicators.
 */
export default function PulseRing({ color = 'emerald', size = 'md', label = '' }) {
  const sizeMap = { sm: 'h-2 w-2', md: 'h-3 w-3', lg: 'h-4 w-4' };
  const ringSize = { sm: 'h-2 w-2', md: 'h-3 w-3', lg: 'h-4 w-4' };
  const colorMap = {
    emerald: 'bg-emerald-500',
    rose: 'bg-rose-500',
    amber: 'bg-amber-500',
    violet: 'bg-violet-500',
    sky: 'bg-sky-500',
    gray: 'bg-gray-400',
  };

  return (
    <span className="inline-flex items-center gap-2">
      <span className="relative flex">
        <span className={`animate-ping absolute inline-flex rounded-full opacity-40 ${ringSize[size]} ${colorMap[color]}`} />
        <span className={`relative inline-flex rounded-full ${sizeMap[size]} ${colorMap[color]}`} />
      </span>
      {label && <span className="text-xs font-medium text-gray-600 dark:text-gray-300">{label}</span>}
    </span>
  );
}
