'use client';

import { useState } from 'react';
import TissueManifold from '@/components/TissueManifold';
import SubtypeRiver from '@/components/SubtypeRiver';

export default function AtlasPage() {
  const [selectedPoint, setSelectedPoint] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'manifold' | 'river' | 'wsi'>('manifold');

  return (
    <div className="mx-auto max-w-[1400px] px-6 sm:px-12 lg:px-24 py-16 lg:py-24">
      <p className="section-label mb-6">INTERACTIVE</p>
      <h1 className="text-3xl sm:text-4xl font-bold leading-[1.1] tracking-[-0.01em] mb-3">
        Tissue State Atlas
      </h1>
      <p className="mb-10 text-[15px] text-[#777] max-w-xl">
        Explore the learned tissue state manifold, subtype emergence patterns,
        and morphology-to-molecular mappings.
      </p>

      {/* Tab navigation */}
      <div className="mb-8 flex flex-wrap gap-2">
        {[
          { key: 'manifold' as const, label: '3D MANIFOLD' },
          { key: 'river' as const, label: 'SUBTYPE RIVER' },
          { key: 'wsi' as const, label: 'WSI VIEWER' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`font-mono text-[11px] tracking-[0.1em] px-4 py-2 border transition-colors ${
              activeTab === tab.key
                ? 'border-white/40 text-white bg-white/[0.04]'
                : 'border-[#1a1a1a] text-[#555] hover:border-white/20 hover:text-white/70'
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
          <div className="space-y-px border border-[#1a1a1a]">
            <div className="bg-[#080808] p-6">
              <p className="font-mono text-[10px] tracking-[0.2em] text-[#444] mb-4">SAMPLE DETAILS</p>
              {selectedPoint ? (
                <div className="space-y-2 text-[14px] text-[#666]">
                  <p><span className="text-white">ID:</span> {selectedPoint}</p>
                  <p><span className="text-white">Subtype:</span> {selectedPoint.split('_')[0]}</p>
                </div>
              ) : (
                <p className="text-[14px] text-[#555]">Click a point in the manifold to see details</p>
              )}
            </div>
            <div className="bg-[#080808] p-6">
              <p className="font-mono text-[10px] tracking-[0.2em] text-[#444] mb-4">MANIFOLD STATS</p>
              <div className="space-y-1.5 text-[14px] text-[#666]">
                <p>Samples: 250 (demo)</p>
                <p>Subtypes: 5 (PAM50)</p>
                <p>Projection: UMAP 3D</p>
                <p>State dim: 512</p>
              </div>
            </div>
            <div className="bg-[#080808] p-6">
              <p className="font-mono text-[10px] tracking-[0.2em] text-[#444] mb-4">CONTROLS</p>
              <div className="space-y-1.5 text-[14px] text-[#666]">
                <p>Drag to rotate</p>
                <p>Scroll to zoom</p>
                <p>Click point for details</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'river' && (
        <div>
          <SubtypeRiver width={900} height={450} />
          <div className="mt-6 border border-[#1a1a1a] bg-[#080808] p-8">
            <p className="font-mono text-[10px] tracking-[0.2em] text-[#444] mb-4">ABOUT THE SUBTYPE RIVER</p>
            <p className="text-[14px] leading-[1.7] text-[#666]">
              The streamgraph shows how subtype proportions shift across
              progression stages (Normal → ADH → DCIS → IDC → Metastatic).
              Stream width encodes relative subtype prevalence at each stage.
              Hover over streams to highlight individual subtypes.
            </p>
          </div>
        </div>
      )}

      {activeTab === 'wsi' && (
        <div className="border border-[#1a1a1a] bg-[#080808] flex h-[500px] items-center justify-center">
          <div className="text-center">
            <p className="font-mono text-[10px] tracking-[0.2em] text-[#444] mb-4">WSI VIEWER</p>
            <h3 className="text-[16px] font-semibold mb-3">Coming Soon</h3>
            <p className="text-[14px] text-[#555] max-w-md">
              Whole-slide image viewer with attention heatmap overlay.
              Will use OpenSeadragon + attention weights from ABMIL.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
