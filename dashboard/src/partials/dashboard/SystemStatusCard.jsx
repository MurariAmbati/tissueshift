import { classNames } from '../../utils/Utils';

const services = [
  { name: 'TissueShift API', status: 'operational', latency: '23ms' },
  { name: 'World Model (Neural ODE)', status: 'operational', latency: '142ms' },
  { name: 'Federated Hub', status: 'operational', latency: '89ms' },
  { name: 'Knowledge Graph DB', status: 'degraded', latency: '340ms' },
];

const statusColors = {
  operational: 'bg-emerald-500',
  degraded: 'bg-amber-500',
  down: 'bg-rose-500',
};

export default function SystemStatusCard({ className = '' }) {
  return (
    <div className={classNames('bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5', className)}>
      <header className="mb-3">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">System Status</h2>
      </header>
      <ul className="space-y-3">
        {services.map((s) => (
          <li key={s.name} className="flex items-center justify-between">
            <div className="flex items-center">
              <span className={classNames('w-2 h-2 rounded-full mr-2.5', statusColors[s.status])} />
              <span className="text-sm text-gray-700 dark:text-gray-300">{s.name}</span>
            </div>
            <span className="text-xs text-gray-400 dark:text-gray-500">{s.latency}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
