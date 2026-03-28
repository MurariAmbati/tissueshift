import { useState, useEffect, useRef, useCallback } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import GlowCard from '../components/GlowCard';
import PulseRing from '../components/PulseRing';
import AnimatedCounter from '../components/AnimatedCounter';
import Sparkline from '../components/Sparkline';

/* ── Patient wellness check-in data ─────────────────────────────── */
const PATIENTS = [
  {
    id: 'P-2846', name: 'Rachel Adams', age: 39, subtype: 'Basal-like',
    avatar: 'RA', riskLevel: 'high',
    currentActivity: 'Resistance Band — Upper Body',
    activityIcon: 'RB',
    checkedInAt: '10:32 AM',
    heartRate: 124, spo2: 97, steps: 4821, calories: 342,
    fatigue: 3, pain: 2, mood: 'positive',
    poseKeypoints: { head: [0.5, 0.12], lShoulder: [0.38, 0.25], rShoulder: [0.62, 0.25], lElbow: [0.28, 0.38], rElbow: [0.72, 0.35], lWrist: [0.22, 0.26], rWrist: [0.78, 0.28], lHip: [0.42, 0.55], rHip: [0.58, 0.55], lKnee: [0.40, 0.72], rKnee: [0.60, 0.72], lAnkle: [0.40, 0.90], rAnkle: [0.60, 0.90] },
    exerciseHistory: [65, 72, 58, 80, 75, 90, 85, 92, 88, 95, 78, 82, 91, 87, 94, 89, 96, 93, 88, 97],
    weeklyMinutes: [120, 135, 110, 145, 160, 130, 155],
    complianceRate: 94,
    treatmentPhase: 'Cycle 3/6 — AC-T',
  },
  {
    id: 'P-1923', name: 'Jane Doe', age: 58, subtype: 'Luminal A',
    avatar: 'JD', riskLevel: 'low',
    currentActivity: 'Walking — Outdoor Track',
    activityIcon: 'WK',
    checkedInAt: '09:15 AM',
    heartRate: 88, spo2: 99, steps: 6340, calories: 218,
    fatigue: 1, pain: 0, mood: 'excellent',
    poseKeypoints: { head: [0.5, 0.12], lShoulder: [0.40, 0.24], rShoulder: [0.60, 0.24], lElbow: [0.35, 0.38], rElbow: [0.65, 0.40], lWrist: [0.30, 0.50], rWrist: [0.70, 0.48], lHip: [0.43, 0.54], rHip: [0.57, 0.54], lKnee: [0.41, 0.72], rKnee: [0.59, 0.72], lAnkle: [0.39, 0.90], rAnkle: [0.61, 0.90] },
    exerciseHistory: [70, 75, 78, 82, 80, 85, 88, 84, 90, 87, 92, 89, 91, 94, 88, 90, 95, 93, 91, 96],
    weeklyMinutes: [150, 165, 140, 170, 180, 155, 175],
    complianceRate: 98,
    treatmentPhase: 'Post-Surgery — Maintenance',
  },
  {
    id: 'P-3102', name: 'Mary Smith', age: 47, subtype: 'HER2+',
    avatar: 'MS', riskLevel: 'moderate',
    currentActivity: 'Yoga — Gentle Recovery',
    activityIcon: 'YG',
    checkedInAt: '11:05 AM',
    heartRate: 72, spo2: 98, steps: 2150, calories: 128,
    fatigue: 4, pain: 3, mood: 'neutral',
    poseKeypoints: { head: [0.5, 0.15], lShoulder: [0.35, 0.28], rShoulder: [0.65, 0.28], lElbow: [0.22, 0.28], rElbow: [0.78, 0.28], lWrist: [0.15, 0.28], rWrist: [0.85, 0.28], lHip: [0.42, 0.55], rHip: [0.58, 0.55], lKnee: [0.38, 0.75], rKnee: [0.62, 0.75], lAnkle: [0.35, 0.90], rAnkle: [0.65, 0.90] },
    exerciseHistory: [40, 45, 50, 42, 55, 48, 60, 52, 58, 65, 55, 62, 70, 58, 65, 72, 60, 68, 75, 62],
    weeklyMinutes: [80, 95, 70, 105, 90, 100, 85],
    complianceRate: 82,
    treatmentPhase: 'Cycle 5/6 — TCH',
  },
  {
    id: 'P-0871', name: 'Alice Chen', age: 62, subtype: 'Luminal B',
    avatar: 'AC', riskLevel: 'moderate',
    currentActivity: 'Stationary Bike — Low Intensity',
    activityIcon: 'BK',
    checkedInAt: '08:45 AM',
    heartRate: 96, spo2: 98, steps: 1820, calories: 195,
    fatigue: 2, pain: 1, mood: 'positive',
    poseKeypoints: { head: [0.5, 0.15], lShoulder: [0.38, 0.27], rShoulder: [0.62, 0.27], lElbow: [0.32, 0.40], rElbow: [0.68, 0.40], lWrist: [0.35, 0.50], rWrist: [0.65, 0.50], lHip: [0.42, 0.55], rHip: [0.58, 0.55], lKnee: [0.38, 0.68], rKnee: [0.62, 0.72], lAnkle: [0.36, 0.85], rAnkle: [0.64, 0.88] },
    exerciseHistory: [50, 55, 60, 58, 65, 62, 70, 68, 72, 75, 70, 78, 65, 80, 72, 76, 80, 84, 78, 82],
    weeklyMinutes: [100, 120, 90, 130, 110, 125, 115],
    complianceRate: 90,
    treatmentPhase: 'Adjuvant Endocrine — Month 8',
  },
];

const SKELETON_BONES = [
  ['head', 'lShoulder'], ['head', 'rShoulder'],
  ['lShoulder', 'rShoulder'], ['lShoulder', 'lElbow'], ['lElbow', 'lWrist'],
  ['rShoulder', 'rElbow'], ['rElbow', 'rWrist'],
  ['lShoulder', 'lHip'], ['rShoulder', 'rHip'], ['lHip', 'rHip'],
  ['lHip', 'lKnee'], ['lKnee', 'lAnkle'],
  ['rHip', 'rKnee'], ['rKnee', 'rAnkle'],
];

const riskColors = { low: '#10b981', moderate: '#f59e0b', high: '#f43f5e' };
const moodLabel = { excellent: 'Excellent', positive: 'Good', neutral: 'Neutral', fatigued: 'Tired', low: 'Low' };

/* ── Pose Skeleton Canvas ─────────────────────────────────────── */
function PoseCanvas({ keypoints, color = '#8b5cf6', activity }) {
  const canvasRef = useRef(null);
  const frameRef = useRef(0);
  const tRef = useRef(0);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const cw = canvas.offsetWidth;
    const ch = canvas.offsetHeight;
    canvas.width = cw * devicePixelRatio;
    canvas.height = ch * devicePixelRatio;
    ctx.scale(devicePixelRatio, devicePixelRatio);

    ctx.fillStyle = '#0d0d1a';
    ctx.fillRect(0, 0, cw, ch);

    // Grid floor
    ctx.strokeStyle = '#ffffff08';
    ctx.lineWidth = 0.5;
    for (let i = 0; i < 20; i++) {
      const y = ch * 0.5 + i * 15;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(cw, y);
      ctx.stroke();
    }
    for (let i = 0; i < 20; i++) {
      const x = i * (cw / 20);
      ctx.beginPath();
      ctx.moveTo(x, ch * 0.5);
      ctx.lineTo(x + (x - cw / 2) * 0.3, ch);
      ctx.stroke();
    }

    const t = performance.now() / 1000;
    tRef.current = t;

    // Breathing animation
    const breathe = Math.sin(t * 1.5) * 0.008;

    // Draw bones
    ctx.lineCap = 'round';
    for (const [a, b] of SKELETON_BONES) {
      const pa = keypoints[a];
      const pb = keypoints[b];
      if (!pa || !pb) continue;
      const ax = pa[0] * cw, ay = (pa[1] + breathe) * ch;
      const bx = pb[0] * cw, by = (pb[1] + breathe) * ch;

      // Glow line
      ctx.beginPath();
      ctx.moveTo(ax, ay);
      ctx.lineTo(bx, by);
      ctx.strokeStyle = color + '60';
      ctx.lineWidth = 6;
      ctx.stroke();

      // Core line
      ctx.beginPath();
      ctx.moveTo(ax, ay);
      ctx.lineTo(bx, by);
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.5;
      ctx.stroke();
    }

    // Draw joints
    for (const [key, [jx, jy]] of Object.entries(keypoints)) {
      const px = jx * cw;
      const py = (jy + breathe) * ch;
      const isHead = key === 'head';

      // Glow
      const glow = ctx.createRadialGradient(px, py, 0, px, py, isHead ? 18 : 10);
      glow.addColorStop(0, color + '50');
      glow.addColorStop(1, 'transparent');
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(px, py, isHead ? 18 : 10, 0, Math.PI * 2);
      ctx.fill();

      // Joint dot
      ctx.beginPath();
      ctx.arc(px, py, isHead ? 8 : 4, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.shadowColor = color;
      ctx.shadowBlur = 8;
      ctx.fill();
      ctx.shadowBlur = 0;
    }

    // Activity label
    ctx.font = 'bold 11px Inter, sans-serif';
    ctx.fillStyle = '#ffffff40';
    ctx.textAlign = 'center';
    ctx.fillText('CV Pose Estimation — Live', cw / 2, ch - 12);
    ctx.textAlign = 'start';

    // Confidence scores floating
    ctx.font = '9px Inter, sans-serif';
    ctx.fillStyle = '#10b981';
    ctx.fillText(`Conf: ${(0.92 + Math.sin(t) * 0.03).toFixed(2)}`, 8, 16);
    ctx.fillText(`FPS: 30`, 8, 28);

    frameRef.current = requestAnimationFrame(draw);
  }, [keypoints, color]);

  useEffect(() => {
    frameRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frameRef.current);
  }, [draw]);

  return <canvas ref={canvasRef} className="w-full rounded-xl" style={{ height: 220 }} />;
}

/* ── Main Page ─────────────────────────────────────────────────── */
export default function PatientWellness() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState(PATIENTS[0]);
  const [liveHR, setLiveHR] = useState(selectedPatient.heartRate);
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const iv = setInterval(() => {
      setLiveHR(prev => Math.max(60, Math.min(160, prev + Math.round((Math.random() - 0.5) * 4))));
      setTime(new Date());
    }, 1500);
    return () => clearInterval(iv);
  }, [selectedPatient]);

  useEffect(() => {
    setLiveHR(selectedPatient.heartRate);
  }, [selectedPatient]);

  const fatigueLabels = ['None', 'Minimal', 'Mild', 'Moderate', 'Significant', 'Severe'];
  const painLabels = ['None', 'Mild', 'Moderate', 'Significant', 'Severe', 'Extreme'];

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[1600px] mx-auto">
            <div className="flex flex-wrap items-end justify-between gap-4 mb-8">
              <div>
                <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
                  Patient Wellness Monitor
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">CV-powered exercise tracking, real-time vitals, and rehabilitation compliance</p>
              </div>
              <div className="flex items-center gap-2">
                <PulseRing color="emerald" size="sm" label="Live Feed" />
                <span className="text-xs text-gray-400 tabular-nums">{time.toLocaleTimeString()}</span>
              </div>
            </div>

            {/* Patient selector strip */}
            <div className="flex gap-3 mb-6 overflow-x-auto pb-2 no-scrollbar">
              {PATIENTS.map((p) => (
                <button
                  key={p.id}
                  onClick={() => setSelectedPatient(p)}
                  className={`flex-shrink-0 flex items-center gap-3 px-4 py-3 rounded-xl border transition-all duration-200 ${
                    selectedPatient.id === p.id
                      ? 'bg-white dark:bg-gray-800 border-violet-400 dark:border-violet-500 shadow-lg shadow-violet-500/10'
                      : 'bg-white/50 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700/60 hover:border-violet-300'
                  }`}
                >
                  <span className="text-sm font-bold text-violet-600 dark:text-violet-400 bg-violet-50 dark:bg-violet-500/10 w-8 h-8 rounded-full flex items-center justify-center">{p.avatar}</span>
                  <div className="text-left">
                    <div className="text-sm font-semibold text-gray-800 dark:text-gray-100">{p.name}</div>
                    <div className="flex items-center gap-2 text-[10px] text-gray-400">
                      <span>{p.id}</span>
                      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: riskColors[p.riskLevel] }} />
                      <span>{p.activityIcon} {p.currentActivity.split('—')[0].trim()}</span>
                    </div>
                  </div>
                </button>
              ))}
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              {/* Left: CV Pose + Vitals */}
              <div className="xl:col-span-2 space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Pose estimation */}
                  <GlowCard glowColor="violet" noPad className="overflow-hidden">
                    <div className="p-4 pb-2">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100">Pose Estimation</h3>
                        <PulseRing color="emerald" size="sm" label="Tracking" />
                      </div>
                    </div>
                    <PoseCanvas keypoints={selectedPatient.poseKeypoints} color={riskColors[selectedPatient.riskLevel] || '#8b5cf6'} activity={selectedPatient.currentActivity} />
                  </GlowCard>

                  {/* Current activity details */}
                  <GlowCard glowColor="teal" className="!p-4">
                    <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Current Session</h3>
                    <div className="flex items-center gap-3 mb-4 p-3 rounded-xl bg-teal-50 dark:bg-teal-500/10">
                      <span className="text-sm font-bold text-teal-600 dark:text-teal-400 bg-teal-50 dark:bg-teal-500/10 w-10 h-10 rounded-lg flex items-center justify-center">{selectedPatient.activityIcon}</span>
                      <div>
                        <div className="text-sm font-bold text-gray-800 dark:text-gray-100">{selectedPatient.currentActivity}</div>
                        <div className="text-xs text-gray-400">Checked in {selectedPatient.checkedInAt}</div>
                      </div>
                    </div>

                    {/* Real-time vitals */}
                    <div className="grid grid-cols-2 gap-3 mb-4">
                      <div className="text-center p-2 rounded-lg bg-rose-500/10">
                        <div className="text-[10px] text-gray-400 mb-0.5">Heart Rate</div>
                        <div className="text-xl font-extrabold text-rose-500 tabular-nums">
                          <AnimatedCounter value={liveHR} duration={800} /> <span className="text-xs font-normal">bpm</span>
                        </div>
                      </div>
                      <div className="text-center p-2 rounded-lg bg-sky-500/10">
                        <div className="text-[10px] text-gray-400 mb-0.5">SpO₂</div>
                        <div className="text-xl font-extrabold text-sky-500 tabular-nums">{selectedPatient.spo2}%</div>
                      </div>
                      <div className="text-center p-2 rounded-lg bg-amber-500/10">
                        <div className="text-[10px] text-gray-400 mb-0.5">Steps</div>
                        <div className="text-xl font-extrabold text-amber-500 tabular-nums">{selectedPatient.steps.toLocaleString()}</div>
                      </div>
                      <div className="text-center p-2 rounded-lg bg-emerald-500/10">
                        <div className="text-[10px] text-gray-400 mb-0.5">Calories</div>
                        <div className="text-xl font-extrabold text-emerald-500 tabular-nums">{selectedPatient.calories}</div>
                      </div>
                    </div>

                    {/* PROs */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">Fatigue Level</span>
                        <div className="flex items-center gap-1">
                          <div className="w-20 h-1.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                            <div className="h-full rounded-full bg-amber-500" style={{ width: `${(selectedPatient.fatigue / 5) * 100}%` }} />
                          </div>
                          <span className="text-gray-600 dark:text-gray-300 font-medium">{fatigueLabels[selectedPatient.fatigue]}</span>
                        </div>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">Pain</span>
                        <div className="flex items-center gap-1">
                          <div className="w-20 h-1.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                            <div className="h-full rounded-full bg-rose-500" style={{ width: `${(selectedPatient.pain / 5) * 100}%` }} />
                          </div>
                          <span className="text-gray-600 dark:text-gray-300 font-medium">{painLabels[selectedPatient.pain]}</span>
                        </div>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">Mood</span>
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-200">{moodLabel[selectedPatient.mood]}</span>
                      </div>
                    </div>
                  </GlowCard>
                </div>

                {/* Exercise Trend & Weekly */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <GlowCard glowColor="sky" className="!p-4">
                    <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Exercise Performance Score (20 sessions)</h3>
                    <div className="flex items-end gap-0.5 h-28">
                      {selectedPatient.exerciseHistory.map((v, i) => (
                        <div key={i} className="flex-1 flex flex-col justify-end items-center">
                          <div
                            className="w-full rounded-t transition-all duration-500"
                            style={{
                              height: `${v}%`,
                              backgroundColor: v >= 85 ? '#10b981' : v >= 65 ? '#f59e0b' : '#f43f5e',
                              opacity: 0.7 + (i / 20) * 0.3,
                            }}
                          />
                        </div>
                      ))}
                    </div>
                    <div className="flex justify-between mt-2 text-[10px] text-gray-400">
                      <span>20 sessions ago</span>
                      <span>Latest</span>
                    </div>
                  </GlowCard>

                  <GlowCard glowColor="indigo" className="!p-4">
                    <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Weekly Activity Minutes</h3>
                    <div className="flex items-end gap-2 h-28">
                      {selectedPatient.weeklyMinutes.map((v, i) => {
                        const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
                        const max = Math.max(...selectedPatient.weeklyMinutes);
                        return (
                          <div key={i} className="flex-1 flex flex-col items-center">
                            <div className="w-full flex flex-col justify-end" style={{ height: 100 }}>
                              <div
                                className="w-full rounded-t bg-violet-500 transition-all duration-500"
                                style={{ height: `${(v / max) * 100}%` }}
                              />
                            </div>
                            <div className="text-[10px] text-gray-400 mt-1">{days[i]}</div>
                            <div className="text-[10px] font-bold text-gray-600 dark:text-gray-300">{v}</div>
                          </div>
                        );
                      })}
                    </div>
                    <div className="mt-3 pt-2 border-t border-gray-200 dark:border-gray-700/60 flex justify-between text-xs">
                      <span className="text-gray-400">Weekly Goal: 150 min</span>
                      <span className="font-bold text-emerald-500">{selectedPatient.weeklyMinutes.reduce((a, b) => a + b, 0)} min total</span>
                    </div>
                  </GlowCard>
                </div>
              </div>

              {/* Right sidebar: Full patient card */}
              <div className="space-y-4">
                <GlowCard glowColor="violet" className="!p-4">
                  <div className="flex items-center gap-3 mb-4">
                    <span className="text-lg font-bold text-violet-600 dark:text-violet-400 bg-violet-50 dark:bg-violet-500/10 w-12 h-12 rounded-full flex items-center justify-center">{selectedPatient.avatar}</span>
                    <div>
                      <div className="text-base font-bold text-gray-800 dark:text-gray-100">{selectedPatient.name}</div>
                      <div className="text-xs text-gray-400">{selectedPatient.id} · {selectedPatient.age}y · {selectedPatient.subtype}</div>
                    </div>
                    <span className="ml-auto px-2 py-0.5 rounded-full text-[10px] font-bold" style={{ backgroundColor: riskColors[selectedPatient.riskLevel] + '20', color: riskColors[selectedPatient.riskLevel] }}>
                      {selectedPatient.riskLevel.toUpperCase()} RISK
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 p-2 rounded-lg bg-gray-50 dark:bg-gray-900/50">
                    <span className="font-semibold text-gray-700 dark:text-gray-200">Treatment:</span> {selectedPatient.treatmentPhase}
                  </div>
                </GlowCard>

                {/* Compliance */}
                <GlowCard glowColor="emerald" className="!p-4 text-center">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">Rehab Compliance</h3>
                  <div className="relative w-24 h-24 mx-auto mb-2">
                    <svg className="w-24 h-24 -rotate-90" viewBox="0 0 100 100">
                      <circle cx="50" cy="50" r="42" fill="none" stroke="#e5e7eb" strokeWidth="8" className="dark:stroke-gray-700" />
                      <circle
                        cx="50" cy="50" r="42" fill="none"
                        stroke={selectedPatient.complianceRate >= 90 ? '#10b981' : selectedPatient.complianceRate >= 70 ? '#f59e0b' : '#f43f5e'}
                        strokeWidth="8" strokeLinecap="round"
                        strokeDasharray={`${selectedPatient.complianceRate * 2.64} 264`}
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-xl font-extrabold text-gray-800 dark:text-gray-100">{selectedPatient.complianceRate}%</span>
                    </div>
                  </div>
                  <div className="text-xs text-gray-400">of prescribed exercise sessions completed</div>
                </GlowCard>

                {/* CV Analysis */}
                <GlowCard glowColor="sky" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">CV Movement Analysis</h3>
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Range of Motion</span>
                      <span className="font-bold text-emerald-500">Normal</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Gait Symmetry</span>
                      <span className="font-bold text-emerald-500">96%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Rep Accuracy</span>
                      <span className="font-bold text-sky-500">88%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Form Score</span>
                      <span className="font-bold text-violet-500">91/100</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Tremor Detection</span>
                      <span className="font-bold text-emerald-500">None</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Fall Risk</span>
                      <span className="font-bold text-emerald-500">Low</span>
                    </div>
                  </div>
                </GlowCard>

                {/* Recent Check-ins */}
                <GlowCard glowColor="amber" className="!p-4">
                  <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Recent Check-ins</h3>
                  <div className="space-y-2">
                    {[
                      { date: 'Today', activity: 'Resistance Band', duration: '35 min', score: 94 },
                      { date: 'Yesterday', activity: 'Walking', duration: '45 min', score: 97 },
                      { date: 'Mar 26', activity: 'Yoga', duration: '30 min', score: 88 },
                      { date: 'Mar 25', activity: 'Stationary Bike', duration: '25 min', score: 91 },
                      { date: 'Mar 24', activity: 'Resistance Band', duration: '30 min', score: 85 },
                    ].map((ci) => (
                      <div key={ci.date} className="flex items-center gap-2 text-xs">
                        <span className="text-gray-400 w-16">{ci.date}</span>
                        <span className="flex-1 text-gray-700 dark:text-gray-200">{ci.activity}</span>
                        <span className="text-gray-400">{ci.duration}</span>
                        <span className={`font-bold tabular-nums ${ci.score >= 90 ? 'text-emerald-500' : ci.score >= 75 ? 'text-amber-500' : 'text-rose-500'}`}>{ci.score}</span>
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
