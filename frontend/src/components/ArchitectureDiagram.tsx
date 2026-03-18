'use client';

import { useState } from 'react';

interface NodeInfo {
  label: string;
  desc: string;
}

const NODE_INFO: Record<string, NodeInfo> = {
  wsi: { label: 'WSI Patches', desc: 'H&E whole-slide image tiles (256×256 px) extracted via Otsu thresholding' },
  uni: { label: 'UNI ViT-L/16', desc: 'Frozen foundation encoder (MahmoodLab) with LoRA adapter for domain tuning' },
  region: { label: 'Region Tokenizer', desc: 'Attention pooling over patch groups with sinusoidal positional encoding' },
  abmil: { label: 'ABMIL', desc: 'Attention-based multi-instance learning for slide-level aggregation' },
  z_path: { label: 'z_path', desc: 'Pathology embedding — 512 dimensions' },
  rna: { label: 'RNA / Protein', desc: 'Gene expression (2000 HVG) + pathway activity (ssGSEA) + proteomic abundance' },
  expr_enc: { label: 'Expression Encoder', desc: 'Multi-head MLP with modality dropout (p=0.15) across expression, pathway, and proteomic inputs' },
  z_mol: { label: 'z_mol', desc: 'Molecular embedding — 256 dimensions' },
  graph: { label: 'Cell Graph', desc: 'Spatial cell-level graph constructed from H&E-derived cell positions (k-NN)' },
  gnn: { label: 'GNN Encoder', desc: 'Graph Isomorphism Network (PyG) with edge features for spatial neighborhood structure' },
  z_spat: { label: 'z_spat', desc: 'Spatial embedding — 128 dimensions' },
  fusion: { label: 'Cross-Attention Fusion', desc: '8 learned tissue-state queries attend across all modality tokens simultaneously' },
  manifold: { label: 'Tissue State z ∈ R⁵¹²', desc: 'Shared manifold with VICReg regularization + subtype contrastive loss for separation' },
  subtype: { label: 'Subtype Head', desc: 'PAM50 classification — Macro-F1 metric' },
  survival: { label: 'Survival Head', desc: 'Discrete hazard model — C-index metric' },
  morph2mol: { label: 'Morph2Mol Head', desc: 'Gene expression prediction from morphology — R² metric' },
  transition: { label: 'Transition Lattice', desc: 'Subtype drift probability with learned adjacency — AUROC metric' },
  microenv: { label: 'MicroEnv Head', desc: 'Spatial phenotype prediction — R²-TIL metric' },
};

const QUERY_LABELS = ['Lineage', 'Prolif', 'HER2', 'Basal', 'Immune', 'Stroma', 'CIN', 'Unc'];

export default function ArchitectureDiagram() {
  const [hovered, setHovered] = useState<string | null>(null);

  const info = hovered ? NODE_INFO[hovered] : null;

  return (
    <div className="relative">
      {/* Tooltip */}
      <div
        className={`absolute top-0 right-0 z-10 max-w-xs border border-[#1a1a1a] bg-[#0a0a0a] p-5 transition-opacity duration-200 ${
          info ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
      >
        {info && (
          <>
            <p className="font-mono text-[11px] tracking-[0.15em] text-white mb-2">{info.label}</p>
            <p className="text-[13px] leading-[1.6] text-[#666]">{info.desc}</p>
          </>
        )}
      </div>

      <svg
        viewBox="0 0 1000 820"
        className="w-full h-auto"
        style={{ maxWidth: 1000 }}
      >
        <defs>
          {/* Glow filter for hovered nodes */}
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          {/* Arrow marker */}
          <marker id="arrow" viewBox="0 0 10 7" refX="10" refY="3.5" markerWidth="8" markerHeight="6" orient="auto-start-auto">
            <path d="M 0 0 L 10 3.5 L 0 7 z" fill="#333" />
          </marker>
          <marker id="arrow-lit" viewBox="0 0 10 7" refX="10" refY="3.5" markerWidth="8" markerHeight="6" orient="auto-start-auto">
            <path d="M 0 0 L 10 3.5 L 0 7 z" fill="#666" />
          </marker>
          {/* Gradient for fusion bar */}
          <linearGradient id="fusionGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#1a1a2e" />
            <stop offset="50%" stopColor="#1e1e3a" />
            <stop offset="100%" stopColor="#1a1a2e" />
          </linearGradient>
          <linearGradient id="manifoldGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#0f0f1a" />
            <stop offset="50%" stopColor="#161628" />
            <stop offset="100%" stopColor="#0f0f1a" />
          </linearGradient>
        </defs>

        {/* ═══════ CONNECTIONS (drawn first, behind nodes) ═══════ */}

        {/* Path: WSI → UNI → Region → ABMIL → z_path */}
        <line x1="110" y1="80" x2="250" y2="80" stroke="#222" strokeWidth="1" markerEnd="url(#arrow)" />
        <line x1="370" y1="80" x2="490" y2="80" stroke="#222" strokeWidth="1" markerEnd="url(#arrow)" />
        <line x1="640" y1="80" x2="750" y2="80" stroke="#222" strokeWidth="1" markerEnd="url(#arrow)" />
        <line x1="820" y1="80" x2="910" y2="80" stroke="#222" strokeWidth="1" markerEnd="url(#arrow)" />

        {/* Path: RNA → Expr Enc → z_mol */}
        <line x1="110" y1="190" x2="370" y2="190" stroke="#222" strokeWidth="1" markerEnd="url(#arrow)" />
        <line x1="530" y1="190" x2="910" y2="190" stroke="#222" strokeWidth="1" markerEnd="url(#arrow)" />

        {/* Path: Graph → GNN → z_spat */}
        <line x1="110" y1="300" x2="370" y2="300" stroke="#222" strokeWidth="1" markerEnd="url(#arrow)" />
        <line x1="530" y1="300" x2="910" y2="300" stroke="#222" strokeWidth="1" markerEnd="url(#arrow)" />

        {/* Vertical merge lines from z_path, z_mol, z_spat down to fusion */}
        <line x1="950" y1="100" x2="950" y2="320" stroke="#333" strokeWidth="1" strokeDasharray="4 3" />
        <line x1="950" y1="320" x2="500" y2="420" stroke="#333" strokeWidth="1" markerEnd="url(#arrow)" />

        {/* Fusion down to manifold */}
        <line x1="500" y1="470" x2="500" y2="540" stroke="#444" strokeWidth="1.5" markerEnd="url(#arrow-lit)" />

        {/* Manifold down to prediction heads */}
        {[180, 320, 500, 680, 820].map((x, i) => (
          <line key={i} x1="500" y1="600" x2={x} y2="700" stroke="#333" strokeWidth="1" markerEnd="url(#arrow)" />
        ))}

        {/* ═══════ INPUT MODALITY ROW ═══════ */}

        {/* WSI Patches */}
        <g
          onMouseEnter={() => setHovered('wsi')}
          onMouseLeave={() => setHovered(null)}
          className="cursor-pointer"
        >
          <rect x="20" y="58" width="90" height="44" rx="2" fill={hovered === 'wsi' ? '#151515' : '#0c0c0c'} stroke={hovered === 'wsi' ? '#444' : '#1a1a1a'} strokeWidth="1" />
          <text x="65" y="76" textAnchor="middle" fill={hovered === 'wsi' ? '#fff' : '#888'} fontSize="10" fontFamily="monospace">WSI</text>
          <text x="65" y="92" textAnchor="middle" fill="#444" fontSize="8" fontFamily="monospace">PATCHES</text>
        </g>

        {/* UNI ViT-L */}
        <g
          onMouseEnter={() => setHovered('uni')}
          onMouseLeave={() => setHovered(null)}
          className="cursor-pointer"
        >
          <rect x="250" y="58" width="120" height="44" rx="2" fill={hovered === 'uni' ? '#151520' : '#0c0c14'} stroke={hovered === 'uni' ? '#5555aa' : '#222'} strokeWidth="1" />
          <text x="310" y="76" textAnchor="middle" fill={hovered === 'uni' ? '#aab' : '#777'} fontSize="11" fontFamily="monospace" fontWeight="600">UNI ViT-L</text>
          <text x="310" y="92" textAnchor="middle" fill="#444" fontSize="8" fontFamily="monospace">FROZEN + LORA</text>
        </g>

        {/* Region Tokenizer */}
        <g
          onMouseEnter={() => setHovered('region')}
          onMouseLeave={() => setHovered(null)}
          className="cursor-pointer"
        >
          <rect x="490" y="58" width="150" height="44" rx="2" fill={hovered === 'region' ? '#151515' : '#0c0c0c'} stroke={hovered === 'region' ? '#444' : '#1a1a1a'} strokeWidth="1" />
          <text x="565" y="76" textAnchor="middle" fill={hovered === 'region' ? '#fff' : '#888'} fontSize="10" fontFamily="monospace">REGION</text>
          <text x="565" y="92" textAnchor="middle" fill="#444" fontSize="8" fontFamily="monospace">TOKENIZER</text>
        </g>

        {/* ABMIL */}
        <g
          onMouseEnter={() => setHovered('abmil')}
          onMouseLeave={() => setHovered(null)}
          className="cursor-pointer"
        >
          <rect x="750" y="58" width="70" height="44" rx="2" fill={hovered === 'abmil' ? '#151515' : '#0c0c0c'} stroke={hovered === 'abmil' ? '#444' : '#1a1a1a'} strokeWidth="1" />
          <text x="785" y="84" textAnchor="middle" fill={hovered === 'abmil' ? '#fff' : '#888'} fontSize="11" fontFamily="monospace" fontWeight="600">ABMIL</text>
        </g>

        {/* z_path */}
        <g
          onMouseEnter={() => setHovered('z_path')}
          onMouseLeave={() => setHovered(null)}
          className="cursor-pointer"
        >
          <rect x="910" y="62" width="70" height="36" rx="18" fill="none" stroke={hovered === 'z_path' ? '#4a9eff' : '#1a3a5a'} strokeWidth="1.5" />
          <text x="945" y="84" textAnchor="middle" fill={hovered === 'z_path' ? '#4a9eff' : '#3a6a9a'} fontSize="11" fontFamily="monospace" fontWeight="600">z_path</text>
        </g>

        {/* RNA / Protein */}
        <g
          onMouseEnter={() => setHovered('rna')}
          onMouseLeave={() => setHovered(null)}
          className="cursor-pointer"
        >
          <rect x="20" y="168" width="90" height="44" rx="2" fill={hovered === 'rna' ? '#151515' : '#0c0c0c'} stroke={hovered === 'rna' ? '#444' : '#1a1a1a'} strokeWidth="1" />
          <text x="65" y="186" textAnchor="middle" fill={hovered === 'rna' ? '#fff' : '#888'} fontSize="10" fontFamily="monospace">RNA /</text>
          <text x="65" y="202" textAnchor="middle" fill="#444" fontSize="8" fontFamily="monospace">PROTEIN</text>
        </g>

        {/* Expression Encoder */}
        <g
          onMouseEnter={() => setHovered('expr_enc')}
          onMouseLeave={() => setHovered(null)}
          className="cursor-pointer"
        >
          <rect x="370" y="168" width="160" height="44" rx="2" fill={hovered === 'expr_enc' ? '#151520' : '#0c0c14'} stroke={hovered === 'expr_enc' ? '#5555aa' : '#222'} strokeWidth="1" />
          <text x="450" y="186" textAnchor="middle" fill={hovered === 'expr_enc' ? '#aab' : '#777'} fontSize="10" fontFamily="monospace">EXPRESSION</text>
          <text x="450" y="202" textAnchor="middle" fill="#444" fontSize="8" fontFamily="monospace">ENCODER</text>
        </g>

        {/* z_mol */}
        <g
          onMouseEnter={() => setHovered('z_mol')}
          onMouseLeave={() => setHovered(null)}
          className="cursor-pointer"
        >
          <rect x="910" y="172" width="70" height="36" rx="18" fill="none" stroke={hovered === 'z_mol' ? '#10b981' : '#1a3a2a'} strokeWidth="1.5" />
          <text x="945" y="194" textAnchor="middle" fill={hovered === 'z_mol' ? '#10b981' : '#2a6a4a'} fontSize="11" fontFamily="monospace" fontWeight="600">z_mol</text>
        </g>

        {/* Cell Graph */}
        <g
          onMouseEnter={() => setHovered('graph')}
          onMouseLeave={() => setHovered(null)}
          className="cursor-pointer"
        >
          <rect x="20" y="278" width="90" height="44" rx="2" fill={hovered === 'graph' ? '#151515' : '#0c0c0c'} stroke={hovered === 'graph' ? '#444' : '#1a1a1a'} strokeWidth="1" />
          <text x="65" y="296" textAnchor="middle" fill={hovered === 'graph' ? '#fff' : '#888'} fontSize="10" fontFamily="monospace">CELL</text>
          <text x="65" y="312" textAnchor="middle" fill="#444" fontSize="8" fontFamily="monospace">GRAPH</text>
        </g>

        {/* GNN Encoder */}
        <g
          onMouseEnter={() => setHovered('gnn')}
          onMouseLeave={() => setHovered(null)}
          className="cursor-pointer"
        >
          <rect x="370" y="278" width="160" height="44" rx="2" fill={hovered === 'gnn' ? '#151520' : '#0c0c14'} stroke={hovered === 'gnn' ? '#5555aa' : '#222'} strokeWidth="1" />
          <text x="450" y="296" textAnchor="middle" fill={hovered === 'gnn' ? '#aab' : '#777'} fontSize="10" fontFamily="monospace">GNN</text>
          <text x="450" y="312" textAnchor="middle" fill="#444" fontSize="8" fontFamily="monospace">ENCODER (PyG)</text>
        </g>

        {/* z_spat */}
        <g
          onMouseEnter={() => setHovered('z_spat')}
          onMouseLeave={() => setHovered(null)}
          className="cursor-pointer"
        >
          <rect x="910" y="282" width="70" height="36" rx="18" fill="none" stroke={hovered === 'z_spat' ? '#ec4899' : '#3a1a2a'} strokeWidth="1.5" />
          <text x="945" y="304" textAnchor="middle" fill={hovered === 'z_spat' ? '#ec4899' : '#6a2a4a'} fontSize="11" fontFamily="monospace" fontWeight="600">z_spat</text>
        </g>

        {/* ═══════ DIMENSION LABELS ═══════ */}
        <text x="985" y="84" fill="#333" fontSize="9" fontFamily="monospace">512d</text>
        <text x="985" y="194" fill="#333" fontSize="9" fontFamily="monospace">256d</text>
        <text x="985" y="304" fill="#333" fontSize="9" fontFamily="monospace">128d</text>

        {/* ═══════ FUSION BAR ═══════ */}
        <g
          onMouseEnter={() => setHovered('fusion')}
          onMouseLeave={() => setHovered(null)}
          className="cursor-pointer"
        >
          <rect x="120" y="400" width="760" height="70" rx="3" fill="url(#fusionGrad)" stroke={hovered === 'fusion' ? '#4444aa' : '#222'} strokeWidth="1" />
          <text x="500" y="422" textAnchor="middle" fill={hovered === 'fusion' ? '#bbb' : '#666'} fontSize="11" fontFamily="monospace" fontWeight="600">CROSS-ATTENTION FUSION</text>
          <text x="500" y="438" textAnchor="middle" fill="#444" fontSize="9" fontFamily="monospace">8 tissue-state queries</text>

          {/* Query chips */}
          {QUERY_LABELS.map((q, i) => {
            const chipW = 75;
            const totalW = QUERY_LABELS.length * chipW;
            const startX = 500 - totalW / 2;
            const cx = startX + i * chipW + chipW / 2;
            return (
              <g key={q}>
                <rect x={cx - 32} y="448" width="64" height="16" rx="2" fill="#111" stroke="#222" strokeWidth="0.5" />
                <text x={cx} y="460" textAnchor="middle" fill="#555" fontSize="8" fontFamily="monospace">{q}</text>
              </g>
            );
          })}
        </g>

        {/* ═══════ MANIFOLD ═══════ */}
        <g
          onMouseEnter={() => setHovered('manifold')}
          onMouseLeave={() => setHovered(null)}
          className="cursor-pointer"
        >
          <rect x="220" y="550" width="560" height="50" rx="25" fill="url(#manifoldGrad)" stroke={hovered === 'manifold' ? '#555' : '#222'} strokeWidth="1.5" />
          <text x="500" y="572" textAnchor="middle" fill={hovered === 'manifold' ? '#ddd' : '#888'} fontSize="12" fontFamily="monospace" fontWeight="600">
            TISSUE STATE   z ∈ R⁵¹²
          </text>
          <text x="500" y="590" textAnchor="middle" fill="#444" fontSize="9" fontFamily="monospace">VICReg + Contrastive</text>
        </g>

        {/* ═══════ PREDICTION HEADS ═══════ */}
        {[
          { key: 'subtype', label: 'SUBTYPE', sub: 'HEAD', x: 180, color: '#4a9eff', dimColor: '#1a3a5a' },
          { key: 'survival', label: 'SURVIVAL', sub: 'HEAD', x: 320, color: '#10b981', dimColor: '#1a3a2a' },
          { key: 'morph2mol', label: 'MORPH2MOL', sub: 'HEAD', x: 500, color: '#f59e0b', dimColor: '#3a2a0a' },
          { key: 'transition', label: 'TRANSITION', sub: 'LATTICE', x: 680, color: '#ec4899', dimColor: '#3a1a2a' },
          { key: 'microenv', label: 'MICROENV', sub: 'HEAD', x: 820, color: '#8b5cf6', dimColor: '#2a1a3a' },
        ].map((head) => (
          <g
            key={head.key}
            onMouseEnter={() => setHovered(head.key)}
            onMouseLeave={() => setHovered(null)}
            className="cursor-pointer"
          >
            <rect
              x={head.x - 55}
              y="710"
              width="110"
              height="50"
              rx="3"
              fill={hovered === head.key ? '#141414' : '#0a0a0a'}
              stroke={hovered === head.key ? head.color : head.dimColor}
              strokeWidth={hovered === head.key ? 1.5 : 1}
            />
            <text
              x={head.x}
              y="732"
              textAnchor="middle"
              fill={hovered === head.key ? head.color : '#666'}
              fontSize="10"
              fontFamily="monospace"
              fontWeight="600"
            >
              {head.label}
            </text>
            <text
              x={head.x}
              y="748"
              textAnchor="middle"
              fill="#444"
              fontSize="8"
              fontFamily="monospace"
            >
              {head.sub}
            </text>
          </g>
        ))}

        {/* ═══════ FLOW DIRECTION LABEL ═══════ */}
        <text x="14" y="420" fill="#222" fontSize="9" fontFamily="monospace" transform="rotate(-90, 14, 420)">DATA FLOW ↓</text>

      </svg>
    </div>
  );
}
