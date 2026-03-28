import { Link } from 'react-router-dom';
import RiskBadge from '../../components/RiskBadge';
import SubtypeBadge from '../../components/SubtypeBadge';
import ConfidenceBar from '../../components/ConfidenceBar';
import { classNames } from '../../utils/Utils';

const recentPatients = [
  { id: 'P-2847', name: 'Patient 2847', subtype: 'luminal_a', risk: 'low', confidence: 0.97, date: '2024-01-15' },
  { id: 'P-2846', name: 'Patient 2846', subtype: 'basal', risk: 'high', confidence: 0.94, date: '2024-01-15' },
  { id: 'P-2845', name: 'Patient 2845', subtype: 'her2_enriched', risk: 'moderate', confidence: 0.88, date: '2024-01-14' },
  { id: 'P-2844', name: 'Patient 2844', subtype: 'luminal_b', risk: 'moderate', confidence: 0.91, date: '2024-01-14' },
  { id: 'P-2843', name: 'Patient 2843', subtype: 'claudin_low', risk: 'high', confidence: 0.86, date: '2024-01-13' },
];

export default function RecentPatientsCard({ className = '' }) {
  return (
    <div className={classNames('bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60', className)}>
      <header className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-700/60">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Recent Patients</h2>
        <Link to="/patients" className="text-sm font-medium text-violet-500 hover:text-violet-600">View All →</Link>
      </header>
      <div className="overflow-x-auto">
        <table className="table-auto w-full text-sm">
          <thead className="text-xs uppercase text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-900/20">
            <tr>
              <th className="px-4 py-3 text-left font-semibold">ID</th>
              <th className="px-4 py-3 text-left font-semibold">Subtype</th>
              <th className="px-4 py-3 text-left font-semibold">Risk</th>
              <th className="px-4 py-3 text-left font-semibold">Confidence</th>
              <th className="px-4 py-3 text-left font-semibold">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700/60">
            {recentPatients.map((p) => (
              <tr key={p.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/20">
                <td className="px-4 py-3">
                  <Link to={`/patients/${p.id}`} className="font-medium text-violet-500 hover:text-violet-600">{p.id}</Link>
                </td>
                <td className="px-4 py-3"><SubtypeBadge subtype={p.subtype} size="sm" /></td>
                <td className="px-4 py-3"><RiskBadge level={p.risk} size="sm" /></td>
                <td className="px-4 py-3 w-36"><ConfidenceBar score={p.confidence} height="h-1.5" /></td>
                <td className="px-4 py-3 text-gray-500 dark:text-gray-400">{p.date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
