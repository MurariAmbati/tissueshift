import { useState } from 'react';
import { useParams } from 'react-router-dom';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import SubtypeBadge from '../components/SubtypeBadge';
import RiskBadge from '../components/RiskBadge';
import { classNames } from '../utils/Utils';

const mockReport = {
  patientId: 'P-2846',
  generated: '2024-01-15 14:32 UTC',
  subtype: 'basal',
  risk: 'high',
  confidence: 0.94,
  stage: 'IIIB',
  summary: 'AI-assisted analysis indicates a basal-like breast carcinoma with high predicted risk. The tumor demonstrates TP53 mutation, BRCA1 promoter methylation, and MYC amplification consistent with aggressive phenotype. Digital twin simulation forecasts 31% 5-year overall survival under standard AC-T regimen, with potential improvement to 57% with immunotherapy combination.',
  recommendations: [
    'Consider Pembrolizumab + chemotherapy combination given high TMB (11.2 mut/Mb) and PD-L1 CPS ≥10',
    'Refer to genetic counseling given BRCA1 methylation — assess germline BRCA1/2 status',
    'Recommend baseline cardiac assessment prior to anthracycline-based chemotherapy',
    'Schedule follow-up digital twin simulation at 3-month post-treatment initiation',
    'Suggest enrollment screening for BRCA-AI-2024 clinical trial (NCT-XXXX)',
  ],
  sections: [
    { title: 'Molecular Profile', content: 'ER(-), PR(-), HER2(-), Ki-67: 82%. TP53 c.742C>T (GOF). BRCA1 promoter hypermethylation. MYC 8q24 amplification. TMB: 11.2 mut/Mb. MSI-stable.' },
    { title: 'Histopathology', content: 'Grade 3 invasive ductal carcinoma, 4.2 cm. Lymphovascular invasion present. 7/18 axillary lymph nodes positive. High mitotic index (14/10 HPF). TIL: 32%.' },
    { title: 'AI Analysis', content: 'Subtype prediction: Basal-like (94% confidence). 5 attention hotspots identified on WSI-0089. Key latent features: proliferation index 88%, immune infiltrate 64%, stromal score 42%.' },
    { title: 'Treatment Forecast', content: 'Digital twin forecast with AC-T: 1yr OS 78%, 2yr OS 54%, 5yr OS 31%. With Pembrolizumab + chemo: 1yr OS 93%, 2yr OS 79%, 5yr OS 57%. Estimated pCR: 42% with immunotherapy.' },
    { title: 'Uncertainty Statement', content: 'Prediction confidence 94% with epistemic uncertainty 0.03 (well within training distribution). Conformal set: {Basal-like} at α=0.05. ECE contribution: 0.012.' },
  ],
};

export default function ReportGenerator() {
  const { id } = useParams();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [format, setFormat] = useState('clinical');
  const [generating, setGenerating] = useState(false);

  const handleGenerate = () => {
    setGenerating(true);
    setTimeout(() => setGenerating(false), 1500);
  };

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
            <div className="flex flex-wrap items-center justify-between mb-8">
              <div>
                <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold">Clinical Report</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{id ? `Patient ${id}` : 'Generate comprehensive AI-assisted clinical reports'}</p>
              </div>
              <div className="flex gap-2 mt-4 sm:mt-0">
                <select className="form-select text-sm rounded-lg border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-800" value={format} onChange={(e) => setFormat(e.target.value)}>
                  <option value="clinical">Clinical Summary</option>
                  <option value="research">Research Report</option>
                  <option value="pathology">Pathology Report</option>
                </select>
                <button onClick={handleGenerate} className="btn text-sm font-medium bg-violet-500 text-white rounded-lg px-4 py-2 hover:bg-violet-600" disabled={generating}>
                  {generating ? 'Generating...' : 'Regenerate'}
                </button>
                <button className="btn text-sm font-medium bg-gray-900 text-gray-100 rounded-lg px-4 py-2 hover:bg-gray-800 dark:bg-gray-100 dark:text-gray-800 dark:hover:bg-white">
                  Download PDF
                </button>
              </div>
            </div>

            {/* Report content */}
            <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-8 max-w-4xl mx-auto">
              {/* Header */}
              <div className="border-b border-gray-200 dark:border-gray-700/60 pb-6 mb-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100">TissueShift Clinical Report</h2>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{mockReport.generated}</p>
                  </div>
                  <span className="text-xs font-medium px-3 py-1 rounded-full bg-violet-100 dark:bg-violet-500/20 text-violet-700 dark:text-violet-400">AI-Assisted</span>
                </div>
                <div className="flex flex-wrap gap-3 items-center">
                  <span className="text-lg font-semibold text-gray-800 dark:text-gray-100">{mockReport.patientId}</span>
                  <SubtypeBadge subtype={mockReport.subtype} />
                  <RiskBadge level={mockReport.risk} />
                  <span className="text-sm text-gray-500">Stage {mockReport.stage}</span>
                </div>
              </div>

              {/* Executive summary */}
              <div className="mb-8">
                <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-3">Executive Summary</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{mockReport.summary}</p>
              </div>

              {/* Recommendations */}
              <div className="mb-8 bg-violet-50 dark:bg-violet-500/5 rounded-xl p-5">
                <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-3">Clinical Recommendations</h3>
                <ol className="space-y-2">
                  {mockReport.recommendations.map((rec, i) => (
                    <li key={i} className="flex gap-3 text-sm text-gray-700 dark:text-gray-300">
                      <span className="shrink-0 w-6 h-6 rounded-full bg-violet-500 text-white flex items-center justify-center text-xs font-bold">{i + 1}</span>
                      {rec}
                    </li>
                  ))}
                </ol>
              </div>

              {/* Sections */}
              {mockReport.sections.map((section) => (
                <div key={section.title} className="mb-6">
                  <h3 className="text-base font-semibold text-gray-800 dark:text-gray-100 mb-2 pb-2 border-b border-gray-100 dark:border-gray-700/60">{section.title}</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{section.content}</p>
                </div>
              ))}

              {/* Disclaimer */}
              <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700/60">
                <p className="text-xs text-gray-400 dark:text-gray-500 italic">
                  This report was generated with AI assistance by TissueShift. All predictions and recommendations should be reviewed by a qualified pathologist or oncologist before clinical decision-making. Model confidence: {(mockReport.confidence * 100).toFixed(0)}%.
                </p>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
