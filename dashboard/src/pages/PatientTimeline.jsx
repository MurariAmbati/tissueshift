import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import RiskBadge from '../components/RiskBadge';
import SubtypeBadge from '../components/SubtypeBadge';
import { classNames } from '../utils/Utils';

const events = [
  { date: '2024-01-15', type: 'analysis', title: 'Slide Analysis Complete', detail: 'WSI-0089 analyzed. Basal-like subtype with 94% confidence. 7 attention hotspots identified.', risk: 'high' },
  { date: '2024-01-10', type: 'treatment', title: 'Chemotherapy Cycle 2 Started', detail: 'AC-T regimen: Doxorubicin 60mg/m² + Cyclophosphamide 600mg/m². No Grade 3+ adverse events from Cycle 1.' },
  { date: '2024-01-05', type: 'genomic', title: 'Genomic Profiling Results', detail: 'TP53 mutation (c.742C>T), BRCA1 promoter methylation, MYC amplification (8q24). TMB: 11.2 mut/Mb.' },
  { date: '2024-01-02', type: 'treatment', title: 'Treatment Plan Initiated', detail: 'Neoadjuvant AC-T followed by Pembrolizumab. Digital twin forecast: 23% pCR probability.' },
  { date: '2023-12-28', type: 'biopsy', title: 'Core Needle Biopsy', detail: 'Right breast, 10 o\'clock, 4.2cm mass. Grade 3 invasive ductal carcinoma. 7/18 lymph nodes positive.' },
  { date: '2023-12-20', type: 'imaging', title: 'Initial Imaging', detail: 'Mammography + MRI: 4.2cm irregular mass right breast. Suspicious axillary lymphadenopathy. BI-RADS 5.' },
  { date: '2023-12-15', type: 'visit', title: 'Initial Consultation', detail: 'Patient presented with palpable right breast mass. Family history: mother diagnosed with breast cancer at age 52.' },
];

const typeIcons = {
  analysis: { color: 'text-violet-500 bg-violet-100 dark:bg-violet-500/20', label: 'AI' },
  treatment: { color: 'text-teal-500 bg-teal-100 dark:bg-teal-500/20', label: 'Tx' },
  genomic: { color: 'text-indigo-500 bg-indigo-100 dark:bg-indigo-500/20', label: 'Gx' },
  biopsy: { color: 'text-rose-500 bg-rose-100 dark:bg-rose-500/20', label: 'Bx' },
  imaging: { color: 'text-amber-500 bg-amber-100 dark:bg-amber-500/20', label: 'Img' },
  visit: { color: 'text-gray-500 bg-gray-100 dark:bg-gray-700/50', label: 'Vis' },
};

export default function PatientTimeline() {
  const { id } = useParams();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
            <div className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              <Link to="/patients" className="text-violet-500 hover:text-violet-600">Patients</Link>
              <span className="mx-2">→</span>
              <Link to={`/patients/${id}`} className="text-violet-500 hover:text-violet-600">{id}</Link>
              <span className="mx-2">→</span>
              <span>Timeline</span>
            </div>

            <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold mb-8">Patient Timeline</h1>

            <div className="relative">
              {/* Vertical line */}
              <div className="absolute left-[1.625rem] top-3 bottom-3 w-0.5 bg-gray-200 dark:bg-gray-700" />

              <div className="space-y-6">
                {events.map((event, i) => {
                  const icon = typeIcons[event.type] || typeIcons.visit;
                  return (
                    <div key={i} className="relative flex gap-4 items-start">
                      {/* Icon */}
                      <div className={classNames('flex items-center justify-center w-[3.25rem] h-[3.25rem] rounded-full shrink-0 text-xs font-bold z-10', icon.color)}>
                        {icon.label}
                      </div>
                      {/* Content */}
                      <div className="flex-1 bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-4">
                        <div className="flex items-center justify-between mb-1">
                          <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-100">{event.title}</h3>
                          <span className="text-xs text-gray-400 dark:text-gray-500">{event.date}</span>
                        </div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">{event.detail}</p>
                        {event.risk && <div className="mt-2"><RiskBadge level={event.risk} size="sm" /></div>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
