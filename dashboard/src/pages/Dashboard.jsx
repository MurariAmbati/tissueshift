import { useState } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import MetricCard from '../components/MetricCard';
import SubtypeDistributionCard from '../partials/dashboard/SubtypeDistributionCard';
import SurvivalCurveCard from '../partials/dashboard/SurvivalCurveCard';
import RecentPatientsCard from '../partials/dashboard/RecentPatientsCard';
import ModelPerformanceCard from '../partials/dashboard/ModelPerformanceCard';
import RiskStratificationCard from '../partials/dashboard/RiskStratificationCard';
import SystemStatusCard from '../partials/dashboard/SystemStatusCard';
import ActiveTrialsCard from '../partials/dashboard/ActiveTrialsCard';
import UncertaintyOverviewCard from '../partials/dashboard/UncertaintyOverviewCard';

export default function Dashboard() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
            {/* Page header */}
            <div className="sm:flex sm:justify-between sm:items-center mb-8">
              <div className="mb-4 sm:mb-0">
                <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold">Clinical Dashboard</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Real-time breast cancer subtype analytics and patient monitoring</p>
              </div>
              <div className="grid grid-flow-col sm:auto-cols-max justify-start sm:justify-end gap-2">
                <button className="btn bg-gray-900 text-gray-100 hover:bg-gray-800 dark:bg-gray-100 dark:text-gray-800 dark:hover:bg-white px-4 py-2 rounded-lg text-sm font-medium">
                  <svg className="fill-current shrink-0 xs:hidden mr-2" width="16" height="16" viewBox="0 0 16 16">
                    <path d="M15 7H9V1c0-.6-.4-1-1-1S7 .4 7 1v6H1c-.6 0-1 .4-1 1s.4 1 1 1h6v6c0 .6.4 1 1 1s1-.4 1-1V9h6c.6 0 1-.4 1-1s-.4-1-1-1z" />
                  </svg>
                  <span>New Patient</span>
                </button>
              </div>
            </div>

            {/* KPI row */}
            <div className="grid grid-cols-12 gap-6 mb-6">
              <MetricCard
                className="col-span-12 sm:col-span-6 xl:col-span-3"
                title="Total Patients"
                value="2,847"
                change="12.5%"
                changeDir="up"
                icon={<svg className="fill-current text-violet-500" width="24" height="24" viewBox="0 0 24 24"><path d="M12 2a5 5 0 015 5 5 5 0 01-5 5 5 5 0 01-5-5 5 5 0 015-5zm0 12c5.5 0 10 2.5 10 5v1a1 1 0 01-1 1H3a1 1 0 01-1-1v-1c0-2.5 4.5-5 10-5z"/></svg>}
              />
              <MetricCard
                className="col-span-12 sm:col-span-6 xl:col-span-3"
                title="Slides Analyzed"
                value="18,392"
                change="8.2%"
                changeDir="up"
                icon={<svg className="fill-current text-teal-500" width="24" height="24" viewBox="0 0 24 24"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14zm-7-2h2V7h-4v2h2z"/></svg>}
              />
              <MetricCard
                className="col-span-12 sm:col-span-6 xl:col-span-3"
                title="Avg Confidence"
                value="94.2%"
                change="1.8%"
                changeDir="up"
                subtitle="Across all predictions"
                icon={<svg className="fill-current text-emerald-500" width="24" height="24" viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>}
              />
              <MetricCard
                className="col-span-12 sm:col-span-6 xl:col-span-3"
                title="High Risk"
                value="127"
                change="3.1%"
                changeDir="down"
                subtitle="Flagged for review"
                icon={<svg className="fill-current text-rose-500" width="24" height="24" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>}
              />
            </div>

            {/* Charts row 1 */}
            <div className="grid grid-cols-12 gap-6 mb-6">
              <SubtypeDistributionCard className="col-span-12 lg:col-span-4" />
              <SurvivalCurveCard className="col-span-12 lg:col-span-8" />
            </div>

            {/* Charts row 2 */}
            <div className="grid grid-cols-12 gap-6 mb-6">
              <ModelPerformanceCard className="col-span-12 lg:col-span-6" />
              <RiskStratificationCard className="col-span-12 lg:col-span-6" />
            </div>

            {/* Lower row */}
            <div className="grid grid-cols-12 gap-6">
              <RecentPatientsCard className="col-span-12 xl:col-span-6" />
              <UncertaintyOverviewCard className="col-span-12 xl:col-span-3" />
              <div className="col-span-12 xl:col-span-3 flex flex-col gap-6">
                <SystemStatusCard />
                <ActiveTrialsCard />
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
