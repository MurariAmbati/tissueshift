import { classNames } from '../utils/Utils';

export default function DropdownFilter({ id, label, options, value, onChange, className = '' }) {
  return (
    <div className={classNames('relative', className)}>
      {label && <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1" htmlFor={id}>{label}</label>}
      <select
        id={id}
        className="form-select w-full text-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700/60 rounded-lg text-gray-600 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600 focus:border-violet-300 dark:focus:border-violet-500"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((opt) => (
          <option key={typeof opt === 'string' ? opt : opt.value} value={typeof opt === 'string' ? opt : opt.value}>
            {typeof opt === 'string' ? opt : opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}
