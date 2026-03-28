import { useState } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import GlowCard from '../components/GlowCard';
import PulseRing from '../components/PulseRing';

/* ── Tumor board case data ────────────────────────────────────── */
const CASES = [
  {
    id: 'TB-2024-0087', patient: 'Rachel Adams', age: 52, mrn: 'MRN-99281',
    diagnosis: 'Invasive Ductal Carcinoma, HER2+, Grade 3',
    stage: 'IIIA (T3 N1 M0)',
    status: 'Under Review',
    presentedBy: 'Dr. Sarah Kim (Medical Oncology)',
    question: 'Optimal neoadjuvant regimen — TCHP vs ddAC-THP?',
    history: 'Diagnosed 6 weeks ago. Core biopsy: IDC, ER 45%, PR 12%, HER2 3+ (IHC), Ki67 62%. Staging CT/PET: 4.2cm primary, 2 ipsilateral axillary LN (SUV 6.8). No distant mets. Genetic testing: BRCA1/2 negative, PIK3CA E545K mutation detected.',
    panelists: [
      { name: 'Dr. S. Kim', role: 'Medical Oncology', vote: 'TCHP × 6', rationale: 'Standard of care with strong RCB-0 data in HER2+' },
      { name: 'Dr. J. Park', role: 'Surgical Oncology', vote: 'TCHP × 6', rationale: 'May convert to BCS if good response — serial imaging recommended' },
      { name: 'Dr. L. Chen', role: 'Radiation Oncology', vote: 'Defer to post-surgical planning', rationale: 'PMRT will depend on surgical outcome and residual burden' },
      { name: 'Dr. R. Patel', role: 'Pathology', vote: 'TCHP × 6, consider alpelisib', rationale: 'PIK3CA E545K may benefit from PI3K inhibitor — consider add-on or trial' },
      { name: 'Dr. M. Tanaka', role: 'Radiology', vote: 'MRI q2 cycles', rationale: 'Need to monitor response for surgical planning' },
      { name: 'Dr. A. Nguyen', role: 'Genomics', vote: 'Trial enrollment NCTXXXXX', rationale: 'PIK3CA mutation makes patient eligible for neoadjuvant capivasertib trial' },
    ],
    aiRecommendation: {
      regimen: 'TCHP × 6 cycles (docetaxel + carboplatin + trastuzumab + pertuzumab)',
      confidence: 94,
      rationale: 'HER2 3+ with pathCR rates > 60% in pivotal trials (NeoSphere, TRYPHAENA). PIK3CA E545K may reduce pCR rate (~15% lower) — consider capivasertib add-on (CAPItello-281 trial eligible). ddAC-THP shows no PFS benefit over TCHP in HER2+ and adds anthracycline cardiotoxicity risk.',
      alternatives: [
        { name: 'ddAC-THP', reason: 'Higher pathCR in TNBC but comparable in HER2+ with more toxicity' },
        { name: 'THP + Capivasertib (trial)', reason: 'PIK3CA-mutated HER2+ — investigational but compelling rationale' },
      ],
      riskFactors: ['PIK3CA mutation — may reduce HER2-targeted therapy efficacy', 'Grade 3 — aggressive biology', 'N1 — axillary involvement'],
    },
    consensus: null,
  },
  {
    id: 'TB-2024-0088', patient: 'Jane Doe', age: 48, mrn: 'MRN-88419',
    diagnosis: 'Triple-Negative Breast Cancer, Grade 3',
    stage: 'IIB (T2 N1 M0)',
    status: 'Consensus Reached',
    presentedBy: 'Dr. Robert Liu (Medical Oncology)',
    question: 'Pembrolizumab neoadjuvant — PD-L1 CPS 8 (below 10 cutoff)',
    history: 'Core biopsy: IDC, ER 0%, PR 0%, HER2 0 (IHC). Ki67 85%. PD-L1 CPS 8. BRCA1 germline mutation confirmed. 2.8cm tumor, 1 positive axillary node.',
    panelists: [
      { name: 'Dr. R. Liu', role: 'Medical Oncology', vote: 'Pembro + carbo-taxol', rationale: 'KEYNOTE-522 included CPS < 10 and showed EFS benefit across subgroups' },
      { name: 'Dr. S. Kim', role: 'Medical Oncology', vote: 'Agrees — add olaparib adjuvant', rationale: 'BRCA1+ qualifies for OlympiA adjuvant olaparib post-surgery' },
    ],
    aiRecommendation: {
      regimen: 'Pembrolizumab + carboplatin-paclitaxel → AC → Surgery → Adj pembro + olaparib',
      confidence: 91,
      rationale: 'KEYNOTE-522: EFS benefit in ITT population regardless of CPS cutoff. OlympiA: olaparib adjuvant in BRCA+ high-risk TNBC showed iDFS benefit.',
      alternatives: [
        { name: 'Carbo-taxol → AC without pembro', reason: 'If concerns about autoimmune toxicity' },
      ],
      riskFactors: ['CPS 8 — borderline PD-L1', 'BRCA1 — eligible for PARP inhibitor adjuvant'],
    },
    consensus: 'Pembrolizumab + carbo-taxol neoadjuvant → AC → Surgery → Adjuvant pembrolizumab × 9 cycles + olaparib × 12 months',
  },
];

export default function TumorBoard() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeCase, setActiveCase] = useState(CASES[0]);
  const [showAI, setShowAI] = useState(true);

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[1600px] mx-auto">
            <div className="mb-6 flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
              <div>
                <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
                  Virtual Tumor Board
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Multi-disciplinary case review with AI-augmented treatment consensus</p>
              </div>
              <button
                onClick={() => setShowAI(!showAI)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${showAI ? 'bg-violet-500 text-white' : 'bg-white dark:bg-gray-800 text-gray-500 border border-gray-200 dark:border-gray-700/60'}`}
              >
                {showAI ? 'AI Recommendations ON' : 'AI Recommendations OFF'}
              </button>
            </div>

            {/* Case tabs */}
            <div className="flex gap-2 mb-6">
              {CASES.map(c => (
                <button
                  key={c.id}
                  onClick={() => setActiveCase(c)}
                  className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2 ${
                    activeCase.id === c.id
                      ? 'bg-rose-500 text-white shadow-lg shadow-rose-500/30'
                      : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700/60'
                  }`}
                >
                  {c.status === 'Under Review' && <PulseRing color="rose" size="sm" />}
                  {c.patient} · {c.id}
                </button>
              ))}
            </div>

            {/* Case Header */}
            <GlowCard glowColor="rose" className="!p-4 mb-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100">{activeCase.patient}, {activeCase.age}F</h2>
                  <p className="text-xs text-gray-400">{activeCase.mrn} · {activeCase.diagnosis} · {activeCase.stage}</p>
                  <p className="text-xs text-gray-400 mt-0.5">Presented by {activeCase.presentedBy}</p>
                </div>
                <span className={`px-3 py-1 rounded-full text-[10px] font-bold ${
                  activeCase.status === 'Under Review' ? 'bg-amber-500/15 text-amber-600 dark:text-amber-400' : 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                }`}>{activeCase.status}</span>
              </div>
              <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
                <h4 className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">Clinical Question</h4>
                <p className="text-sm font-semibold text-gray-800 dark:text-white">{activeCase.question}</p>
              </div>
            </GlowCard>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              {/* Left 2/3: Case details + panelists */}
              <div className="xl:col-span-2 space-y-4">
                {/* Case history */}
                <GlowCard glowColor="violet" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-2">Clinical History & Workup</h3>
                  <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">{activeCase.history}</p>
                </GlowCard>

                {/* Panel votes */}
                <GlowCard glowColor="sky" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Panel Recommendations ({activeCase.panelists.length})</h3>
                  <div className="space-y-3">
                    {activeCase.panelists.map(p => (
                      <div key={p.name} className="p-3 bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700/60 rounded-xl">
                        <div className="flex items-start justify-between gap-2 mb-1">
                          <div>
                            <span className="text-sm font-bold text-gray-800 dark:text-gray-100">{p.name}</span>
                            <span className="text-[10px] text-gray-400 ml-2">{p.role}</span>
                          </div>
                        </div>
                        <div className="text-xs mt-1">
                          <span className="text-violet-500 font-bold">Vote: </span>
                          <span className="text-gray-700 dark:text-gray-300">{p.vote}</span>
                        </div>
                        <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1 italic">{p.rationale}</p>
                      </div>
                    ))}
                  </div>
                </GlowCard>

                {/* Consensus */}
                {activeCase.consensus && (
                  <GlowCard glowColor="emerald" className="!p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-emerald-500 text-lg">✓</span>
                      <h3 className="text-sm font-bold text-emerald-700 dark:text-emerald-400">Board Consensus</h3>
                    </div>
                    <p className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">{activeCase.consensus}</p>
                  </GlowCard>
                )}
              </div>

              {/* Right: AI recommendation */}
              {showAI && (
                <div className="space-y-4">
                  <GlowCard glowColor="indigo" className="!p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-xs font-bold text-violet-600 dark:text-violet-400 bg-violet-50 dark:bg-violet-500/10 w-6 h-6 rounded flex items-center justify-center">AI</span>
                      <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100">AI Treatment Recommendation</h3>
                    </div>
                    <div className="p-3 bg-violet-500/5 rounded-xl mb-3">
                      <div className="text-xs font-bold text-violet-600 dark:text-violet-400 mb-1">Recommended Regimen</div>
                      <p className="text-sm font-semibold text-gray-800 dark:text-white">{activeCase.aiRecommendation.regimen}</p>
                    </div>

                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-xs text-gray-400">Confidence:</span>
                      <div className="flex-1 h-2 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                        <div className="h-full rounded-full bg-emerald-500" style={{ width: `${activeCase.aiRecommendation.confidence}%` }} />
                      </div>
                      <span className="text-xs font-bold text-emerald-500">{activeCase.aiRecommendation.confidence}%</span>
                    </div>

                    <h4 className="text-[10px] uppercase tracking-wider text-gray-400 mb-1.5">Rationale</h4>
                    <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed mb-3">{activeCase.aiRecommendation.rationale}</p>

                    <h4 className="text-[10px] uppercase tracking-wider text-gray-400 mb-1.5">Alternatives Considered</h4>
                    <div className="space-y-2 mb-3">
                      {activeCase.aiRecommendation.alternatives.map(a => (
                        <div key={a.name} className="p-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                          <div className="text-xs font-bold text-gray-800 dark:text-gray-100">{a.name}</div>
                          <div className="text-[10px] text-gray-400">{a.reason}</div>
                        </div>
                      ))}
                    </div>

                    <h4 className="text-[10px] uppercase tracking-wider text-gray-400 mb-1.5">Key Risk Factors</h4>
                    <div className="space-y-1">
                      {activeCase.aiRecommendation.riskFactors.map(r => (
                        <div key={r} className="text-xs text-rose-600 dark:text-rose-400 flex items-center gap-1.5">
                          <span className="text-[8px] text-amber-500 font-bold">!</span> {r}
                        </div>
                      ))}
                    </div>
                  </GlowCard>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
