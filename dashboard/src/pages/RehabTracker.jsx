import { useState, useEffect, useRef, useCallback } from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import GlowCard from '../components/GlowCard';
import PulseRing from '../components/PulseRing';
import AnimatedCounter from '../components/AnimatedCounter';

/* ── Prescribed exercise programs ───────────────────────────────── */
const PROGRAMS = [
  {
    id: 'upper-chemo', name: 'Upper Body — Chemo Recovery',
    target: 'Post-chemotherapy lymphedema prevention & shoulder mobility',
    exercises: [
      { name: 'Wall Push-ups', sets: 3, reps: 10, icon: 'WP', completed: 3, repsDone: [10, 10, 10], formScores: [92, 88, 95] },
      { name: 'Arm Circles', sets: 2, reps: 15, icon: 'AC', completed: 2, repsDone: [15, 15], formScores: [97, 96] },
      { name: 'Resistance Band Pull', sets: 3, reps: 12, icon: 'RB', completed: 2, repsDone: [12, 12], formScores: [84, 89] },
      { name: 'Shoulder Press (light)', sets: 2, reps: 10, icon: 'SP', completed: 1, repsDone: [10], formScores: [91] },
      { name: 'Wrist Flexion/Extension', sets: 2, reps: 20, icon: 'WF', completed: 0, repsDone: [], formScores: [] },
    ],
  },
  {
    id: 'cardio-recovery', name: 'Cardio Endurance — Recovery Phase',
    target: 'Rebuild cardiovascular fitness during treatment',
    exercises: [
      { name: 'Treadmill Walk (3.0mph)', sets: 1, reps: 1, icon: 'TW', completed: 1, repsDone: [1], formScores: [96], isDuration: true, durationMin: 20 },
      { name: 'Stationary Bike', sets: 1, reps: 1, icon: 'SB', completed: 1, repsDone: [1], formScores: [93], isDuration: true, durationMin: 15 },
      { name: 'Step-ups (6")', sets: 3, reps: 10, icon: 'SU', completed: 2, repsDone: [10, 10], formScores: [87, 90] },
      { name: 'Seated Marching', sets: 2, reps: 30, icon: 'SM', completed: 0, repsDone: [], formScores: [] },
    ],
  },
  {
    id: 'flexibility', name: 'Flexibility & Balance — Fall Prevention',
    target: 'Address neuropathy-related balance deficits',
    exercises: [
      { name: 'Standing Balance (one leg)', sets: 3, reps: 1, icon: 'SB', completed: 3, repsDone: [1, 1, 1], formScores: [78, 82, 85], isDuration: true, durationSec: 30 },
      { name: 'Heel-Toe Walk', sets: 2, reps: 1, icon: 'HT', completed: 2, repsDone: [1, 1], formScores: [88, 91], isDuration: true, durationMin: 2 },
      { name: 'Seated Hamstring Stretch', sets: 2, reps: 1, icon: 'HS', completed: 1, repsDone: [1], formScores: [94], isDuration: true, durationSec: 45 },
      { name: 'Cat-Cow Stretch', sets: 2, reps: 10, icon: 'CC', completed: 2, repsDone: [10, 10], formScores: [96, 95] },
      { name: 'Ankle Circles', sets: 2, reps: 15, icon: 'AK', completed: 0, repsDone: [], formScores: [] },
    ],
  },
];

/* ── Canvas: Rep counter with motion trail ───────────────────── */
function RepCounterCanvas({ exercise, setIdx }) {
  const canvasRef = useRef(null);
  const frameRef = useRef(0);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const cw = canvas.offsetWidth;
    const ch = canvas.offsetHeight;
    canvas.width = cw * devicePixelRatio;
    canvas.height = ch * devicePixelRatio;
    ctx.scale(devicePixelRatio, devicePixelRatio);

    ctx.fillStyle = '#0a0a18';
    ctx.fillRect(0, 0, cw, ch);

    const t = performance.now() / 1000;
    const repsDone = exercise.repsDone[setIdx] || 0;
    const total = exercise.reps;
    const formScore = exercise.formScores[setIdx] || 0;

    // Circular progress ring
    const cx = cw / 2, cy = ch / 2, radius = Math.min(cw, ch) * 0.32;

    // Track
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.strokeStyle = '#ffffff10';
    ctx.lineWidth = 12;
    ctx.stroke();

    // Progress arc
    const progress = repsDone / total;
    const startAngle = -Math.PI / 2;
    const endAngle = startAngle + progress * Math.PI * 2;
    const gradient = ctx.createConicGradient(startAngle, cx, cy);
    gradient.addColorStop(0, '#8b5cf6');
    gradient.addColorStop(0.5, '#6366f1');
    gradient.addColorStop(1, '#0ea5e9');

    ctx.beginPath();
    ctx.arc(cx, cy, radius, startAngle, endAngle);
    ctx.strokeStyle = gradient;
    ctx.lineWidth = 12;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Glow at tip
    if (progress > 0) {
      const tipX = cx + Math.cos(endAngle) * radius;
      const tipY = cy + Math.sin(endAngle) * radius;
      const glow = ctx.createRadialGradient(tipX, tipY, 0, tipX, tipY, 20);
      glow.addColorStop(0, '#8b5cf680');
      glow.addColorStop(1, 'transparent');
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(tipX, tipY, 20, 0, Math.PI * 2);
      ctx.fill();
    }

    // Center text
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = 'bold 32px Inter, sans-serif';
    ctx.fillStyle = '#ffffff';
    ctx.fillText(`${repsDone}/${total}`, cx, cy - 8);
    ctx.font = '11px Inter, sans-serif';
    ctx.fillStyle = '#ffffff60';
    ctx.fillText('reps', cx, cy + 18);

    // Form score arc (outer)
    if (formScore > 0) {
      const fRadius = radius + 18;
      const fEnd = startAngle + (formScore / 100) * Math.PI * 2;
      ctx.beginPath();
      ctx.arc(cx, cy, fRadius, startAngle, fEnd);
      ctx.strokeStyle = formScore >= 90 ? '#10b98180' : formScore >= 75 ? '#f59e0b80' : '#f43f5e80';
      ctx.lineWidth = 4;
      ctx.lineCap = 'round';
      ctx.stroke();

      ctx.font = '9px Inter, sans-serif';
      ctx.fillStyle = formScore >= 90 ? '#10b981' : formScore >= 75 ? '#f59e0b' : '#f43f5e';
      ctx.fillText(`Form: ${formScore}%`, cx, cy + radius + 30);
    }

    // Motion trail particles (decorative)
    for (let i = 0; i < 8; i++) {
      const angle = t * 0.8 + i * 0.8;
      const trailR = radius * 0.7;
      const px = cx + Math.cos(angle) * trailR;
      const py = cy + Math.sin(angle) * trailR;
      const a = 0.1 + (i / 8) * 0.2;
      ctx.beginPath();
      ctx.arc(px, py, 2, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(139,92,246,${a})`;
      ctx.fill();
    }

    ctx.textAlign = 'start';
    frameRef.current = requestAnimationFrame(draw);
  }, [exercise, setIdx]);

  useEffect(() => {
    frameRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frameRef.current);
  }, [draw]);

  return <canvas ref={canvasRef} className="w-full" style={{ height: 200 }} />;
}

/* ── Main Page ─────────────────────────────────────────────────── */
export default function RehabTracker() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeProgram, setActiveProgram] = useState(PROGRAMS[0]);
  const [selectedExercise, setSelectedExercise] = useState(null);
  const [selectedSet, setSelectedSet] = useState(0);

  const totalExercises = activeProgram.exercises.length;
  const completedExercises = activeProgram.exercises.filter(e => e.completed >= e.sets).length;
  const totalSets = activeProgram.exercises.reduce((a, e) => a + e.sets, 0);
  const completedSets = activeProgram.exercises.reduce((a, e) => a + e.completed, 0);
  const avgForm = (() => {
    const all = activeProgram.exercises.flatMap(e => e.formScores);
    return all.length ? Math.round(all.reduce((a, b) => a + b, 0) / all.length) : 0;
  })();

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[1600px] mx-auto">
            <div className="mb-6">
              <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
                Rehabilitation Exercise Tracker
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">CV-guided exercise execution — real-time form scoring, rep counting, and progress tracking</p>
            </div>

            {/* Program tabs */}
            <div className="flex gap-2 mb-6 overflow-x-auto no-scrollbar pb-1">
              {PROGRAMS.map(p => (
                <button
                  key={p.id}
                  onClick={() => { setActiveProgram(p); setSelectedExercise(null); }}
                  className={`flex-shrink-0 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                    activeProgram.id === p.id
                      ? 'bg-violet-500 text-white shadow-lg shadow-violet-500/30'
                      : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700/60 hover:border-violet-300'
                  }`}
                >
                  {p.name}
                </button>
              ))}
            </div>

            {/* Summary row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <GlowCard glowColor="violet" className="!p-4 text-center">
                <div className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">Exercises</div>
                <div className="text-2xl font-extrabold text-gray-800 dark:text-white">{completedExercises}/{totalExercises}</div>
              </GlowCard>
              <GlowCard glowColor="sky" className="!p-4 text-center">
                <div className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">Sets Completed</div>
                <div className="text-2xl font-extrabold text-gray-800 dark:text-white">{completedSets}/{totalSets}</div>
              </GlowCard>
              <GlowCard glowColor="emerald" className="!p-4 text-center">
                <div className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">Avg Form Score</div>
                <div className={`text-2xl font-extrabold ${avgForm >= 90 ? 'text-emerald-500' : avgForm >= 75 ? 'text-amber-500' : 'text-rose-500'}`}>{avgForm}%</div>
              </GlowCard>
              <GlowCard glowColor="amber" className="!p-4 text-center">
                <div className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">Session Progress</div>
                <div className="text-2xl font-extrabold text-gray-800 dark:text-white">{Math.round((completedSets / totalSets) * 100)}%</div>
              </GlowCard>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              {/* Exercise list */}
              <div className="xl:col-span-2">
                <GlowCard glowColor="violet" className="!p-4">
                  <div className="mb-3">
                    <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100">{activeProgram.name}</h3>
                    <p className="text-xs text-gray-400 mt-0.5">{activeProgram.target}</p>
                  </div>
                  <div className="space-y-3">
                    {activeProgram.exercises.map((ex, ei) => {
                      const done = ex.completed >= ex.sets;
                      const inProgress = ex.completed > 0 && !done;
                      return (
                        <button
                          key={ex.name}
                          onClick={() => { setSelectedExercise(ex); setSelectedSet(Math.min(ex.completed, ex.sets - 1)); }}
                          className={`w-full flex items-center gap-4 p-4 rounded-xl text-left transition-all border ${
                            selectedExercise?.name === ex.name
                              ? 'bg-violet-50 dark:bg-violet-900/20 border-violet-400 dark:border-violet-500'
                              : 'bg-white dark:bg-gray-800/50 border-gray-200 dark:border-gray-700/60 hover:border-violet-300'
                          }`}
                        >
                          <span className="text-xs font-bold text-violet-600 dark:text-violet-400 bg-violet-50 dark:bg-violet-500/10 w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0">{ex.icon}</span>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-bold text-gray-800 dark:text-gray-100">{ex.name}</span>
                              {done && <span className="text-emerald-500 text-sm">✓</span>}
                              {inProgress && <PulseRing color="violet" size="sm" />}
                            </div>
                            <div className="text-xs text-gray-400 mt-0.5">
                              {ex.isDuration
                                ? `${ex.durationMin ? ex.durationMin + ' min' : ex.durationSec + 's'} × ${ex.sets} set${ex.sets > 1 ? 's' : ''}`
                                : `${ex.reps} reps × ${ex.sets} sets`}
                            </div>
                            {/* Set progress dots */}
                            <div className="flex gap-1 mt-2">
                              {Array.from({ length: ex.sets }).map((_, si) => (
                                <div
                                  key={si}
                                  className={`h-1.5 flex-1 rounded-full ${
                                    si < ex.completed
                                      ? ex.formScores[si] >= 90 ? 'bg-emerald-500' : ex.formScores[si] >= 75 ? 'bg-amber-500' : 'bg-rose-500'
                                      : 'bg-gray-200 dark:bg-gray-700'
                                  }`}
                                />
                              ))}
                            </div>
                          </div>
                          <div className="text-right flex-shrink-0">
                            <div className="text-lg font-bold text-gray-800 dark:text-white">{ex.completed}/{ex.sets}</div>
                            <div className="text-[10px] text-gray-400">sets</div>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </GlowCard>
              </div>

              {/* Right: Detail panel */}
              <div className="space-y-4">
                {selectedExercise ? (
                  <>
                    <GlowCard glowColor="indigo" noPad className="overflow-hidden">
                      <div className="p-4 pb-2">
                        <div className="flex items-center justify-between">
                          <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100">{selectedExercise.icon} {selectedExercise.name}</h3>
                          <PulseRing color="violet" size="sm" label="CV Active" />
                        </div>
                        <div className="flex gap-1 mt-2">
                          {Array.from({ length: selectedExercise.sets }).map((_, si) => (
                            <button
                              key={si}
                              onClick={() => setSelectedSet(si)}
                              className={`px-2 py-0.5 rounded text-[10px] font-semibold transition-colors ${
                                selectedSet === si
                                  ? 'bg-violet-500 text-white'
                                  : si < selectedExercise.completed
                                    ? 'bg-emerald-500/20 text-emerald-600'
                                    : 'bg-gray-200 dark:bg-gray-700 text-gray-400'
                              }`}
                            >
                              Set {si + 1}
                            </button>
                          ))}
                        </div>
                      </div>
                      {selectedSet < selectedExercise.completed ? (
                        <RepCounterCanvas exercise={selectedExercise} setIdx={selectedSet} />
                      ) : (
                        <div className="h-[200px] flex items-center justify-center text-gray-400 text-sm">
                          Not started yet
                        </div>
                      )}
                    </GlowCard>

                    {/* Form breakdown */}
                    {selectedExercise.formScores.length > 0 && (
                      <GlowCard glowColor="emerald" className="!p-4">
                        <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">Form Analysis by Set</h3>
                        <div className="space-y-2">
                          {selectedExercise.formScores.map((score, si) => (
                            <div key={si} className="flex items-center gap-2">
                              <span className="text-xs text-gray-400 w-10">Set {si + 1}</span>
                              <div className="flex-1 h-2 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                                <div
                                  className="h-full rounded-full transition-all duration-500"
                                  style={{
                                    width: `${score}%`,
                                    backgroundColor: score >= 90 ? '#10b981' : score >= 75 ? '#f59e0b' : '#f43f5e',
                                  }}
                                />
                              </div>
                              <span className={`text-xs font-bold tabular-nums w-10 text-right ${score >= 90 ? 'text-emerald-500' : score >= 75 ? 'text-amber-500' : 'text-rose-500'}`}>{score}%</span>
                            </div>
                          ))}
                        </div>
                      </GlowCard>
                    )}

                    {/* CV Feedback */}
                    <GlowCard glowColor="sky" className="!p-4">
                      <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-3">AI Coach Feedback</h3>
                      <div className="space-y-2 text-xs">
                        <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-700 dark:text-emerald-300">
                          Good shoulder alignment throughout movement
                        </div>
                        <div className="p-2 rounded-lg bg-amber-500/10 text-amber-700 dark:text-amber-300">
                          Slight elbow flare on reps 7-10 — try keeping elbows closer to body
                        </div>
                        <div className="p-2 rounded-lg bg-sky-500/10 text-sky-700 dark:text-sky-300">
                          Pace is consistent — consider increasing resistance next session
                        </div>
                      </div>
                    </GlowCard>
                  </>
                ) : (
                  <GlowCard glowColor="violet" className="!p-6 text-center">
                    <h3 className="text-sm font-bold text-gray-800 dark:text-gray-100 mb-1">Select an Exercise</h3>
                    <p className="text-xs text-gray-400">Click any exercise to see its CV-tracked progress, form scores, and AI coaching feedback.</p>
                  </GlowCard>
                )}
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
