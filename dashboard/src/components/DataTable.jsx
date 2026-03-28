import { classNames } from '../utils/Utils';

export default function DataTable({ columns, rows, onRowClick, emptyMessage = 'No data available', className = '' }) {
  return (
    <div className={classNames('bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 overflow-hidden', className)}>
      <div className="overflow-x-auto">
        <table className="table-auto w-full text-sm">
          <thead className="text-xs uppercase text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-900/20 border-b border-gray-200 dark:border-gray-700/60">
            <tr>
              {columns.map((col, i) => (
                <th key={i} className="px-4 py-3 whitespace-nowrap font-semibold text-left">
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700/60">
            {rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-8 text-center text-gray-400 dark:text-gray-500">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              rows.map((row, ri) => (
                <tr
                  key={row.id || ri}
                  className={classNames(
                    'text-gray-700 dark:text-gray-300',
                    onRowClick ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/20' : '',
                  )}
                  onClick={() => onRowClick && onRowClick(row)}
                >
                  {columns.map((col, ci) => (
                    <td key={ci} className="px-4 py-3 whitespace-nowrap">
                      {col.render ? col.render(row) : row[col.accessor]}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
