import { useState } from 'react';

export default function SidebarLinkGroup({ children, activecondition }) {
  const [open, setOpen] = useState(activecondition);

  const handleClick = () => {
    setOpen(!open);
  };

  return (
    <li className={`pl-4 pr-3 py-2 rounded-lg mb-0.5 last:mb-0 ${activecondition && 'bg-violet-50 dark:bg-violet-500/10'}`}>
      {children(handleClick, open)}
    </li>
  );
}
