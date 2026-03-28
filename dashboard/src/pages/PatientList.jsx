import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import RiskBadge from '../components/RiskBadge';
import SubtypeBadge from '../components/SubtypeBadge';
import ConfidenceBar from '../components/ConfidenceBar';
import DropdownFilter from '../components/DropdownFilter';

const mockPatients = [
  { id: 'P-2847', age: 54, subtype: 'luminal_a', risk: 'low', confidence: 0.97, stage: 'IIA', date: '2024-01-15', er: '+', pr: '+', her2: '-' },
  { id: 'P-2846', age: 67, subtype: 'basal', risk: 'high', confidence: 0.94, stage: 'IIIB', date: '2024-01-15', er: '-', pr: '-', her2: '-' },
  { id: 'P-2845', age: 48, subtype: 'her2_enriched', risk: 'moderate', confidence: 0.88, stage: 'IIB', date: '2024-01-14', er: '-', pr: '-', her2: '+' },
  { id: 'P-2844', age: 61, subtype: 'luminal_b', risk: 'moderate', confidence: 0.91, stage: 'IIA', date: '2024-01-14', er: '+', pr: '+', her2: '+' },
  { id: 'P-2843', age: 39, subtype: 'claudin_low', risk: 'high', confidence: 0.86, stage: 'IIIA', date: '2024-01-13', er: '-', pr: '-', her2: '-' },
  { id: 'P-2842', age: 72, subtype: 'luminal_a', risk: 'low', confidence: 0.95, stage: 'IA', date: '2024-01-13', er: '+', pr: '+', her2: '-' },
  { id: 'P-2841', age: 55, subtype: 'normal_like', risk: 'low', confidence: 0.82, stage: 'IB', date: '2024-01-12', er: '+', pr: '+', her2: '-' },
  { id: 'P-2840', age: 44, subtype: 'her2_enriched', risk: 'high', confidence: 0.93, stage: 'IIIC', date: '2024-01-12', er: '-', pr: '-', her2: '+' },
  { id: 'P-2839', age: 63, subtype: 'dcis', risk: 'low', confidence: 0.96, stage: '0', date: '2024-01-11', er: '+', pr: '+', her2: '-' },
  { id: 'P-2838', age: 58, subtype: 'luminal_b', risk: 'moderate', confidence: 0.89, stage: 'IIB', date: '2024-01-11', er: '+', pr: '-', her2: '+' },
];

export default function PatientList() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const [subtypeFilter, setSubtypeFilter] = useState('all');
  const navigate = useNavigate();

  const filtered = mockPatients.filter((p) => {
    if (search && !p.id.toLowerCase().includes(search.toLowerCase())) return false;
    if (riskFilter !== 'all' && p.risk !== riskFilter) return false;
    if (subtypeFilter !== 'all' && p.subtype !== subtypeFilter) return false;
    return true;
  });

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
            <div className="sm:flex sm:justify-between sm:items-center mb-8">
              <div>
                <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold">Patients</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{filtered.length} patients found</p>
              </div>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap gap-3 mb-6">
              <div className="flex-1 min-w-[200px] max-w-sm">
                <input
                  type="text"
                  className="form-input w-full text-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700/60 rounded-lg placeholder-gray-400"
                  placeholder="Search by patient ID..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <DropdownFilter
                id="risk-filter"
                options={[{ value: 'all', label: 'All Risk Levels' }, { value: 'low', label: 'Low Risk' }, { value: 'moderate', label: 'Moderate Risk' }, { value: 'high', label: 'High Risk' }]}
                value={riskFilter}
                onChange={setRiskFilter}
              />
              <DropdownFilter
                id="subtype-filter"
                options={[{ value: 'all', label: 'All Subtypes' }, { value: 'luminal_a', label: 'Luminal A' }, { value: 'luminal_b', label: 'Luminal B' }, { value: 'her2_enriched', label: 'HER2+' }, { value: 'basal', label: 'Basal-like' }, { value: 'normal_like', label: 'Normal-like' }, { value: 'claudin_low', label: 'Claudin-low' }, { value: 'dcis', label: 'DCIS' }]}
                value={subtypeFilter}
                onChange={setSubtypeFilter}
              />
            </div>

            {/* Table */}
            <div className="bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="table-auto w-full text-sm">
                  <thead className="text-xs uppercase text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-900/20 border-b border-gray-200 dark:border-gray-700/60">
                    <tr>
                      <th className="px-4 py-3 text-left font-semibold">Patient ID</th>
                      <th className="px-4 py-3 text-left font-semibold">Age</th>
                      <th className="px-4 py-3 text-left font-semibold">Stage</th>
                      <th className="px-4 py-3 text-left font-semibold">Subtype</th>
                      <th className="px-4 py-3 text-left font-semibold">Receptor</th>
                      <th className="px-4 py-3 text-left font-semibold">Risk</th>
                      <th className="px-4 py-3 text-left font-semibold">Confidence</th>
                      <th className="px-4 py-3 text-left font-semibold">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700/60">
                    {filtered.map((p) => (
                      <tr key={p.id} className="text-gray-700 dark:text-gray-300 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/20" onClick={() => navigate(`/patients/${p.id}`)}>
                        <td className="px-4 py-3 font-medium text-violet-500">{p.id}</td>
                        <td className="px-4 py-3">{p.age}</td>
                        <td className="px-4 py-3">{p.stage}</td>
                        <td className="px-4 py-3"><SubtypeBadge subtype={p.subtype} size="sm" /></td>
                        <td className="px-4 py-3 text-xs font-mono">ER{p.er} PR{p.pr} HER2{p.her2}</td>
                        <td className="px-4 py-3"><RiskBadge level={p.risk} size="sm" /></td>
                        <td className="px-4 py-3 w-32"><ConfidenceBar score={p.confidence} height="h-1.5" /></td>
                        <td className="px-4 py-3 text-gray-500 dark:text-gray-400">{p.date}</td>
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
