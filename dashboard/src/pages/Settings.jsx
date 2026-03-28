import { useState } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import { classNames } from '../utils/Utils';

export default function Settings() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [apiUrl, setApiUrl] = useState('http://localhost:8000');
  const [modelVersion, setModelVersion] = useState('v2.1');
  const [conformalAlpha, setConformalAlpha] = useState('0.05');
  const [dpEpsilon, setDpEpsilon] = useState('1.2');
  const [autoReport, setAutoReport] = useState(true);
  const [riskThreshold, setRiskThreshold] = useState('0.7');
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-4xl mx-auto">
            <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold mb-8">Settings</h1>

            <div className="space-y-8">
              {/* API Configuration */}
              <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-6">
                <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">API Configuration</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Backend URL</label>
                    <input type="text" className="form-input w-full text-sm rounded-lg border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-800" value={apiUrl} onChange={(e) => setApiUrl(e.target.value)} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Model Version</label>
                    <select className="form-select w-full text-sm rounded-lg border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-800" value={modelVersion} onChange={(e) => setModelVersion(e.target.value)}>
                      <option>v2.1</option>
                      <option>v2.0</option>
                      <option>v1.5</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Clinical Parameters */}
              <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-6">
                <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Clinical Parameters</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Risk Threshold (high-risk cutoff)</label>
                    <input type="number" step="0.05" min="0" max="1" className="form-input w-full text-sm rounded-lg border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-800" value={riskThreshold} onChange={(e) => setRiskThreshold(e.target.value)} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Conformal Alpha (significance level)</label>
                    <input type="number" step="0.01" min="0.01" max="0.5" className="form-input w-full text-sm rounded-lg border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-800" value={conformalAlpha} onChange={(e) => setConformalAlpha(e.target.value)} />
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Auto-generate Reports</label>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Automatically create clinical reports for new analyses</p>
                    </div>
                    <div className="form-switch">
                      <input type="checkbox" id="auto-report" className="sr-only" checked={autoReport} onChange={() => setAutoReport(!autoReport)} />
                      <label className={classNames('block w-11 h-6 rounded-full cursor-pointer transition-colors', autoReport ? 'bg-violet-500' : 'bg-gray-300 dark:bg-gray-600')} htmlFor="auto-report">
                        <span className={classNames('block w-5 h-5 bg-white rounded-full shadow transform transition-transform mt-0.5', autoReport ? 'translate-x-[1.375rem]' : 'translate-x-0.5')} />
                      </label>
                    </div>
                  </div>
                </div>
              </div>

              {/* Federated Privacy */}
              <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-6">
                <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Federated Learning & Privacy</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Differential Privacy ε</label>
                    <input type="number" step="0.1" min="0.1" max="10" className="form-input w-full text-sm rounded-lg border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-800" value={dpEpsilon} onChange={(e) => setDpEpsilon(e.target.value)} />
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Lower values = stronger privacy guarantee (recommended: 0.5-2.0)</p>
                  </div>
                </div>
              </div>

              {/* Save */}
              <div className="flex justify-end gap-3">
                <button className="btn text-sm font-medium bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700/60 rounded-lg px-6 py-2 hover:border-gray-300">
                  Reset to Defaults
                </button>
                <button className="btn text-sm font-medium bg-violet-500 text-white rounded-lg px-6 py-2 hover:bg-violet-600" onClick={handleSave}>
                  {saved ? '✓ Saved' : 'Save Settings'}
                </button>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
