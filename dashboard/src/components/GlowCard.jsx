/**
 * Glassmorphism card with subtle glow, blur, and hover lift.
 * The visual signature of TissueShift — makes every panel feel premium.
 */
export default function GlowCard({
  children,
  className = '',
  glowColor = 'violet',
  hover = true,
  noPad = false,
}) {
  const glowMap = {
    violet: 'shadow-violet-500/10 hover:shadow-violet-500/25 border-violet-500/20',
    emerald: 'shadow-emerald-500/10 hover:shadow-emerald-500/25 border-emerald-500/20',
    rose: 'shadow-rose-500/10 hover:shadow-rose-500/25 border-rose-500/20',
    sky: 'shadow-sky-500/10 hover:shadow-sky-500/25 border-sky-500/20',
    amber: 'shadow-amber-500/10 hover:shadow-amber-500/25 border-amber-500/20',
    teal: 'shadow-teal-500/10 hover:shadow-teal-500/25 border-teal-500/20',
    indigo: 'shadow-indigo-500/10 hover:shadow-indigo-500/25 border-indigo-500/20',
    neutral: 'shadow-gray-500/5 hover:shadow-gray-500/10 border-gray-200 dark:border-gray-700/60',
  };

  return (
    <div
      className={[
        'relative rounded-2xl border backdrop-blur-sm',
        'bg-white/80 dark:bg-gray-800/80',
        'shadow-lg transition-all duration-300',
        hover ? 'hover:-translate-y-0.5 hover:shadow-xl' : '',
        glowMap[glowColor] || glowMap.violet,
        noPad ? '' : 'p-6',
        className,
      ].join(' ')}
    >
      {children}
    </div>
  );
}
