import { subtypeColors } from '../charts/ChartjsConfig';
import { classNames } from '../utils/Utils';

const labels = {
  luminal_a: 'Luminal A',
  luminal_b: 'Luminal B',
  her2_enriched: 'HER2+',
  basal: 'Basal-like',
  normal_like: 'Normal-like',
  claudin_low: 'Claudin-low',
  dcis: 'DCIS',
};

export default function SubtypeBadge({ subtype, size = 'md', className = '' }) {
  const color = subtypeColors[subtype] || '#94a3b8';
  const label = labels[subtype] || subtype;
  const sizeClass = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-2.5 py-1';

  return (
    <span
      className={classNames('inline-flex items-center font-semibold rounded-full whitespace-nowrap', sizeClass, className)}
      style={{ backgroundColor: `${color}20`, color }}
    >
      <span className="w-2 h-2 rounded-full mr-1.5" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}
