import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '../utils/ThemeContext';
import Transition from '../utils/Transition';

export default function Header({ sidebarOpen, setSidebarOpen, variant = 'default' }) {
  const [searchModalOpen, setSearchModalOpen] = useState(false);
  const { currentTheme, changeCurrentTheme } = useTheme();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  const userMenuRef = useRef(null);
  const notificationsRef = useRef(null);

  // Close user menu on click outside
  useEffect(() => {
    const handler = ({ target }) => {
      if (!userMenuRef.current) return;
      if (!userMenuOpen || userMenuRef.current.contains(target)) return;
      setUserMenuOpen(false);
    };
    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  });

  // Close notifications on click outside
  useEffect(() => {
    const handler = ({ target }) => {
      if (!notificationsRef.current) return;
      if (!notificationsOpen || notificationsRef.current.contains(target)) return;
      setNotificationsOpen(false);
    };
    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  });

  return (
    <header className={`sticky top-0 before:absolute before:inset-0 before:backdrop-blur-md before:bg-white/90 dark:before:bg-gray-800/90 before:-z-10 z-30 ${variant === 'v2' || variant === 'v3' ? 'before:bg-white after:absolute after:h-px after:inset-x-0 after:top-full after:bg-gray-200 dark:after:bg-gray-700/60 after:-z-10' : 'shadow-xs'}`}>
      <div className="px-4 sm:px-6 lg:px-8">
        <div className={`flex items-center justify-between h-16 ${variant === 'v2' || variant === 'v3' ? '' : 'border-b border-gray-200 dark:border-gray-700/60'}`}>
          {/* Left side */}
          <div className="flex">
            {/* Hamburger button */}
            <button
              className="text-gray-500 hover:text-gray-600 dark:hover:text-gray-400 lg:hidden"
              aria-controls="sidebar"
              aria-expanded={sidebarOpen}
              onClick={(e) => { e.stopPropagation(); setSidebarOpen(!sidebarOpen); }}
            >
              <span className="sr-only">Open sidebar</span>
              <svg className="w-6 h-6 fill-current" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <rect x="4" y="5" width="16" height="2" />
                <rect x="4" y="11" width="16" height="2" />
                <rect x="4" y="17" width="16" height="2" />
              </svg>
            </button>
          </div>

          {/* Right side */}
          <div className="flex items-center space-x-3">
            {/* Search button */}
            <div>
              <button
                className={`w-8 h-8 flex items-center justify-center hover:bg-gray-100 lg:hover:bg-gray-200 dark:hover:bg-gray-700/50 dark:lg:hover:bg-gray-800 rounded-full ${searchModalOpen && 'bg-gray-200 dark:bg-gray-700/60'}`}
                onClick={() => setSearchModalOpen(true)}
              >
                <span className="sr-only">Search</span>
                <svg className="fill-current text-gray-500/80 dark:text-gray-400/80" width="16" height="16" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
                  <path d="M7 14c-3.86 0-7-3.14-7-7s3.14-7 7-7 7 3.14 7 7-3.14 7-7 7ZM7 2C4.243 2 2 4.243 2 7s2.243 5 5 5 5-2.243 5-5-2.243-5-5-5Z" />
                  <path d="m13.314 11.9 2.393 2.393a.999.999 0 1 1-1.414 1.414L11.9 13.314a8.019 8.019 0 0 0 1.414-1.414Z" />
                </svg>
              </button>
            </div>

            {/* Notifications button */}
            <div className="relative inline-flex" ref={notificationsRef}>
              <button
                className={`w-8 h-8 flex items-center justify-center hover:bg-gray-100 lg:hover:bg-gray-200 dark:hover:bg-gray-700/50 dark:lg:hover:bg-gray-800 rounded-full ${notificationsOpen && 'bg-gray-200 dark:bg-gray-700/60'}`}
                onClick={() => setNotificationsOpen(!notificationsOpen)}
              >
                <span className="sr-only">Notifications</span>
                <svg className="fill-current text-gray-500/80 dark:text-gray-400/80" width="16" height="16" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
                  <path d="M6.5 0C2.91 0 0 2.462 0 5.5c0 1.075.37 2.074 1 2.922V12l2.699-1.542A7.454 7.454 0 0 0 6.5 11c3.59 0 6.5-2.462 6.5-5.5S10.09 0 6.5 0Z" />
                  <path d="M16 9.5c0-.987-.429-1.897-1.147-2.639C14.124 10.348 10.66 13 6.5 13c-.103 0-.202-.018-.305-.021C7.231 13.617 8.556 14 10 14c.449 0 .886-.04 1.307-.11L14 16v-3.435c1.244-.95 2-2.298 2-3.814V9.5Z" />
                </svg>
                <div className="absolute top-0 right-0 w-2.5 h-2.5 bg-rose-500 border-2 border-white dark:border-gray-800 rounded-full"></div>
              </button>
              {/* Dropdown */}
              <Transition
                className="origin-top-right z-10 absolute top-full -mr-48 sm:mr-0 min-w-[20rem] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700/60 py-1.5 rounded-lg shadow-lg overflow-hidden mt-1 right-0"
                show={notificationsOpen}
                enter="transition ease-out duration-200 transform"
                enterStart="opacity-0 -translate-y-2"
                enterEnd="opacity-100 translate-y-0"
                leave="transition ease-out duration-200"
                leaveStart="opacity-100"
                leaveEnd="opacity-0"
              >
                <div className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase pt-1.5 pb-2 px-4">Notifications</div>
                <ul>
                  <li className="border-b border-gray-200 dark:border-gray-700/60 last:border-0">
                    <Link className="block py-2 px-4 hover:bg-gray-50 dark:hover:bg-gray-700/20" to="#0" onClick={() => setNotificationsOpen(false)}>
                      <span className="block text-sm mb-2">
                        <span className="font-medium text-gray-800 dark:text-gray-100">New analysis complete</span> — Slide WSI-0047 subtype prediction ready.
                      </span>
                      <span className="block text-xs font-medium text-gray-400 dark:text-gray-500">2 min ago</span>
                    </Link>
                  </li>
                  <li className="border-b border-gray-200 dark:border-gray-700/60 last:border-0">
                    <Link className="block py-2 px-4 hover:bg-gray-50 dark:hover:bg-gray-700/20" to="#0" onClick={() => setNotificationsOpen(false)}>
                      <span className="block text-sm mb-2">
                        <span className="font-medium text-gray-800 dark:text-gray-100">Federated round #42</span> — Global model aggregation finished (3 sites).
                      </span>
                      <span className="block text-xs font-medium text-gray-400 dark:text-gray-500">18 min ago</span>
                    </Link>
                  </li>
                  <li className="border-b border-gray-200 dark:border-gray-700/60 last:border-0">
                    <Link className="block py-2 px-4 hover:bg-gray-50 dark:hover:bg-gray-700/20" to="#0" onClick={() => setNotificationsOpen(false)}>
                      <span className="block text-sm mb-2">
                        <span className="font-medium text-gray-800 dark:text-gray-100">High-risk alert</span> — Patient P-1034 flagged with basal-like subtype (confidence 0.94).
                      </span>
                      <span className="block text-xs font-medium text-gray-400 dark:text-gray-500">1 hr ago</span>
                    </Link>
                  </li>
                </ul>
              </Transition>
            </div>

            {/* Dark mode toggle */}
            <div>
              <input type="checkbox" name="light-switch" id="light-switch" className="light-switch sr-only" checked={currentTheme === 'dark'} onChange={() => changeCurrentTheme(currentTheme === 'dark' ? 'light' : 'dark')} />
              <label className="flex items-center justify-center cursor-pointer w-8 h-8 hover:bg-gray-100 lg:hover:bg-gray-200 dark:hover:bg-gray-700/50 dark:lg:hover:bg-gray-800 rounded-full" htmlFor="light-switch">
                <svg className="dark:hidden fill-current text-gray-500/80" width="16" height="16" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
                  <path d="M8 0Q8.2 0 8.4.1a.7.7 0 01.5.6v1.2a.7.7 0 01-.6.7A5.2 5.2 0 003 7.7 5.2 5.2 0 008 13a5.2 5.2 0 004.3-2.3.6.6 0 01.5-.3.7.7 0 01.7.5 6.4 6.4 0 01-5 3.8A6.4 6.4 0 011.5 9 6.4 6.4 0 018 0Z" />
                </svg>
                <svg className="hidden dark:block fill-current text-gray-400/80" width="16" height="16" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
                  <path d="M8 4a4 4 0 100 8 4 4 0 000-8zM7.3.3a.7.7 0 011.4 0v1.4a.7.7 0 01-1.4 0V.3zm0 14a.7.7 0 011.4 0v1.4a.7.7 0 01-1.4 0V14.3zM2.1 2.8a.7.7 0 011 0l1 1a.7.7 0 01-1 1l-1-1a.7.7 0 010-1zm9.8 9.8a.7.7 0 011 0l1 1a.7.7 0 01-1 1l-1-1a.7.7 0 010-1zM0 8.7a.7.7 0 01.3-.7h1.4a.7.7 0 010 1.4H.3a.7.7 0 01-.3-.7zm14 0a.7.7 0 01.3-.7h1.4a.7.7 0 010 1.4h-1.4a.7.7 0 01-.3-.7zM2.8 13.9a.7.7 0 010-1l1-1a.7.7 0 011 1l-1 1a.7.7 0 01-1 0zm9.8-9.8a.7.7 0 010-1l1-1a.7.7 0 011 1l-1 1a.7.7 0 01-1 0z" />
                </svg>
                <span className="sr-only">Switch to light / dark version</span>
              </label>
            </div>

            {/* Divider */}
            <hr className="w-px h-6 bg-gray-200 dark:bg-gray-700/60 border-none" />

            {/* User button */}
            <div className="relative inline-flex" ref={userMenuRef}>
              <button
                className="inline-flex justify-center items-center group"
                aria-haspopup="true"
                onClick={() => setUserMenuOpen(!userMenuOpen)}
              >
                <div className="flex items-center truncate">
                  <span className="truncate ml-2 text-sm font-medium text-gray-600 dark:text-gray-100 group-hover:text-gray-800 dark:group-hover:text-white">Pathologist</span>
                  <svg className="w-3 h-3 shrink-0 ml-1 fill-current text-gray-400 dark:text-gray-500" viewBox="0 0 12 12">
                    <path d="M5.9 11.4.5 6l1.4-1.4 4 4 4-4L11.3 6z" />
                  </svg>
                </div>
              </button>
              <Transition
                className="origin-top-right z-10 absolute top-full min-w-[11rem] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700/60 py-1.5 rounded-lg shadow-lg overflow-hidden mt-1 right-0"
                show={userMenuOpen}
                enter="transition ease-out duration-200 transform"
                enterStart="opacity-0 -translate-y-2"
                enterEnd="opacity-100 translate-y-0"
                leave="transition ease-out duration-200"
                leaveStart="opacity-100"
                leaveEnd="opacity-0"
              >
                <div className="pt-0.5 pb-2 px-3 mb-1 border-b border-gray-200 dark:border-gray-700/60">
                  <div className="font-medium text-gray-800 dark:text-gray-100">Clinical User</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 italic">Pathologist</div>
                </div>
                <ul>
                  <li>
                    <Link className="font-medium text-sm text-violet-500 hover:text-violet-600 dark:hover:text-violet-400 flex items-center py-1 px-3" to="/settings" onClick={() => setUserMenuOpen(false)}>Settings</Link>
                  </li>
                  <li>
                    <Link className="font-medium text-sm text-violet-500 hover:text-violet-600 dark:hover:text-violet-400 flex items-center py-1 px-3" to="#0" onClick={() => setUserMenuOpen(false)}>Sign Out</Link>
                  </li>
                </ul>
              </Transition>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
