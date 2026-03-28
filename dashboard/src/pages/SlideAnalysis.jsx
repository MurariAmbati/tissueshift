import { useState, useRef } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import SubtypeBadge from '../components/SubtypeBadge';
import RiskBadge from '../components/RiskBadge';
import ConfidenceBar from '../components/ConfidenceBar';
import { classNames } from '../utils/Utils';

export default function SlideAnalysis() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [file, setFile] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const fileInputRef = useRef(null);

  const handleUpload = () => {
    setAnalyzing(true);
    // Simulate analysis
    setTimeout(() => {
      setResult({
        slideId: 'WSI-' + Math.floor(Math.random() * 9000 + 1000),
        subtype: 'her2_enriched',
        confidence: 0.91,
        risk: 'moderate',
        hotspots: 5,
        cellCount: 48720,
        mitoticIndex: 14,
        tumorPurity: 0.78,
        til: 0.32,
        necrosisPercent: 8.4,
        attentionRegions: [
          { x: 120, y: 340, weight: 0.95, label: 'HER2 amplified cluster' },
          { x: 456, y: 128, weight: 0.87, label: 'High mitotic region' },
          { x: 312, y: 510, weight: 0.82, label: 'TIL-rich zone' },
          { x: 89, y: 42, weight: 0.76, label: 'Grade 3 architecture' },
          { x: 540, y: 380, weight: 0.71, label: 'Necrotic boundary' },
        ],
        latentComponents: [
          { name: 'Proliferation Index', value: 0.88 },
          { name: 'Immune Infiltrate', value: 0.64 },
          { name: 'Stromal Score', value: 0.42 },
          { name: 'Angiogenesis', value: 0.55 },
          { name: 'DNA Damage Response', value: 0.73 },
        ],
      });
      setAnalyzing(false);
    }, 2500);
  };

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
            <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold mb-2">Slide Analysis</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-8">Upload whole-slide images for AI-powered subtype prediction, attention mapping, and morphological analysis</p>

            <div className="grid grid-cols-12 gap-6">
              {/* Upload zone */}
              <div className="col-span-12 lg:col-span-5">
                <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-6">
                  <div
                    className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl p-8 text-center cursor-pointer hover:border-violet-400 transition-colors"
                    onClick={() => fileInputRef.current?.click()}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => { e.preventDefault(); setFile(e.dataTransfer.files[0]); }}
                  >
                    <input ref={fileInputRef} type="file" className="hidden" accept=".svs,.ndpi,.tiff,.png,.jpg" onChange={(e) => setFile(e.target.files[0])} />
                    <svg className="mx-auto mb-4 text-gray-400" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" />
                    </svg>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                      {file ? file.name : 'Drop WSI file here or click to browse'}
                    </p>
                    <p className="text-xs text-gray-400">Supports: SVS, NDPI, TIFF, PNG, JPEG</p>
                  </div>
                  <button
                    className={classNames(
                      'w-full mt-4 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
                      file && !analyzing
                        ? 'bg-violet-500 text-white hover:bg-violet-600'
                        : 'bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed',
                    )}
                    disabled={!file || analyzing}
                    onClick={handleUpload}
                  >
                    {analyzing ? (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                        Analyzing...
                      </span>
                    ) : 'Run Analysis'}
                  </button>

                  {/* Recent slides */}
                  <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700/60">
                    <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-3">Recent Analyses</h3>
                    <ul className="space-y-2">
                      {['WSI-0089', 'WSI-0088', 'WSI-0087'].map((s) => (
                        <li key={s} className="flex items-center justify-between text-sm p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/20 cursor-pointer">
                          <span className="text-gray-700 dark:text-gray-300">{s}</span>
                          <span className="text-xs text-gray-400">2 hrs ago</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              {/* Results */}
              <div className="col-span-12 lg:col-span-7">
                {!result ? (
                  <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-12 text-center">
                    <svg className="mx-auto mb-4 text-gray-300 dark:text-gray-600" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                      <rect x="3" y="3" width="18" height="18" rx="2" />
                      <circle cx="8.5" cy="8.5" r="1.5" /><path d="M21 15l-5-5L5 21" />
                    </svg>
                    <p className="text-gray-400 dark:text-gray-500">Upload and analyze a slide to see results</p>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {/* Summary row */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                      {[
                        { label: 'Cells Counted', value: result.cellCount.toLocaleString() },
                        { label: 'Mitotic Index', value: `${result.mitoticIndex}/10 HPF` },
                        { label: 'Tumor Purity', value: `${(result.tumorPurity * 100).toFixed(0)}%` },
                        { label: 'TIL Score', value: `${(result.til * 100).toFixed(0)}%` },
                      ].map((m) => (
                        <div key={m.label} className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-4 text-center">
                          <div className="text-xl font-bold text-gray-800 dark:text-gray-100">{m.value}</div>
                          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{m.label}</div>
                        </div>
                      ))}
                    </div>

                    {/* Prediction */}
                    <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5">
                      <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Prediction Result</h2>
                      <div className="flex items-center gap-4 mb-4">
                        <SubtypeBadge subtype={result.subtype} />
                        <RiskBadge level={result.risk} />
                        <span className="text-sm text-gray-500">Slide: {result.slideId}</span>
                      </div>
                      <ConfidenceBar score={result.confidence} height="h-3" />
                    </div>

                    {/* Attention hotspots */}
                    <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5">
                      <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Attention Hotspots ({result.hotspots})</h2>
                      <div className="space-y-2">
                        {result.attentionRegions.map((r, i) => (
                          <div key={i} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900/30 rounded-lg">
                            <div>
                              <span className="text-sm font-medium text-gray-800 dark:text-gray-100">{r.label}</span>
                              <span className="text-xs text-gray-400 ml-2">({r.x}, {r.y})</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <div className="w-20 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                <div className="h-full bg-violet-500 rounded-full" style={{ width: `${r.weight * 100}%` }} />
                              </div>
                              <span className="text-xs font-medium text-gray-600 dark:text-gray-300 w-10 text-right">{(r.weight * 100).toFixed(0)}%</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Latent components */}
                    <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5">
                      <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Latent Components</h2>
                      <div className="space-y-3">
                        {result.latentComponents.map((c) => (
                          <div key={c.name}>
                            <div className="flex justify-between text-sm mb-1">
                              <span className="text-gray-600 dark:text-gray-300">{c.name}</span>
                              <span className="font-medium text-gray-800 dark:text-gray-100">{(c.value * 100).toFixed(0)}%</span>
                            </div>
                            <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                              <div className="h-full bg-violet-500 rounded-full transition-all duration-700" style={{ width: `${c.value * 100}%` }} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
