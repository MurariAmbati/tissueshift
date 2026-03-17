import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'TissueShift — Temporal Histopathology Atlas',
  description:
    'Open temporal histopathology-to-omics model for breast cancer subtype emergence and progression',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] antialiased">
        <nav className="fixed top-0 z-50 w-full border-b border-white/10 bg-black/50 backdrop-blur-xl">
          <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
            <a href="/" className="flex items-center gap-2 font-bold text-lg">
              <span className="text-[var(--accent-purple)]">🔬</span>
              TissueShift
            </a>
            <div className="flex items-center gap-6 text-sm text-[var(--text-secondary)]">
              <a href="/atlas" className="hover:text-white transition-colors">
                Atlas
              </a>
              <a href="/leaderboard" className="hover:text-white transition-colors">
                Leaderboard
              </a>
              <a href="/contribute" className="hover:text-white transition-colors">
                Contribute
              </a>
              <a href="/dashboard" className="hover:text-white transition-colors">
                Dashboard
              </a>
              <a
                href="https://github.com/tissueshift/tissueshift"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-white transition-colors"
              >
                GitHub
              </a>
            </div>
          </div>
        </nav>
        <main className="pt-14">{children}</main>
      </body>
    </html>
  );
}
