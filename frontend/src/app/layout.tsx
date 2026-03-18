import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });
const jetbrainsMono = JetBrains_Mono({ subsets: ['latin'], variable: '--font-mono' });

export const metadata: Metadata = {
  title: 'TissueShift — Temporal Histopathology-to-Omics',
  description:
    'Open temporal histopathology-to-omics model for breast cancer subtype emergence and progression',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen font-sans antialiased">
        <nav className="fixed top-0 z-50 w-full border-b border-white/[0.06] bg-black/80 backdrop-blur-md">
          <div className="mx-auto flex h-14 max-w-[1400px] items-center justify-between px-6 sm:px-12">
            <a href="/" className="font-mono text-sm font-semibold tracking-[0.05em] text-white">
              TISSUESHIFT
            </a>
            <div className="hidden items-center gap-8 font-mono text-[11px] tracking-[0.15em] text-[#555] sm:flex">
              <a href="/#problem" className="transition-colors hover:text-white">THE PROBLEM</a>
              <a href="/#model" className="transition-colors hover:text-white">ARCHITECTURE</a>
              <a href="/#benchmark" className="transition-colors hover:text-white">BENCHMARK</a>
              <a href="/#roadmap" className="transition-colors hover:text-white">ROADMAP</a>
              <a href="/#contact" className="transition-colors hover:text-white">CONTACT</a>
            </div>
          </div>
        </nav>
        <main className="pt-14">{children}</main>
      </body>
    </html>
  );
}
