import { useState, useRef, useEffect, useCallback } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import GlowCard from '../components/GlowCard';
import AnimatedCounter from '../components/AnimatedCounter';
import Sparkline from '../components/Sparkline';

/* ── Cohort data ──────────────────────────────────────────────── */
const REGIONS = [
  { name: 'Northeast', patients: 2840, avgAge: 58.2, incidenceRate: 128.4, mortalityRate: 19.2, screeningRate: 82, lat: 0.72, lng: 0.82 },
  { name: 'Southeast', patients: 3120, avgAge: 55.8, incidenceRate: 134.1, mortalityRate: 22.8, screeningRate: 71, lat: 0.55, lng: 0.78 },
  { name: 'Midwest', patients: 2560, avgAge: 57.1, incidenceRate: 126.9, mortalityRate: 20.5, screeningRate: 76, lat: 0.62, lng: 0.48 },
  { name: 'Southwest', patients: 1980, avgAge: 54.3, incidenceRate: 118.5, mortalityRate: 18.1, screeningRate: 68, lat: 0.38, lng: 0.35 },
  { name: 'West Coast', patients: 3450, avgAge: 56.9, incidenceRate: 131.2, mortalityRate: 17.4, screeningRate: 85, lat: 0.45, lng: 0.12 },
  { name: 'Mountain', patients: 1240, avgAge: 56.0, incidenceRate: 112.8, mortalityRate: 16.9, screeningRate: 73, lat: 0.52, lng: 0.28 },
];

const SUBTYPES = [
  { name: 'Luminal A', pct: 42, color: '#0ea5e9', trend: [38,39,40,41,42,42] },
  { name: 'Luminal B', pct: 18, color: '#8b5cf6', trend: [20,19,19,18,18,18] },
  { name: 'HER2+', pct: 15, color: '#f59e0b', trend: [16,16,15,15,15,15] },
  { name: 'Triple-Neg', pct: 14, color: '#f43f5e', trend: [12,13,13,14,14,14] },
  { name: 'Normal-like', pct: 6, color: '#10b981', trend: [8,7,7,6,6,6] },
  { name: 'Unclassified', pct: 5, color: '#6b7280', trend: [6,6,6,5,5,5] },
];

const DISPARITIES = [
  { group: 'White', incidence: 130.8, mortality: 19.3, lateStage: 22 },
  { group: 'Black', incidence: 126.7, mortality: 27.6, lateStage: 31 },
  { group: 'Hispanic', incidence: 99.4, mortality: 14.2, lateStage: 28 },
  { group: 'Asian/PI', incidence: 102.9, mortality: 11.4, lateStage: 24 },
  { group: 'AIAN', incidence: 79.5, mortality: 15.1, lateStage: 34 },
];

const YEAR_TRENDS = {
  incidence: [122.1, 124.5, 126.3, 128.7, 129.8, 131.4, 128.9, 130.2],
  mortality: [22.8, 21.9, 21.1, 20.4, 19.8, 19.2, 18.7, 18.3],
  survival5y: [88.1, 88.9, 89.4, 89.8, 90.2, 90.6, 91.0, 91.3],
  years: ['2017','2018','2019','2020','2021','2022','2023','2024'],
};

/* ── Region map canvas ──────────────────────────────────────── */
function RegionMap({ regions, selectedRegion, onSelect }) {
  const canvasRef = useRef(null);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const cw = canvas.offsetWidth, ch = 280;
    canvas.width = cw * devicePixelRatio;
    canvas.height = ch * devicePixelRatio;
    canvas.style.height = ch + 'px';
    ctx.scale(devicePixelRatio, devicePixelRatio);

    ctx.fillStyle = '#0a0a18';
    ctx.fillRect(0, 0, cw, ch);

    // Simplified US outline (polygon)
    ctx.strokeStyle = '#ffffff15';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(cw * 0.1, ch * 0.3);
    ctx.lineTo(cw * 0.15, ch * 0.18);
    ctx.lineTo(cw * 0.35, ch * 0.15);
    ctx.lineTo(cw * 0.55, ch * 0.15);
    ctx.lineTo(cw * 0.72, ch * 0.12);
    ctx.lineTo(cw * 0.88, ch * 0.2);
    ctx.lineTo(cw * 0.92, ch * 0.35);
    ctx.lineTo(cw * 0.85, ch * 0.55);
    ctx.lineTo(cw * 0.75, ch * 0.7);
    ctx.lineTo(cw * 0.6, ch * 0.78);
    ctx.lineTo(cw * 0.45, ch * 0.82);
    ctx.lineTo(cw * 0.3, ch * 0.75);
    ctx.lineTo(cw * 0.15, ch * 0.65);
    ctx.lineTo(cw * 0.1, ch * 0.5);
    ctx.closePath();
    ctx.stroke();
    ctx.fillStyle = '#ffffff04';
    ctx.fill();

    // Bubbles for each region
    regions.forEach(r => {
      const x = r.lng * cw * 0.8 + cw * 0.1;
      const y = r.lat * ch * 0.7 + ch * 0.12;
      const radius = Math.sqrt(r.patients / 200);
      const isSel = selectedRegion?.name === r.name;

      // Halo
      const hue = r.mortalityRate > 21 ? '#f43f5e' : r.mortalityRate > 18 ? '#f59e0b' : '#10b981';
      const glow = ctx.createRadialGradient(x, y, 0, x, y, radius * 2.5);
      glow.addColorStop(0, hue + '30');
      glow.addColorStop(1, 'transparent');
      ctx.fillStyle = glow;
      ctx.beginPath(); ctx.arc(x, y, radius * 2.5, 0, Math.PI * 2); ctx.fill();

      // Bubble
      ctx.beginPath(); ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fillStyle = isSel ? hue : hue + '80';
      ctx.fill();
      if (isSel) { ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.stroke(); }

      // Label
      ctx.font = '9px Inter, sans-serif';
      ctx.fillStyle = '#ffffffaa';
      ctx.textAlign = 'center';
      ctx.fillText(r.name, x, y + radius + 14);
      ctx.font = 'bold 8px Inter, sans-serif';
      ctx.fillStyle = '#ffffff60';
      ctx.fillText(`${r.patients.toLocaleString()} pts`, x, y + radius + 24);
    });
  }, [regions, selectedRegion]);

  useEffect(() => { draw(); }, [draw]);

  const handleClick = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const cw = rect.width, ch = 280;
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    for (const r of regions) {
      const x = r.lng * cw * 0.8 + cw * 0.1;
      const y = r.lat * ch * 0.7 + ch * 0.12;
      const radius = Math.sqrt(r.patients / 200);
      const dx = x - mx, dy = y - my;
      if (dx * dx + dy * dy < (radius + 8) ** 2) { onSelect(r); return; }
    }
  };

  return <canvas ref={canvasRef} className="w-full cursor-pointer" onClick={handleClick} />;
}

/* ── Trend chart (mini line) ──────────────────────────────────── */
function TrendLine({ data, years, label, color, suffix }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const cw = canvas.offsetWidth, ch = 90;
    canvas.width = cw * devicePixelRatio;
    canvas.height = ch * devicePixelRatio;
    canvas.style.height = ch + 'px';
    ctx.scale(devicePixelRatio, devicePixelRatio);

    ctx.fillStyle = '#0a0a18';
    ctx.fillRect(0, 0, cw, ch);

    const min = Math.min(...data) * 0.95, max = Math.max(...data) * 1.05;
    const pts = data.map((v, i) => ({
      x: 30 + (i / (data.length - 1)) * (cw - 50),
      y: ch - 20 - ((v - min) / (max - min)) * (ch - 40),
    }));

    // Area
    ctx.beginPath();
    pts.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
    ctx.lineTo(pts[pts.length - 1].x, ch - 20);
    ctx.lineTo(pts[0].x, ch - 20);
    ctx.closePath();
    ctx.fillStyle = color + '15';
    ctx.fill();

    // Line
    ctx.beginPath();
    pts.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.stroke();

    // Dots
    pts.forEach(p => { ctx.beginPath(); ctx.arc(p.x, p.y, 2.5, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill(); });

    // Labels
    ctx.font = '8px Inter, sans-serif';
    ctx.fillStyle = '#ffffff40';
    ctx.textAlign = 'center';
    years.forEach((y, i) => { if (i % 2 === 0) ctx.fillText(y, pts[i].x, ch - 4); });

    // Title + latest value
    ctx.font = 'bold 10px Inter, sans-serif';
    ctx.fillStyle = color;
    ctx.textAlign = 'left';
    ctx.fillText(`${label}: ${data[data.length - 1]}${suffix}`, 4, 12);
  }, [data, years, label, color, suffix]);

  return <canvas ref={canvasRef} className="w-full rounded-lg" />;
}

/* ── Main Page ────────────────────────────────────────────────── */
export default function PopulationHealth() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedRegion, setSelectedRegion] = useState(null);

  const totalPatients = REGIONS.reduce((a, r) => a + r.patients, 0);
  const avgMortality = (REGIONS.reduce((a, r) => a + r.mortalityRate, 0) / REGIONS.length).toFixed(1);
  const avgScreening = Math.round(REGIONS.reduce((a, r) => a + r.screeningRate, 0) / REGIONS.length);

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[1600px] mx-auto">
            <div className="mb-6">
              <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
                Population Health Analytics
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Epidemiological surveillance — incidence, mortality, disparities, and screening coverage across regions</p>
            </div>

            {/* KPIs */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
              {[
                { label: 'Total Cohort', value: totalPatients, suffix: '' },
                { label: 'Avg Incidence/100k', value: 128.9, suffix: '' },
                { label: 'Avg Mortality/100k', value: +avgMortality, suffix: '' },
                { label: 'Screening Rate', value: avgScreening, suffix: '%' },
                { label: '5yr Overall Survival', value: 91.3, suffix: '%' },
              ].map(k => (
                <GlowCard key={k.label} glowColor="sky" className="!p-3 text-center">
                  <div className="text-[10px] uppercase tracking-wider text-gray-400">{k.label}</div>
                  <div className="text-lg font-extrabold text-gray-800 dark:text-white mt-0.5"><AnimatedCounter end={k.value} suffix={k.suffix} decimals={k.value % 1 !== 0 ? 1 : 0} /></div>
                </GlowCard>
              ))}
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              {/* Map + trends */}
              <div className="xl:col-span-2 space-y-4">
                <GlowCard glowColor="teal" noPad className="overflow-hidden">
                  <div className="p-4 pb-2">
                    <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100">Regional Patient Distribution</h3>
                    <p className="text-[10px] text-gray-400">Bubble size = patient count · Color = mortality risk (green=low, amber=moderate, red=high)</p>
                  </div>
                  <RegionMap regions={REGIONS} selectedRegion={selectedRegion} onSelect={setSelectedRegion} />
                </GlowCard>

                {/* Temporal trends */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <GlowCard glowColor="rose" noPad className="overflow-hidden p-1">
                    <TrendLine data={YEAR_TRENDS.incidence} years={YEAR_TRENDS.years} label="Incidence/100k" color="#f43f5e" suffix="" />
                  </GlowCard>
                  <GlowCard glowColor="emerald" noPad className="overflow-hidden p-1">
                    <TrendLine data={YEAR_TRENDS.mortality} years={YEAR_TRENDS.years} label="Mortality/100k" color="#10b981" suffix="" />
                  </GlowCard>
                  <GlowCard glowColor="violet" noPad className="overflow-hidden p-1">
                    <TrendLine data={YEAR_TRENDS.survival5y} years={YEAR_TRENDS.years} label="5yr Survival" color="#8b5cf6" suffix="%" />
                  </GlowCard>
                </div>

                {/* Disparities table */}
                <GlowCard glowColor="amber" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Health Disparities by Race/Ethnicity</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-[10px] uppercase tracking-wider text-gray-400 border-b border-gray-200 dark:border-gray-700/60">
                          <th className="text-left pb-2 pr-4">Group</th>
                          <th className="text-right pb-2 pr-4">Incidence/100k</th>
                          <th className="text-right pb-2 pr-4">Mortality/100k</th>
                          <th className="text-right pb-2">Late-Stage Dx</th>
                        </tr>
                      </thead>
                      <tbody>
                        {DISPARITIES.map(d => (
                          <tr key={d.group} className="border-b border-gray-100 dark:border-gray-800">
                            <td className="py-2 pr-4 font-semibold text-gray-700 dark:text-gray-300">{d.group}</td>
                            <td className="py-2 pr-4 text-right tabular-nums">{d.incidence}</td>
                            <td className={`py-2 pr-4 text-right tabular-nums font-bold ${d.mortality > 22 ? 'text-rose-500' : d.mortality > 18 ? 'text-amber-500' : 'text-emerald-500'}`}>{d.mortality}</td>
                            <td className={`py-2 text-right tabular-nums ${d.lateStage > 28 ? 'text-rose-500' : 'text-gray-500'}`}>{d.lateStage}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </GlowCard>
              </div>

              {/* Right column */}
              <div className="space-y-4">
                {/* Selected region detail */}
                {selectedRegion ? (
                  <GlowCard glowColor="teal" className="!p-4">
                    <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">{selectedRegion.name}</h3>
                    <div className="grid grid-cols-2 gap-2 mb-3">
                      {[
                        { label: 'Patients', value: selectedRegion.patients.toLocaleString() },
                        { label: 'Avg Age', value: selectedRegion.avgAge },
                        { label: 'Incidence/100k', value: selectedRegion.incidenceRate },
                        { label: 'Mortality/100k', value: selectedRegion.mortalityRate },
                        { label: 'Screening Rate', value: selectedRegion.screeningRate + '%' },
                      ].map(d => (
                        <div key={d.label} className="p-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
                          <div className="text-[10px] text-gray-400">{d.label}</div>
                          <div className="text-sm font-bold text-gray-800 dark:text-white">{d.value}</div>
                        </div>
                      ))}
                    </div>
                  </GlowCard>
                ) : (
                  <GlowCard glowColor="teal" className="!p-5 text-center">

                    <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-1">Click a Region</h3>
                    <p className="text-xs text-gray-400">Select a region bubble on the map to drill into demographics.</p>
                  </GlowCard>
                )}

                {/* Subtype distribution */}
                <GlowCard glowColor="violet" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Subtype Distribution</h3>
                  <div className="space-y-2.5">
                    {SUBTYPES.map(s => (
                      <div key={s.name}>
                        <div className="flex items-center justify-between mb-0.5">
                          <div className="flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: s.color }} />
                            <span className="text-xs text-gray-600 dark:text-gray-300">{s.name}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Sparkline data={s.trend} color={s.color} width={40} height={14} />
                            <span className="text-[10px] font-bold text-gray-400 tabular-nums w-8 text-right">{s.pct}%</span>
                          </div>
                        </div>
                        <div className="h-1.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                          <div className="h-full rounded-full transition-all" style={{ width: `${s.pct}%`, backgroundColor: s.color }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </GlowCard>

                {/* Top-line metrics */}
                <GlowCard glowColor="emerald" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Key Population Indicators</h3>
                  <div className="space-y-2">
                    {[
                      { label: 'Median Age at Diagnosis', value: '62 years', trend: '→ stable' },
                      { label: 'Stage I at Diagnosis', value: '44%', trend: '↑ improving' },
                      { label: 'BRCA Testing Rate', value: '68%', trend: '↑ improving' },
                      { label: 'Guideline Concordance', value: '78%', trend: '↑ improving' },
                      { label: '30-day Readmission', value: '4.2%', trend: '↓ improving' },
                      { label: 'Clinical Trial Enrollment', value: '12%', trend: '→ stable' },
                    ].map(i => (
                      <div key={i.label} className="flex items-center justify-between">
                        <span className="text-xs text-gray-500 dark:text-gray-400">{i.label}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-gray-800 dark:text-white">{i.value}</span>
                          <span className={`text-[10px] ${i.trend.includes('improving') ? 'text-emerald-500' : 'text-gray-400'}`}>{i.trend}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </GlowCard>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
