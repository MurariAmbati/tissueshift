import { useState, useRef, useEffect, useCallback } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import { classNames } from '../utils/Utils';

const mockNodes = [
  { id: 'ERBB2', type: 'gene', x: 400, y: 200, connections: ['PIK3CA', 'AKT1', 'MAPK', 'Trastuzumab'] },
  { id: 'PIK3CA', type: 'gene', x: 250, y: 120, connections: ['AKT1', 'mTOR', 'Alpelisib'] },
  { id: 'AKT1', type: 'gene', x: 300, y: 310, connections: ['mTOR', 'PIK3CA'] },
  { id: 'mTOR', type: 'pathway', x: 150, y: 250, connections: ['AKT1', 'Everolimus'] },
  { id: 'MAPK', type: 'pathway', x: 550, y: 150, connections: ['ERBB2', 'MEK'] },
  { id: 'MEK', type: 'pathway', x: 650, y: 250, connections: ['MAPK', 'Trametinib'] },
  { id: 'TP53', type: 'gene', x: 500, y: 350, connections: ['MDM2', 'CDK4'] },
  { id: 'MDM2', type: 'gene', x: 600, y: 400, connections: ['TP53'] },
  { id: 'CDK4', type: 'gene', x: 400, y: 420, connections: ['TP53', 'Palbociclib'] },
  { id: 'Trastuzumab', type: 'drug', x: 350, y: 80, connections: ['ERBB2'] },
  { id: 'Alpelisib', type: 'drug', x: 100, y: 80, connections: ['PIK3CA'] },
  { id: 'Everolimus', type: 'drug', x: 50, y: 320, connections: ['mTOR'] },
  { id: 'Trametinib', type: 'drug', x: 720, y: 320, connections: ['MEK'] },
  { id: 'Palbociclib', type: 'drug', x: 350, y: 500, connections: ['CDK4'] },
];

const typeColors = { gene: '#8b5cf6', pathway: '#0ea5e9', drug: '#10b981' };

export default function KnowledgeGraphView() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selected, setSelected] = useState(null);
  const [search, setSearch] = useState('');
  const canvasRef = useRef(null);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const nodeMap = {};
    mockNodes.forEach((n) => { nodeMap[n.id] = n; });

    // Draw edges
    ctx.strokeStyle = '#64748b30';
    ctx.lineWidth = 1.5;
    mockNodes.forEach((n) => {
      n.connections.forEach((cId) => {
        const target = nodeMap[cId];
        if (!target) return;
        const isHighlighted = selected && (selected === n.id || selected === cId);
        ctx.strokeStyle = isHighlighted ? '#8b5cf680' : '#64748b20';
        ctx.lineWidth = isHighlighted ? 2.5 : 1;
        ctx.beginPath();
        ctx.moveTo(n.x, n.y);
        ctx.lineTo(target.x, target.y);
        ctx.stroke();
      });
    });

    // Draw nodes
    mockNodes.forEach((n) => {
      const isSelected = selected === n.id;
      const isSearched = search && n.id.toLowerCase().includes(search.toLowerCase());
      const r = isSelected ? 24 : 18;
      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
      ctx.fillStyle = isSearched ? '#f59e0b' : typeColors[n.type];
      ctx.globalAlpha = isSelected ? 1 : 0.85;
      ctx.fill();
      ctx.globalAlpha = 1;
      if (isSelected) { ctx.strokeStyle = '#fff'; ctx.lineWidth = 3; ctx.stroke(); }
      ctx.fillStyle = '#fff';
      ctx.font = `${isSelected ? 'bold ' : ''}${isSelected ? 11 : 9}px Inter, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(n.id, n.x, n.y);
    });
  }, [selected, search]);

  useEffect(() => { draw(); }, [draw]);

  useEffect(() => {
    const handleResize = () => draw();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [draw]);

  const handleCanvasClick = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const clicked = mockNodes.find((n) => Math.hypot(n.x - x, n.y - y) < 20);
    setSelected(clicked ? clicked.id : null);
  };

  const selectedNode = mockNodes.find((n) => n.id === selected);

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
            <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold mb-2">Knowledge Graph</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">Interactive gene-pathway-drug network for breast cancer</p>

            <div className="grid grid-cols-12 gap-6">
              {/* Graph */}
              <div className="col-span-12 lg:col-span-8 bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-4">
                <div className="flex items-center gap-3 mb-4">
                  <input
                    className="form-input text-sm flex-1 bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700/60 rounded-lg"
                    placeholder="Search nodes..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                  <div className="flex items-center gap-3 text-xs">
                    {Object.entries(typeColors).map(([t, c]) => (
                      <span key={t} className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: c }} />{t}</span>
                    ))}
                  </div>
                </div>
                <div className="relative h-[520px] bg-gray-50 dark:bg-gray-900/30 rounded-lg overflow-hidden">
                  <canvas ref={canvasRef} className="absolute inset-0 cursor-pointer" onClick={handleCanvasClick} />
                </div>
              </div>

              {/* Details panel */}
              <div className="col-span-12 lg:col-span-4 bg-white dark:bg-gray-800 shadow-xs rounded-xl border border-gray-200 dark:border-gray-700/60 p-5">
                <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Node Details</h2>
                {selectedNode ? (
                  <div>
                    <div className="flex items-center gap-2 mb-4">
                      <span className="w-4 h-4 rounded-full" style={{ backgroundColor: typeColors[selectedNode.type] }} />
                      <span className="text-xl font-bold text-gray-800 dark:text-gray-100">{selectedNode.id}</span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700/50 text-gray-600 dark:text-gray-300 uppercase">{selectedNode.type}</span>
                    </div>
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Connections ({selectedNode.connections.length})</h3>
                    <ul className="space-y-2">
                      {selectedNode.connections.map((c) => {
                        const target = mockNodes.find((n) => n.id === c);
                        return (
                          <li key={c} className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/20 cursor-pointer" onClick={() => setSelected(c)}>
                            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: target ? typeColors[target.type] : '#94a3b8' }} />
                            <span className="text-sm text-gray-700 dark:text-gray-300">{c}</span>
                            {target && <span className="text-xs text-gray-400 ml-auto">{target.type}</span>}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                ) : (
                  <p className="text-sm text-gray-400 dark:text-gray-500">Click a node in the graph to see details</p>
                )}
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
