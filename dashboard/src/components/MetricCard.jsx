import { classNames } from '../utils/Utils';

const variants = {
  default: 'bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60',
  flat: 'bg-gray-50 dark:bg-gray-900/30 rounded-xl border border-gray-100 dark:border-gray-700/40',
};

export default function MetricCard({ title, value, change, changeDir = 'up', icon, variant = 'default', subtitle, children, className = '' }) {
  return (
    <div className={classNames(variants[variant] || variants.default, 'p-5', className)}>
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase mb-1">{title}</div>
          <div className="text-3xl font-bold text-gray-800 dark:text-gray-100">{value}</div>
          {subtitle && <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">{subtitle}</div>}
          {change !== undefined && (
            <div className="flex items-center mt-2">
              <svg
                className={classNames('shrink-0 mr-1.5', changeDir === 'up' ? 'fill-emerald-500' : 'fill-rose-500', changeDir === 'up' ? '' : 'rotate-180')}
                width="8" height="8" viewBox="0 0 8 8"
              >
                <path d="M4 0l4 6H0z" />
              </svg>
              <span className={classNames('text-sm font-medium', changeDir === 'up' ? 'text-emerald-600' : 'text-rose-600')}>{change}</span>
            </div>
          )}
        </div>
        {icon && (
          <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-violet-50 dark:bg-violet-500/10">
            {icon}
          </div>
        )}
      </div>
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}
