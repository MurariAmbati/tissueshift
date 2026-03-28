import { useState } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import GlowCard from '../components/GlowCard';
import PulseRing from '../components/PulseRing';

/* ── NCCN Guideline tree ──────────────────────────────────────── */
const GUIDELINE = {
  title: 'NCCN Breast Cancer Clinical Practice Guidelines v4.2024',
  version: '4.2024',
  lastUpdated: '2024-03-15',
  categories: [
    {
      id: 'workup', name: 'Initial Workup', icon: 'IW',
      nodes: [
        { id: 'w1', text: 'Core needle biopsy with ER, PR, HER2, Ki-67', status: 'complete', detail: 'Required for all newly diagnosed invasive breast cancer. HER2 testing per ASCO/CAP 2023 guidelines.' },
        { id: 'w2', text: 'Staging imaging per clinical stage', status: 'complete', detail: 'CT chest/abdomen/pelvis + bone scan OR PET/CT for Stage ≥ IIB.' },
        { id: 'w3', text: 'Genetic counseling if ≤50 yo or TNBC', status: 'current', detail: 'BRCA1/2, PALB2, TP53, ATM, CHEK2 — multi-gene panel recommended.' },
        { id: 'w4', text: 'Fertility counseling (premenopausal)', status: 'pending', detail: 'Refer to reproductive endocrinology prior to systemic therapy.' },
        { id: 'w5', text: 'Cardiology baseline (HER2+ or anthracycline)', status: 'pending', detail: 'Baseline LVEF by ECHO or MUGA. Serial monitoring q3mo during HER2-targeted tx.' },
      ],
    },
    {
      id: 'neoadjuvant', name: 'Neoadjuvant Therapy', icon: 'NT',
      nodes: [
        { id: 'n1', text: 'HER2+: TCHP × 6 (Category 1)', status: 'current', detail: 'Docetaxel + Carboplatin + Trastuzumab + Pertuzumab. RCB-0/1 rate ~60%. Consider ddAC-THP only if high-risk features.' },
        { id: 'n2', text: 'TNBC: Pembrolizumab + carbo-taxol → AC', status: 'not-applicable', detail: 'KEYNOTE-522 regimen. Category 1. Adjuvant pembrolizumab for 9 additional cycles regardless of pathCR.' },
        { id: 'n3', text: 'HR+/HER2-: Consider chemotherapy if high-risk', status: 'not-applicable', detail: 'OncotypeDX RS ≥ 26 or clinical high-risk. Consider endocrine monotherapy if low-risk (RS < 16).' },
        { id: 'n4', text: 'Imaging assessment q2 cycles', status: 'pending', detail: 'Breast MRI preferred. Adjust regimen if PD. Consider surgery if no response after 2 cycles.' },
      ],
    },
    {
      id: 'surgery', name: 'Surgical Management', icon: 'SM',
      nodes: [
        { id: 's1', text: 'BCS if favorable tumor-to-breast ratio + clear margins', status: 'pending', detail: 'No ink on tumor = negative margin for invasive cancer. Re-excision if positive margin.' },
        { id: 's2', text: 'Mastectomy with reconstruction options', status: 'pending', detail: 'Indicated if multicentric disease, extensive DCIS, or patient preference.' },
        { id: 's3', text: 'SLNB pre-neoadjuvant or post-neoadjuvant', status: 'pending', detail: 'If cN0: SLNB at surgery. If cN1→ycN0 after NAT: SLNB with ≥3 nodes and dual tracer (FNR < 10%).' },
        { id: 's4', text: 'ALND if ≥3 positive nodes or persistent disease', status: 'pending', detail: 'Level I/II dissection. Consider PMRT if ≥4 nodes or cT3-4.' },
      ],
    },
    {
      id: 'adjuvant', name: 'Adjuvant Therapy', icon: 'AT',
      nodes: [
        { id: 'a1', text: 'HER2+ with residual disease: T-DM1 × 14 cycles', status: 'pending', detail: 'KATHERINE trial: 50% reduction in recurrence with T-DM1 vs trastuzumab in patients with residual disease post-NAT.' },
        { id: 'a2', text: 'HER2+ with pCR: Complete trastuzumab ± pertuzumab', status: 'pending', detail: 'Total 1 year of HER2-targeted therapy. APHINITY: pertuzumab adds modest iDFS benefit in node-positive.' },
        { id: 'a3', text: 'TNBC + BRCA: Olaparib × 12 months', status: 'pending', detail: 'OlympiA: Adjuvant olaparib in BRCA+ high-risk early BC. 7.3% absolute iDFS benefit at 3 years.' },
        { id: 'a4', text: 'HR+: Endocrine therapy ≥ 5 years', status: 'pending', detail: 'Tamoxifen or AI. Extended therapy to 10y in high-risk. OFS + AI in premenopausal high-risk (TEXT/SOFT).' },
        { id: 'a5', text: 'Radiation per BCS or high-risk mastectomy', status: 'pending', detail: 'Whole breast + boost after BCS. PMRT if T3-4, ≥4 nodes, or close margins.' },
      ],
    },
    {
      id: 'surveillance', name: 'Surveillance & Follow-up', icon: 'SF',
      nodes: [
        { id: 'su1', text: 'H&P every 3-6 months × 3 years', status: 'pending', detail: 'Then every 6-12 months to year 5, then annually.' },
        { id: 'su2', text: 'Annual mammography', status: 'pending', detail: 'First post-treatment mammogram 6-12 months after completing radiation.' },
        { id: 'su3', text: 'Monitor endocrine therapy adherence', status: 'pending', detail: 'Address side effects. Bone density if on AI. Lipid panel annually.' },
        { id: 'su4', text: 'Cardiac monitoring if HER2-targeted or anthracycline', status: 'pending', detail: 'ECHO at 6, 12, 24 months post-treatment. LVEF monitoring.' },
      ],
    },
  ],
};

const STATUS_COLORS = {
  complete: { bg: 'bg-emerald-500/15', text: 'text-emerald-600 dark:text-emerald-400', dot: 'bg-emerald-500', label: 'Complete' },
  current: { bg: 'bg-violet-500/15', text: 'text-violet-600 dark:text-violet-400', dot: 'bg-violet-500', label: 'Current' },
  pending: { bg: 'bg-gray-500/10', text: 'text-gray-500', dot: 'bg-gray-400', label: 'Pending' },
  'not-applicable': { bg: 'bg-gray-500/5', text: 'text-gray-400', dot: 'bg-gray-300 dark:bg-gray-600', label: 'N/A' },
};

export default function NCCNNavigator() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [expandedCat, setExpandedCat] = useState('workup');
  const [selectedNode, setSelectedNode] = useState(null);

  const currentStep = GUIDELINE.categories.flatMap(c => c.nodes).find(n => n.status === 'current');

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[1600px] mx-auto">
            <div className="mb-6">
              <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
                NCCN Guideline Navigator
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{GUIDELINE.title} · Last updated {GUIDELINE.lastUpdated}</p>
            </div>

            {/* Current step highlight */}
            {currentStep && (
              <GlowCard glowColor="violet" className="!p-4 mb-6">
                <div className="flex items-center gap-3">
                  <PulseRing color="violet" size="sm" />
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-violet-500 font-semibold">Current Guideline Step</div>
                    <div className="text-sm font-bold text-gray-800 dark:text-white">{currentStep.text}</div>
                  </div>
                </div>
              </GlowCard>
            )}

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              {/* Guideline tree */}
              <div className="xl:col-span-2 space-y-3">
                {GUIDELINE.categories.map(cat => {
                  const isExpanded = expandedCat === cat.id;
                  const completedCount = cat.nodes.filter(n => n.status === 'complete').length;
                  const currentCount = cat.nodes.filter(n => n.status === 'current').length;
                  return (
                    <GlowCard key={cat.id} glowColor={currentCount > 0 ? 'violet' : completedCount === cat.nodes.length ? 'emerald' : 'sky'} className="!p-0 overflow-hidden">
                      <button
                        onClick={() => setExpandedCat(isExpanded ? null : cat.id)}
                        className="w-full flex items-center justify-between p-4 text-left"
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-xs font-bold text-violet-600 dark:text-violet-400 bg-violet-50 dark:bg-violet-500/10 w-7 h-7 rounded-lg flex items-center justify-center">{cat.icon}</span>
                          <div>
                            <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100">{cat.name}</h3>
                            <p className="text-[10px] text-gray-400">{completedCount}/{cat.nodes.length} steps completed</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {currentCount > 0 && <PulseRing color="violet" size="sm" />}
                          <svg className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                        </div>
                      </button>
                      {isExpanded && (
                        <div className="px-4 pb-4">
                          <div className="border-l-2 border-gray-200 dark:border-gray-700 ml-5 pl-6 space-y-3">
                            {cat.nodes.map(node => {
                              const s = STATUS_COLORS[node.status];
                              return (
                                <button
                                  key={node.id}
                                  onClick={() => setSelectedNode(node)}
                                  className={`w-full text-left p-3 rounded-xl border transition-all ${
                                    selectedNode?.id === node.id
                                      ? 'border-violet-400 dark:border-violet-500 bg-violet-50 dark:bg-violet-900/10'
                                      : 'border-gray-200 dark:border-gray-700/60 hover:border-violet-300'
                                  }`}
                                >
                                  <div className="flex items-start gap-2">
                                    <span className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${s.dot}`} />
                                    <div className="flex-1">
                                      <div className="text-xs font-semibold text-gray-800 dark:text-gray-100">{node.text}</div>
                                      <span className={`inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded font-semibold ${s.bg} ${s.text}`}>{s.label}</span>
                                    </div>
                                  </div>
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </GlowCard>
                  );
                })}
              </div>

              {/* Detail panel */}
              <div className="space-y-4">
                {selectedNode ? (
                  <GlowCard glowColor="teal" className="!p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <span className={`w-2.5 h-2.5 rounded-full ${STATUS_COLORS[selectedNode.status].dot}`} />
                      <span className={`text-[10px] font-semibold uppercase ${STATUS_COLORS[selectedNode.status].text}`}>{STATUS_COLORS[selectedNode.status].label}</span>
                    </div>
                    <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">{selectedNode.text}</h3>
                    <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
                      <h4 className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">Guideline Detail</h4>
                      <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">{selectedNode.detail}</p>
                    </div>
                  </GlowCard>
                ) : (
                  <GlowCard glowColor="teal" className="!p-6 text-center">

                    <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-1">Select a Step</h3>
                    <p className="text-xs text-gray-400">Click any guideline step to see the detailed clinical recommendation.</p>
                  </GlowCard>
                )}

                {/* Progress overview */}
                <GlowCard glowColor="emerald" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Overall Progress</h3>
                  {GUIDELINE.categories.map(cat => {
                    const total = cat.nodes.length;
                    const done = cat.nodes.filter(n => n.status === 'complete').length;
                    const pct = Math.round((done / total) * 100);
                    return (
                      <div key={cat.id} className="mb-2">
                        <div className="flex justify-between mb-0.5">
                          <span className="text-[10px] text-gray-500">{cat.icon} {cat.name}</span>
                          <span className="text-[10px] font-bold text-gray-400 tabular-nums">{done}/{total}</span>
                        </div>
                        <div className="h-1.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                          <div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </GlowCard>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
