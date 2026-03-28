import { useState, useEffect, useRef } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import SidebarLinkGroup from './SidebarLinkGroup';

export default function Sidebar({ sidebarOpen, setSidebarOpen, variant = 'default' }) {
  const location = useLocation();
  const { pathname } = location;

  const trigger = useRef(null);
  const sidebar = useRef(null);

  const storedSidebarExpanded = localStorage.getItem('sidebar-expanded');
  const [sidebarExpanded, setSidebarExpanded] = useState(storedSidebarExpanded === null ? false : storedSidebarExpanded === 'true');

  // Close on click outside
  useEffect(() => {
    const clickHandler = ({ target }) => {
      if (!sidebar.current || !trigger.current) return;
      if (!sidebarOpen || sidebar.current.contains(target) || trigger.current.contains(target)) return;
      setSidebarOpen(false);
    };
    document.addEventListener('click', clickHandler);
    return () => document.removeEventListener('click', clickHandler);
  });

  // Close on Escape
  useEffect(() => {
    const keyHandler = ({ keyCode }) => {
      if (!sidebarOpen || keyCode !== 27) return;
      setSidebarOpen(false);
    };
    document.addEventListener('keydown', keyHandler);
    return () => document.removeEventListener('keydown', keyHandler);
  });

  useEffect(() => {
    localStorage.setItem('sidebar-expanded', sidebarExpanded);
    if (sidebarExpanded) {
      document.querySelector('body').classList.add('sidebar-expanded');
    } else {
      document.querySelector('body').classList.remove('sidebar-expanded');
    }
  }, [sidebarExpanded]);

  return (
    <div id="sidebar" className={`flex lg:flex-shrink-0 ${variant === 'v2' ? 'border-r border-gray-200 dark:border-gray-700/60' : ''}`}>
      {/* Sidebar backdrop (mobile only) */}
      <div
        className={`fixed inset-0 bg-gray-900/30 z-40 lg:hidden lg:z-auto transition-opacity duration-200 ${sidebarOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
        aria-hidden="true"
      ></div>

      {/* Sidebar */}
      <div
        id="sidebar"
        ref={sidebar}
        className={`flex flex-col absolute z-40 left-0 top-0 lg:static lg:left-auto lg:top-auto lg:translate-x-0 h-[100dvh] overflow-y-scroll lg:overflow-y-auto no-scrollbar w-64 lg:w-20 lg:sidebar-expanded:!w-64 2xl:sidebar-expanded:!w-64 shrink-0 bg-white dark:bg-gray-800 p-4 transition-all duration-200 ease-in-out ${sidebarOpen ? 'translate-x-0' : '-translate-x-64'} ${variant === 'v2' ? '' : 'rounded-r-2xl shadow-xs'}`}
      >
        {/* Sidebar header */}
        <div className="flex justify-between mb-10 pr-3 sm:px-2">
          {/* Close button */}
          <button
            ref={trigger}
            className="lg:hidden text-gray-500 hover:text-gray-400"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-controls="sidebar"
            aria-expanded={sidebarOpen}
          >
            <span className="sr-only">Close sidebar</span>
            <svg className="w-6 h-6 fill-current" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M10.7 18.7l1.4-1.4L7.8 13H20v-2H7.8l4.3-4.3-1.4-1.4L4 12z" />
            </svg>
          </button>
          {/* Logo */}
          <NavLink end to="/" className="block">
            <div className="flex items-center">
              <svg className="w-8 h-8" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
                <rect fill="#7C3AED" width="32" height="32" rx="16" />
                <path d="M18.277.16C26.035 1.267 32 7.938 32 16c0 8.837-7.163 16-16 16a15.937 15.937 0 01-10.426-3.863L18.277.161z" fill="#14B8A6" />
                <path d="M7.404 2.503l18.339 26.19A15.93 15.93 0 0116 32C7.163 32 0 24.837 0 16 0 10.327 2.952 5.344 7.404 2.503z" fill="#7C3AED" opacity=".64" />
              </svg>
              <span className="text-lg font-bold ml-2 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200 text-gray-800 dark:text-gray-100 whitespace-nowrap">TissueShift</span>
            </div>
          </NavLink>
        </div>

        {/* Links */}
        <div className="space-y-8">
          {/* Overview group */}
          <div>
            <h3 className="text-xs uppercase text-gray-400 dark:text-gray-500 font-semibold pl-3">
              <span className="hidden lg:block lg:sidebar-expanded:hidden 2xl:hidden text-center w-6" aria-hidden="true">•••</span>
              <span className="lg:hidden lg:sidebar-expanded:block 2xl:block">Clinical</span>
            </h3>
            <ul className="mt-3">
              {/* Dashboard */}
              <li className={`pl-4 pr-3 py-2 rounded-lg mb-0.5 last:mb-0 ${pathname === '/' && 'bg-violet-50 dark:bg-violet-500/10'}`}>
                <NavLink
                  end
                  to="/"
                  className={`block text-gray-800 dark:text-gray-100 truncate transition ${pathname === '/' ? '' : 'hover:text-gray-900 dark:hover:text-white'}`}
                >
                  <div className="flex items-center">
                    <svg className={`shrink-0 fill-current ${pathname === '/' ? 'text-violet-500' : 'text-gray-400 dark:text-gray-500'}`} xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
                      <path d="M5.936.278A7.983 7.983 0 0 1 8 0a8 8 0 1 1-8 8c0-.722.104-1.413.278-2.064a1 1 0 1 1 1.932.516A5.99 5.99 0 0 0 2 8a6 6 0 1 0 6-6c-.53 0-1.045.076-1.548.21A1 1 0 1 1 5.936.278Z" />
                      <path d="M6.068 7.482A2.003 2.003 0 0 0 8 10a2 2 0 1 0-2-2c0 .17.02.336.068.482Zm-2.925-.149a4.003 4.003 0 0 1 5.524-3.19 1 1 0 0 0 .666-1.886 6.003 6.003 0 0 0-8.281 4.793 1 1 0 1 0 1.988.236 4 4 0 0 1 .103-.953Z" />
                    </svg>
                    <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">Dashboard</span>
                  </div>
                </NavLink>
              </li>

              {/* Patients */}
              <SidebarLinkGroup activecondition={pathname.includes('patient')}>
                {(handleClick, open) => (
                  <>
                    <a
                      href="#0"
                      className={`block text-gray-800 dark:text-gray-100 truncate transition ${pathname.includes('patient') ? '' : 'hover:text-gray-900 dark:hover:text-white'}`}
                      onClick={(e) => { e.preventDefault(); sidebarExpanded ? handleClick() : setSidebarExpanded(true); }}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center">
                          <svg className={`shrink-0 fill-current ${pathname.includes('patient') ? 'text-violet-500' : 'text-gray-400 dark:text-gray-500'}`} xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
                            <path d="M8 0a3 3 0 0 1 3 3 3 3 0 0 1-3 3 3 3 0 0 1-3-3 3 3 0 0 1 3-3Zm0 8c3.5 0 6 2 6 4v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-1c0-2 2.5-4 6-4Z" />
                          </svg>
                          <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">Patients</span>
                        </div>
                        <div className="flex shrink-0 ml-2">
                          <svg className={`w-3 h-3 shrink-0 ml-1 fill-current text-gray-400 dark:text-gray-500 ${open && 'rotate-180'}`} viewBox="0 0 12 12">
                            <path d="M5.9 11.4.5 6l1.4-1.4 4 4 4-4L11.3 6z" />
                          </svg>
                        </div>
                      </div>
                    </a>
                    <div className="lg:hidden lg:sidebar-expanded:block 2xl:block">
                      <ul className={`pl-8 mt-1 ${!open && 'hidden'}`}>
                        <li className="mb-1 last:mb-0">
                          <NavLink end to="/patients" className={({ isActive }) => 'block transition truncate ' + (isActive ? 'text-violet-500' : 'text-gray-500/90 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200')}>
                            <span className="text-sm font-medium lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">Patient List</span>
                          </NavLink>
                        </li>
                      </ul>
                    </div>
                  </>
                )}
              </SidebarLinkGroup>

              {/* Slide Analysis */}
              <li className={`pl-4 pr-3 py-2 rounded-lg mb-0.5 last:mb-0 ${pathname.includes('slide-analysis') && 'bg-violet-50 dark:bg-violet-500/10'}`}>
                <NavLink
                  end
                  to="/slide-analysis"
                  className={`block text-gray-800 dark:text-gray-100 truncate transition ${pathname.includes('slide-analysis') ? '' : 'hover:text-gray-900 dark:hover:text-white'}`}
                >
                  <div className="flex items-center">
                    <svg className={`shrink-0 fill-current ${pathname.includes('slide-analysis') ? 'text-violet-500' : 'text-gray-400 dark:text-gray-500'}`} xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
                      <path d="M7 0a7 7 0 0 1 7 7 1 1 0 0 1-1 1H8v5a1 1 0 0 1-1 1 7 7 0 0 1 0-14Zm4.5 9.5a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0Zm-1 3a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0Z" />
                    </svg>
                    <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">Slide Analysis</span>
                  </div>
                </NavLink>
              </li>
            </ul>
          </div>

          {/* Modeling group */}
          <div>
            <h3 className="text-xs uppercase text-gray-400 dark:text-gray-500 font-semibold pl-3">
              <span className="hidden lg:block lg:sidebar-expanded:hidden 2xl:hidden text-center w-6" aria-hidden="true">M</span>
              <span className="lg:hidden lg:sidebar-expanded:block 2xl:block">Modeling</span>
            </h3>
            <ul className="mt-3">
              {/* Digital Twin */}
              <li className={`pl-4 pr-3 py-2 rounded-lg mb-0.5 last:mb-0 ${pathname.includes('digital-twin') && 'bg-violet-50 dark:bg-violet-500/10'}`}>
                <NavLink
                  end
                  to="/digital-twin"
                  className={`block text-gray-800 dark:text-gray-100 truncate transition ${pathname.includes('digital-twin') ? '' : 'hover:text-gray-900 dark:hover:text-white'}`}
                >
                  <div className="flex items-center">
                    <svg className={`shrink-0 fill-current ${pathname.includes('digital-twin') ? 'text-violet-500' : 'text-gray-400 dark:text-gray-500'}`} xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
                      <path d="M5 1a1 1 0 0 1 1 1v3a1 1 0 0 1-2 0V2a1 1 0 0 1 1-1Zm6 0a1 1 0 0 1 1 1v3a1 1 0 0 1-2 0V2a1 1 0 0 1 1-1ZM2 8a1 1 0 0 1 1-1h3a1 1 0 0 1 0 2H3a1 1 0 0 1-1-1Zm8 0a1 1 0 0 1 1-1h3a1 1 0 1 1 0 2h-3a1 1 0 0 1-1-1Zm-5 3a1 1 0 0 1 1 1v3a1 1 0 0 1-2 0v-3a1 1 0 0 1 1-1Zm6 0a1 1 0 0 1 1 1v3a1 1 0 0 1-2 0v-3a1 1 0 0 1 1-1Z" />
                    </svg>
                    <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">Digital Twin</span>
                  </div>
                </NavLink>
              </li>

              {/* Treatment Comparison */}
              <li className={`pl-4 pr-3 py-2 rounded-lg mb-0.5 last:mb-0 ${pathname.includes('treatment-comparison') && 'bg-violet-50 dark:bg-violet-500/10'}`}>
                <NavLink
                  end
                  to="/treatment-comparison"
                  className={`block text-gray-800 dark:text-gray-100 truncate transition ${pathname.includes('treatment-comparison') ? '' : 'hover:text-gray-900 dark:hover:text-white'}`}
                >
                  <div className="flex items-center">
                    <svg className={`shrink-0 fill-current ${pathname.includes('treatment-comparison') ? 'text-violet-500' : 'text-gray-400 dark:text-gray-500'}`} xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
                      <path d="M3.5 2a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3ZM3 8.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 .5.5v5a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-5Zm6 0a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 .5.5v5a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-5ZM12.5 2a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z" />
                    </svg>
                    <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">Treatment Compare</span>
                  </div>
                </NavLink>
              </li>

              {/* Uncertainty */}
              <li className={`pl-4 pr-3 py-2 rounded-lg mb-0.5 last:mb-0 ${pathname.includes('uncertainty') && 'bg-violet-50 dark:bg-violet-500/10'}`}>
                <NavLink
                  end
                  to="/uncertainty"
                  className={`block text-gray-800 dark:text-gray-100 truncate transition ${pathname.includes('uncertainty') ? '' : 'hover:text-gray-900 dark:hover:text-white'}`}
                >
                  <div className="flex items-center">
                    <svg className={`shrink-0 fill-current ${pathname.includes('uncertainty') ? 'text-violet-500' : 'text-gray-400 dark:text-gray-500'}`} xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
                      <path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0Zm.93 12.588h-1.9V10.7h1.9v1.888Zm-.09-3.166H7.12l-.27-5.072h2.26l-.27 5.072Z" />
                    </svg>
                    <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">Uncertainty</span>
                  </div>
                </NavLink>
              </li>
            </ul>
          </div>

          {/* Analytics group */}
          <div>
            <h3 className="text-xs uppercase text-gray-400 dark:text-gray-500 font-semibold pl-3">
              <span className="hidden lg:block lg:sidebar-expanded:hidden 2xl:hidden text-center w-6" aria-hidden="true">•••</span>
              <span className="lg:hidden lg:sidebar-expanded:block 2xl:block">Analytics</span>
            </h3>
            <ul className="mt-3">
              {/* Cohort Analytics */}
              <li className={`pl-4 pr-3 py-2 rounded-lg mb-0.5 last:mb-0 ${pathname.includes('cohort') && 'bg-violet-50 dark:bg-violet-500/10'}`}>
                <NavLink
                  end
                  to="/cohort"
                  className={`block text-gray-800 dark:text-gray-100 truncate transition ${pathname.includes('cohort') ? '' : 'hover:text-gray-900 dark:hover:text-white'}`}
                >
                  <div className="flex items-center">
                    <svg className={`shrink-0 fill-current ${pathname.includes('cohort') ? 'text-violet-500' : 'text-gray-400 dark:text-gray-500'}`} xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
                      <path d="M1 3a1 1 0 0 1 1-1h3a1 1 0 1 1 0 2H2a1 1 0 0 1-1-1Zm0 5a1 1 0 0 1 1-1h7a1 1 0 0 1 0 2H2a1 1 0 0 1-1-1Zm0 5a1 1 0 0 1 1-1h11a1 1 0 1 1 0 2H2a1 1 0 0 1-1-1Z" />
                    </svg>
                    <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">Cohort Analytics</span>
                  </div>
                </NavLink>
              </li>

              {/* Biomarker Explorer */}
              <li className={`pl-4 pr-3 py-2 rounded-lg mb-0.5 last:mb-0 ${pathname.includes('biomarkers') && 'bg-violet-50 dark:bg-violet-500/10'}`}>
                <NavLink
                  end
                  to="/biomarkers"
                  className={`block text-gray-800 dark:text-gray-100 truncate transition ${pathname.includes('biomarkers') ? '' : 'hover:text-gray-900 dark:hover:text-white'}`}
                >
                  <div className="flex items-center">
                    <svg className={`shrink-0 fill-current ${pathname.includes('biomarkers') ? 'text-violet-500' : 'text-gray-400 dark:text-gray-500'}`} xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
                      <path d="M8 1a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 1Zm0 5a2 2 0 1 0 0 4 2 2 0 0 0 0-4Zm-4.5.5a4.5 4.5 0 1 1 9 0 4.5 4.5 0 0 1-9 0ZM8 12.5a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2a.5.5 0 0 1 .5-.5Z" />
                    </svg>
                    <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">Biomarkers</span>
                  </div>
                </NavLink>
              </li>

              {/* Knowledge Graph */}
              <li className={`pl-4 pr-3 py-2 rounded-lg mb-0.5 last:mb-0 ${pathname.includes('knowledge-graph') && 'bg-violet-50 dark:bg-violet-500/10'}`}>
                <NavLink
                  end
                  to="/knowledge-graph"
                  className={`block text-gray-800 dark:text-gray-100 truncate transition ${pathname.includes('knowledge-graph') ? '' : 'hover:text-gray-900 dark:hover:text-white'}`}
                >
                  <div className="flex items-center">
                    <svg className={`shrink-0 fill-current ${pathname.includes('knowledge-graph') ? 'text-violet-500' : 'text-gray-400 dark:text-gray-500'}`} xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
                      <path d="M2.5 2a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3Zm11 0a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3Zm-5.5 4.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3ZM2.5 11a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3Zm11 0a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3ZM4 3.5h3.5v1H4v-1Zm4.5 0H12v1H8.5v-1ZM4 12.5h3.5v-1H4v1Zm4.5 0H12v-1H8.5v1ZM3.25 5v2.75h1V5h-1ZM7.5 10v2h1v-2h-1Zm4.25-5v2.75h-1V5h1Z" />
                    </svg>
                    <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">Knowledge Graph</span>
                  </div>
                </NavLink>
              </li>
            </ul>
          </div>

          {/* System group */}
          <div>
            <h3 className="text-xs uppercase text-gray-400 dark:text-gray-500 font-semibold pl-3">
              <span className="hidden lg:block lg:sidebar-expanded:hidden 2xl:hidden text-center w-6" aria-hidden="true">•••</span>
              <span className="lg:hidden lg:sidebar-expanded:block 2xl:block">System</span>
            </h3>
            <ul className="mt-3">
              {/* Federated */}
              <li className={`pl-4 pr-3 py-2 rounded-lg mb-0.5 last:mb-0 ${pathname.includes('federated') && 'bg-violet-50 dark:bg-violet-500/10'}`}>
                <NavLink
                  end
                  to="/federated"
                  className={`block text-gray-800 dark:text-gray-100 truncate transition ${pathname.includes('federated') ? '' : 'hover:text-gray-900 dark:hover:text-white'}`}
                >
                  <div className="flex items-center">
                    <svg className={`shrink-0 fill-current ${pathname.includes('federated') ? 'text-violet-500' : 'text-gray-400 dark:text-gray-500'}`} xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
                      <path d="M3.5 0A1.5 1.5 0 0 0 2 1.5v1A1.5 1.5 0 0 0 3.5 4h1A1.5 1.5 0 0 0 6 2.5v-1A1.5 1.5 0 0 0 4.5 0h-1Zm7 0A1.5 1.5 0 0 0 9 1.5v1A1.5 1.5 0 0 0 10.5 4h1A1.5 1.5 0 0 0 13 2.5v-1A1.5 1.5 0 0 0 11.5 0h-1Zm-7 6A1.5 1.5 0 0 0 2 7.5v1A1.5 1.5 0 0 0 3.5 10h1A1.5 1.5 0 0 0 6 8.5v-1A1.5 1.5 0 0 0 4.5 6h-1Zm7 0A1.5 1.5 0 0 0 9 7.5v1A1.5 1.5 0 0 0 10.5 10h1A1.5 1.5 0 0 0 13 8.5v-1A1.5 1.5 0 0 0 11.5 6h-1Zm-3.5 6a1.5 1.5 0 0 0-1.5 1.5v1A1.5 1.5 0 0 0 7 16h2a1.5 1.5 0 0 0 1.5-1.5v-1A1.5 1.5 0 0 0 9 12H7Z" />
                    </svg>
                    <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">Federated</span>
                  </div>
                </NavLink>
              </li>

              {/* Reports */}
              <li className={`pl-4 pr-3 py-2 rounded-lg mb-0.5 last:mb-0 ${pathname.includes('reports') && 'bg-violet-50 dark:bg-violet-500/10'}`}>
                <NavLink
                  end
                  to="/reports"
                  className={`block text-gray-800 dark:text-gray-100 truncate transition ${pathname.includes('reports') ? '' : 'hover:text-gray-900 dark:hover:text-white'}`}
                >
                  <div className="flex items-center">
                    <svg className={`shrink-0 fill-current ${pathname.includes('reports') ? 'text-violet-500' : 'text-gray-400 dark:text-gray-500'}`} xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
                      <path d="M3 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V4.5L10.5 0H3Zm7 1.5L13.5 5H11a1 1 0 0 1-1-1V1.5ZM4 7h8v1H4V7Zm0 3h8v1H4v-1Zm0 3h5v1H4v-1Z" />
                    </svg>
                    <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">Reports</span>
                  </div>
                </NavLink>
              </li>

              {/* Settings */}
              <li className={`pl-4 pr-3 py-2 rounded-lg mb-0.5 last:mb-0 ${pathname.includes('settings') && 'bg-violet-50 dark:bg-violet-500/10'}`}>
                <NavLink
                  end
                  to="/settings"
                  className={`block text-gray-800 dark:text-gray-100 truncate transition ${pathname.includes('settings') ? '' : 'hover:text-gray-900 dark:hover:text-white'}`}
                >
                  <div className="flex items-center">
                    <svg className={`shrink-0 fill-current ${pathname.includes('settings') ? 'text-violet-500' : 'text-gray-400 dark:text-gray-500'}`} xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
                      <path d="M10.5 1a3.502 3.502 0 0 1 3.355 2.5H15a1 1 0 1 1 0 2h-1.145a3.502 3.502 0 0 1-6.71 0H1a1 1 0 0 1 0-2h6.145A3.502 3.502 0 0 1 10.5 1ZM9 3.5a1.5 1.5 0 1 0 3 0 1.5 1.5 0 0 0-3 0ZM5.5 9a3.502 3.502 0 0 1 3.355 2.5H15a1 1 0 1 1 0 2H8.855a3.502 3.502 0 0 1-6.71 0H1a1 1 0 1 1 0-2h1.145A3.502 3.502 0 0 1 5.5 9ZM4 11.5a1.5 1.5 0 1 0 3 0 1.5 1.5 0 0 0-3 0Z" />
                    </svg>
                    <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">Settings</span>
                  </div>
                </NavLink>
              </li>
            </ul>
          </div>

          {/* Advanced group */}
          <div>
            <h3 className="text-xs uppercase text-gray-400 dark:text-gray-500 font-semibold pl-3">
              <span className="hidden lg:block lg:sidebar-expanded:hidden 2xl:hidden text-center w-6" aria-hidden="true">•••</span>
              <span className="lg:hidden lg:sidebar-expanded:block 2xl:block">Advanced</span>
            </h3>
            <ul className="mt-3">
              {[
                { to: '/command-center', label: 'Command Center', d: 'M1 2h5v5H1zm8 0h6v5H9zM1 9h5v5H1zm8 0h6v5H9z' },
                { to: '/tumor-microenvironment', label: 'Tumor Micro-env', d: 'M5 1a3 3 0 1 0 0 6 3 3 0 0 0 0-6zm7 4a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm-5 6a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z' },
                { to: '/genomic-constellation', label: 'Genomic Map', d: 'M8 1a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM3 6a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm10 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM6 12a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm4 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4z' },
                { to: '/clinical-workflow', label: 'Clinical Pipeline', d: 'M1 3h4l2 2-2 2H1V3zm5 4h4l2 2-2 2H6V7zm5 3h3v3h-3v-3z' },
                { to: '/multi-omics', label: 'Multi-Omics Hub', d: 'M8 5a2 2 0 1 1 0-4 2 2 0 0 1 0 4zM3 10a2 2 0 1 1 0-4 2 2 0 0 1 0 4zm10 0a2 2 0 1 1 0-4 2 2 0 0 1 0 4zM8 15a2 2 0 1 1 0-4 2 2 0 0 1 0 4z' },
              ].map(link => (
                <li key={link.to} className={`pl-4 pr-3 py-2 rounded-lg mb-0.5 last:mb-0 ${pathname === link.to && 'bg-violet-50 dark:bg-violet-500/10'}`}>
                  <NavLink end to={link.to} className={`block text-gray-800 dark:text-gray-100 truncate transition ${pathname === link.to ? '' : 'hover:text-gray-900 dark:hover:text-white'}`}>
                    <div className="flex items-center">
                      <svg className={`shrink-0 fill-current ${pathname === link.to ? 'text-violet-500' : 'text-gray-400 dark:text-gray-500'}`} xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16"><path d={link.d} /></svg>
                      <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">{link.label}</span>
                    </div>
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>

          {/* Deep Learning group */}
          <div>
            <h3 className="text-xs uppercase text-gray-400 dark:text-gray-500 font-semibold pl-3">
              <span className="hidden lg:block lg:sidebar-expanded:hidden 2xl:hidden text-center w-6" aria-hidden="true">DL</span>
              <span className="lg:hidden lg:sidebar-expanded:block 2xl:block">Deep Learning</span>
            </h3>
            <ul className="mt-3">
              {[
                { to: '/3d-reconstruction', label: '3D Reconstruction', d: 'M8 1L1 5v6l7 4 7-4V5L8 1zm0 2.2L12.8 6 8 8.8 3.2 6 8 3.2zM2.5 6.7L7.5 9.5v4.3L2.5 11V6.7zm11 0V11l-5 2.8V9.5l5-2.8z' },
                { to: '/virtual-staining', label: 'Virtual Staining', d: 'M10 1a2 2 0 0 0-2 2v1H6a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2V3a1 1 0 1 1 2 0v1h1V3a2 2 0 0 0-3-2zM6 6h4v6H6V6z' },
                { to: '/cell-graph', label: 'Cell Graph Network', d: 'M3 3a2 2 0 1 1 2.83 1.83l2.34 2.34a2 2 0 1 1-.7.7L5.12 5.53A2 2 0 0 1 3 3zm8 0a2 2 0 1 1-1.17 3.63l-1.46 1.74a2 2 0 1 1-.76-.64l1.46-1.74A2 2 0 0 1 11 3z' },
                { to: '/survival-prediction', label: 'Survival Analysis', d: 'M2 13V3h1v8.5l3-2 3 1.5 3-2V3h1v10H2zm4-3.5l-3 2V5l3-1 3 1.5 3-2v5l-3 2-3-1.5z' },
                { to: '/attention-heatmaps', label: 'Attention Maps', d: 'M1 1h4v4H1V1zm5 0h4v4H6V1zm5 0h4v4h-4V1zM1 6h4v4H1V6zm5 0h4v4H6V6zm5 0h4v4h-4V6zM1 11h4v4H1v-4zm5 0h4v4H6v-4zm5 0h4v4h-4v-4z' },
              ].map(link => (
                <li key={link.to} className={`pl-4 pr-3 py-2 rounded-lg mb-0.5 last:mb-0 ${pathname === link.to && 'bg-violet-50 dark:bg-violet-500/10'}`}>
                  <NavLink end to={link.to} className={`block text-gray-800 dark:text-gray-100 truncate transition ${pathname === link.to ? '' : 'hover:text-gray-900 dark:hover:text-white'}`}>
                    <div className="flex items-center">
                      <svg className={`shrink-0 fill-current ${pathname === link.to ? 'text-violet-500' : 'text-gray-400 dark:text-gray-500'}`} xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16"><path d={link.d} /></svg>
                      <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">{link.label}</span>
                    </div>
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>

          {/* Computer Vision group */}
          <div>
            <h3 className="text-xs uppercase text-gray-400 dark:text-gray-500 font-semibold pl-3">
              <span className="hidden lg:block lg:sidebar-expanded:hidden 2xl:hidden text-center w-6" aria-hidden="true">•••</span>
              <span className="lg:hidden lg:sidebar-expanded:block 2xl:block">Computer Vision</span>
            </h3>
            <ul className="mt-3">
              {[
                { to: '/pathology-lab', label: 'Pathology Lab', d: 'M9 1H7v3H5v2h2v3l-3 4v2h8v-2l-3-4V6h2V4H9V1z' },
                { to: '/spatial-transcriptomics', label: 'Spatial Atlas', d: 'M1 1h3v3H1zm5 0h3v3H6zm5 0h3v3h-3zM1 6h3v3H1zm5 0h3v3H6zm5 0h3v3h-3zM1 11h3v3H1zm5 0h3v3H6zm5 0h3v3h-3z' },
                { to: '/patient-wellness', label: 'Patient Wellness', d: 'M8 2.748C6.5.5 1 1.5 1 5c0 4 7 9.5 7 9.5s7-5.5 7-9.5c0-3.5-5.5-4.5-7-2.252z' },
                { to: '/rehab-tracker', label: 'Rehab Tracker', d: 'M3 5a1 1 0 0 0-1 1v4a1 1 0 0 0 2 0V9h8v1a1 1 0 0 0 2 0V6a1 1 0 0 0-2 0v1H4V6a1 1 0 0 0-1-1z' },
              ].map(link => (
                <li key={link.to} className={`pl-4 pr-3 py-2 rounded-lg mb-0.5 last:mb-0 ${pathname === link.to && 'bg-violet-50 dark:bg-violet-500/10'}`}>
                  <NavLink end to={link.to} className={`block text-gray-800 dark:text-gray-100 truncate transition ${pathname === link.to ? '' : 'hover:text-gray-900 dark:hover:text-white'}`}>
                    <div className="flex items-center">
                      <svg className={`shrink-0 fill-current ${pathname === link.to ? 'text-violet-500' : 'text-gray-400 dark:text-gray-500'}`} xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16"><path d={link.d} /></svg>
                      <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">{link.label}</span>
                    </div>
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>

          {/* Decision Support group */}
          <div>
            <h3 className="text-xs uppercase text-gray-400 dark:text-gray-500 font-semibold pl-3">
              <span className="hidden lg:block lg:sidebar-expanded:hidden 2xl:hidden text-center w-6" aria-hidden="true">•••</span>
              <span className="lg:hidden lg:sidebar-expanded:block 2xl:block">Decision Support</span>
            </h3>
            <ul className="mt-3">
              {[
                { to: '/tumor-board', label: 'Tumor Board', d: 'M3 3a2 2 0 1 0 4 0 2 2 0 0 0-4 0zm6 0a2 2 0 1 0 4 0 2 2 0 0 0-4 0zM1 12c0-2 1.8-3.5 4-3.5h2c.4 0 .8.1 1.1.2A4.5 4.5 0 0 0 7 11v2H1zm14 0H9v-1c0-2 1.8-3.5 4-3.5h1c2.2 0 4 1.5 4 3.5v1h-3z' },
                { to: '/trial-matcher', label: 'Trial Matcher', d: 'M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1zm0 2a5 5 0 1 1 0 10A5 5 0 0 1 8 3zm0 2a3 3 0 1 0 0 6 3 3 0 0 0 0-6zm0 2a1 1 0 1 1 0 2 1 1 0 0 1 0-2z' },
                { to: '/drug-mechanisms', label: 'Drug Mechanisms', d: 'M6 1a2 2 0 0 0-2 2v2h8V3a2 2 0 0 0-2-2H6zM4 6v5a4 4 0 0 0 8 0V6H4z' },
                { to: '/guideline-navigator', label: 'NCCN Navigator', d: 'M3 0a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V1a1 1 0 0 0-1-1H3zm2 3h6v1H5V3zm0 3h6v1H5V6zm0 3h4v1H5V9z' },
                { to: '/population-health', label: 'Population Health', d: 'M1 14V2h1v12h13v1H1zm3-8h2v6H4V6zm3-2h2v8H7V4zm3 4h2v4h-2V8zm3-3h2v7h-2V5z' },
              ].map(link => (
                <li key={link.to} className={`pl-4 pr-3 py-2 rounded-lg mb-0.5 last:mb-0 ${pathname === link.to && 'bg-violet-50 dark:bg-violet-500/10'}`}>
                  <NavLink end to={link.to} className={`block text-gray-800 dark:text-gray-100 truncate transition ${pathname === link.to ? '' : 'hover:text-gray-900 dark:hover:text-white'}`}>
                    <div className="flex items-center">
                      <svg className={`shrink-0 fill-current ${pathname === link.to ? 'text-violet-500' : 'text-gray-400 dark:text-gray-500'}`} xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16"><path d={link.d} /></svg>
                      <span className="text-sm font-medium ml-4 lg:opacity-0 lg:sidebar-expanded:opacity-100 2xl:opacity-100 duration-200">{link.label}</span>
                    </div>
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Expand / collapse button */}
        <div className="pt-3 hidden lg:inline-flex 2xl:hidden justify-end mt-auto">
          <div className="w-12 pl-4 pr-3 py-2">
            <button className="text-gray-400 hover:text-gray-500 dark:text-gray-500 dark:hover:text-gray-400" onClick={() => setSidebarExpanded(!sidebarExpanded)}>
              <span className="sr-only">Expand / collapse sidebar</span>
              <svg className={`shrink-0 fill-current text-gray-400 dark:text-gray-500 sidebar-expanded:rotate-180`} xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
                <path d="M6.6 13.4 5.2 12l4-4-4-4 1.4-1.4L12 8z" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
