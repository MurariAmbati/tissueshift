import { useEffect, useRef } from 'react';

/**
 * Animated flowing data connection between two points.
 * Creates the visual impression of live data streaming through the system.
 */
export default function DataFlowLine({ from, to, color = '139,92,246', speed = 2, className = '' }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animId;
    let t = 0;

    const draw = () => {
      const cw = canvas.offsetWidth;
      const ch = canvas.offsetHeight;
      canvas.width = cw * devicePixelRatio;
      canvas.height = ch * devicePixelRatio;
      ctx.scale(devicePixelRatio, devicePixelRatio);
      ctx.clearRect(0, 0, cw, ch);

      const x1 = from.x * cw, y1 = from.y * ch;
      const x2 = to.x * cw, y2 = to.y * ch;

      // Static line
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      const cx = (x1 + x2) / 2;
      const cy = Math.min(y1, y2) - 30;
      ctx.quadraticCurveTo(cx, cy, x2, y2);
      ctx.strokeStyle = `rgba(${color}, 0.15)`;
      ctx.lineWidth = 2;
      ctx.stroke();

      // Flowing dot
      t += 0.005 * speed;
      if (t > 1) t = 0;
      const px = (1 - t) * (1 - t) * x1 + 2 * (1 - t) * t * cx + t * t * x2;
      const py = (1 - t) * (1 - t) * y1 + 2 * (1 - t) * t * cy + t * t * y2;

      ctx.beginPath();
      ctx.arc(px, py, 4, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${color}, 0.9)`;
      ctx.shadowColor = `rgba(${color}, 0.6)`;
      ctx.shadowBlur = 12;
      ctx.fill();
      ctx.shadowBlur = 0;

      animId = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(animId);
  }, [from, to, color, speed]);

  return (
    <canvas
      ref={canvasRef}
      className={`absolute inset-0 pointer-events-none ${className}`}
      style={{ width: '100%', height: '100%' }}
    />
  );
}
