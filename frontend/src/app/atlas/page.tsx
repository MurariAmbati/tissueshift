'use client';

import { useState } from 'react';
import TissueManifold from '@/components/TissueManifold';
import SubtypeRiver from '@/components/SubtypeRiver';

export default function AtlasPage() {
  const [selectedPoint, setSelectedPoint] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'manifold' | 'river' | 'wsi'>(
    'manifold'
  );

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="mb-2 text-3xl font-bold">Tissue State Atlas</h1>
      <p className="mb-8 text-[var(--text-secondary)]">
        Explore the learned tissue state manifold, subtype emergence patterns,
        and morphology-to-molecular mappings.
      </p>

      {/* Tab navigation */}
      <div className="mb-6 flex gap-2">
        {[
          { key: 'manifold' as const, label: '3D Manifold' },
          { key: 'river' as const, label: 'Subtype River' },
          { key: 'wsi' as const, label: 'WSI Viewer' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? 'bg-[var(--accent-purple)] text-white'
                : 'bg-white/5 text-[var(--text-secondary)] hover:bg-white/10'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === 'manifold' && (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <TissueManifold
              onPointClick={(p) => setSelectedPoint(p.id)}
              selectedPoint={selectedPoint}
            />
          </div>
          <div className="space-y-4">
            <div className="glass-card p-4">
              <h3 className="mb-2 font-semibold">Sample Details</h3>
              {selectedPoint ? (
                <div className="space-y-2 text-sm text-[var(--text-secondary)]">
                  <p>
                    <span className="text-white">ID:</span> {selectedPoint}
                  </p>
                  <p>
                    <span className="text-white">Subtype:</span>{' '}
                    {selectedPoint.split('_')[0]}
                  </p>
                  <p className="text-xs">
                    Click a point in the manifold to see details
                  </p>
                </div>
              ) : (
                <p className="text-sm text-[var(--text-secondary)]">
                  Click a point in the manifold to see sample details
                </p>
              )}
            </div>

            <div className="glass-card p-4">
              <h3 className="mb-2 font-semibold">Manifold Stats</h3>
              <div className="space-y-1 text-sm text-[var(--text-secondary)]">
                <p>Samples: 250 (demo)</p>
                <p>Subtypes: 5 (PAM50)</p>
                <p>Projection: UMAP 3D</p>
                <p>State dim: 512</p>
              </div>
            </div>

            <div className="glass-card p-4">
              <h3 className="mb-3 font-semibold">Controls</h3>
              <div className="space-y-2 text-sm text-[var(--text-secondary)]">
                <p>🖱️ Drag to rotate</p>
                <p>📏 Scroll to zoom</p>
                <p>👆 Click point for details</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'river' && (
        <div>
          <SubtypeRiver width={900} height={450} />
          <div className="mt-4 glass-card p-4">
            <h3 className="mb-2 font-semibold">About the Subtype River</h3>
            <p className="text-sm text-[var(--text-secondary)]">
              The streamgraph shows how subtype proportions shift across
              progression stages (Normal → ADH → DCIS → IDC → Metastatic).
              Stream width encodes relative subtype prevalence at each stage.
              Hover over streams to highlight individual subtypes.
            </p>
          </div>
        </div>
      )}

      {activeTab === 'wsi' && (
        <div className="glass-card flex h-[500px] items-center justify-center p-8">
          <div className="text-center text-[var(--text-secondary)]">
            <div className="mb-4 text-4xl">🔬</div>
            <h3 className="mb-2 text-lg font-semibold text-white">
              WSI Viewer
            </h3>
            <p className="text-sm">
              Whole-slide image viewer with attention heatmap overlay.
              <br />
              Coming soon — will use OpenSeadragon + attention weights from ABMIL.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
