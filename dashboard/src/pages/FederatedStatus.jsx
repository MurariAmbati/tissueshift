import { useState } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import MetricCard from '../components/MetricCard';
import { classNames } from '../utils/Utils';

const sites = [
  { name: 'Memorial Sloan Kettering', location: 'New York, USA', patients: 1240, status: 'active', lastSync: '2 min ago', contribution: 0.34 },
  { name: 'MD Anderson', location: 'Houston, USA', patients: 980, status: 'active', lastSync: '5 min ago', contribution: 0.28 },
  { name: 'Institut Curie', location: 'Paris, France', patients: 640, status: 'active', lastSync: '12 min ago', contribution: 0.18 },
  { name: 'UCSF Medical Center', location: 'San Francisco, USA', patients: 420, status: 'syncing', lastSync: 'syncing...', contribution: 0.12 },
  { name: 'Charite Berlin', location: 'Berlin, Germany', patients: 310, status: 'offline', lastSync: '2 hrs ago', contribution: 0.08 },
];

const rounds = [
  { round: 42, sites: 4, privacy: 'ε=1.2, δ=1e-5', accuracy: 0.943, timestamp: '2024-01-15 14:22' },
  { round: 41, sites: 5, privacy: 'ε=1.2, δ=1e-5', accuracy: 0.941, timestamp: '2024-01-15 12:18' },
  { round: 40, sites: 4, privacy: 'ε=1.3, δ=1e-5', accuracy: 0.938, timestamp: '2024-01-15 10:05' },
  { round: 39, sites: 5, privacy: 'ε=1.3, δ=1e-5', accuracy: 0.937, timestamp: '2024-01-15 08:02' },
  { round: 38, sites: 4, privacy: 'ε=1.4, δ=1e-5', accuracy: 0.934, timestamp: '2024-01-14 22:15' },
];

const statusColors = { active: 'bg-emerald-500', syncing: 'bg-amber-500 animate-pulse', offline: 'bg-gray-400' };

export default function FederatedStatus() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
            <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold mb-2">Federated Learning</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-8">Privacy-preserving multi-site training with differential privacy guarantees</p>

            {/* KPIs */}
            <div className="grid grid-cols-12 gap-6 mb-6">
              <MetricCard className="col-span-12 sm:col-span-6 xl:col-span-3" title="Active Sites" value="4/5" subtitle="1 site offline" />
              <MetricCard className="col-span-12 sm:col-span-6 xl:col-span-3" title="Current Round" value="#42" subtitle="Aggregation complete" />
              <MetricCard className="col-span-12 sm:col-span-6 xl:col-span-3" title="Global Accuracy" value="94.3%" change="0.2%" changeDir="up" />
              <MetricCard className="col-span-12 sm:col-span-6 xl:col-span-3" title="Privacy Budget" value="ε = 1.2" subtitle="δ = 1e-5" />
            </div>

            {/* Sites */}
            <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 mb-6">
              <header className="px-5 py-4 border-b border-gray-100 dark:border-gray-700/60">
                <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Participating Sites</h2>
              </header>
              <div className="overflow-x-auto">
                <table className="table-auto w-full text-sm">
                  <thead className="text-xs uppercase text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-900/20">
                    <tr>
                      <th className="px-4 py-3 text-left">Site</th>
                      <th className="px-4 py-3 text-left">Location</th>
                      <th className="px-4 py-3 text-center">Patients</th>
                      <th className="px-4 py-3 text-center">Status</th>
                      <th className="px-4 py-3 text-center">Contribution</th>
                      <th className="px-4 py-3 text-right">Last Sync</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700/60 text-gray-700 dark:text-gray-300">
                    {sites.map((s) => (
                      <tr key={s.name}>
                        <td className="px-4 py-3 font-medium">{s.name}</td>
                        <td className="px-4 py-3 text-gray-500 dark:text-gray-400">{s.location}</td>
                        <td className="px-4 py-3 text-center">{s.patients.toLocaleString()}</td>
                        <td className="px-4 py-3 text-center">
                          <span className="inline-flex items-center gap-1.5">
                            <span className={classNames('w-2 h-2 rounded-full', statusColors[s.status])} />
                            <span className="capitalize">{s.status}</span>
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <div className="flex items-center justify-center gap-2">
                            <div className="w-16 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                              <div className="h-full bg-violet-500 rounded-full" style={{ width: `${s.contribution * 100}%` }} />
                            </div>
                            <span className="text-xs">{(s.contribution * 100).toFixed(0)}%</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right text-gray-500 dark:text-gray-400">{s.lastSync}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Training history */}
            <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60">
              <header className="px-5 py-4 border-b border-gray-100 dark:border-gray-700/60">
                <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Aggregation History</h2>
              </header>
              <div className="overflow-x-auto">
                <table className="table-auto w-full text-sm">
                  <thead className="text-xs uppercase text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-900/20">
                    <tr>
                      <th className="px-4 py-3 text-left">Round</th>
                      <th className="px-4 py-3 text-center">Sites</th>
                      <th className="px-4 py-3 text-center">DP Params</th>
                      <th className="px-4 py-3 text-center">Accuracy</th>
                      <th className="px-4 py-3 text-right">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700/60 text-gray-700 dark:text-gray-300">
                    {rounds.map((r) => (
                      <tr key={r.round}>
                        <td className="px-4 py-3 font-medium">#{r.round}</td>
                        <td className="px-4 py-3 text-center">{r.sites}</td>
                        <td className="px-4 py-3 text-center font-mono text-xs">{r.privacy}</td>
                        <td className="px-4 py-3 text-center font-medium">{(r.accuracy * 100).toFixed(1)}%</td>
                        <td className="px-4 py-3 text-right text-gray-500 dark:text-gray-400">{r.timestamp}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
