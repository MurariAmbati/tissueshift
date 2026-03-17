'use client';

import { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Html } from '@react-three/drei';
import * as THREE from 'three';

const SUBTYPE_COLORS: Record<string, string> = {
  LumA: '#3b82f6',
  LumB: '#6366f1',
  Her2: '#ec4899',
  Basal: '#ef4444',
  Normal: '#10b981',
};

interface ManifoldPoint {
  id: string;
  position: [number, number, number];
  subtype: string;
  confidence: number;
}

interface TissueManifoldProps {
  points?: ManifoldPoint[];
  onPointClick?: (point: ManifoldPoint) => void;
  selectedPoint?: string | null;
}

function ManifoldPoints({
  points,
  onPointClick,
  selectedPoint,
}: {
  points: ManifoldPoint[];
  onPointClick?: (p: ManifoldPoint) => void;
  selectedPoint?: string | null;
}) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  const { colorArray, scaleArray } = useMemo(() => {
    const colors = new Float32Array(points.length * 3);
    const scales = new Float32Array(points.length);

    points.forEach((point, i) => {
      const color = new THREE.Color(SUBTYPE_COLORS[point.subtype] || '#888888');
      colors[i * 3] = color.r;
      colors[i * 3 + 1] = color.g;
      colors[i * 3 + 2] = color.b;
      scales[i] = point.confidence * 0.08 + 0.02;
    });

    return { colorArray: colors, scaleArray: scales };
  }, [points]);

  useFrame(() => {
    if (!meshRef.current) return;

    points.forEach((point, i) => {
      dummy.position.set(...point.position);
      const scale = point.id === selectedPoint ? scaleArray[i] * 2 : scaleArray[i];
      dummy.scale.setScalar(scale);
      dummy.updateMatrix();
      meshRef.current!.setMatrixAt(i, dummy.matrix);
    });

    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, points.length]}
      onClick={(e) => {
        if (onPointClick && e.instanceId !== undefined) {
          onPointClick(points[e.instanceId]);
        }
      }}
    >
      <sphereGeometry args={[1, 16, 16]} />
      <meshStandardMaterial vertexColors />
      <instancedBufferAttribute
        attach="geometry-attributes-color"
        args={[colorArray, 3]}
      />
    </instancedMesh>
  );
}

function SubtypeLabels() {
  const labels = Object.entries(SUBTYPE_COLORS);
  return (
    <Html position={[0, 3, 0]} center>
      <div className="flex gap-4 rounded-lg bg-black/70 px-4 py-2 backdrop-blur">
        {labels.map(([name, color]) => (
          <div key={name} className="flex items-center gap-1.5 text-xs text-white">
            <div
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: color }}
            />
            {name}
          </div>
        ))}
      </div>
    </Html>
  );
}

export default function TissueManifold({
  points = [],
  onPointClick,
  selectedPoint,
}: TissueManifoldProps) {
  // Generate demo points if none provided
  const demoPoints = useMemo(() => {
    if (points.length > 0) return points;

    const subtypes = Object.keys(SUBTYPE_COLORS);
    const centers: Record<string, [number, number, number]> = {
      LumA: [-1.5, 0, -1],
      LumB: [-0.5, 0.5, -0.5],
      Her2: [1, 1, 0],
      Basal: [2, -0.5, 1],
      Normal: [-2, -1, 1],
    };

    const generated: ManifoldPoint[] = [];
    subtypes.forEach((subtype) => {
      const center = centers[subtype];
      for (let i = 0; i < 50; i++) {
        generated.push({
          id: `${subtype}_${i}`,
          position: [
            center[0] + (Math.random() - 0.5) * 1.2,
            center[1] + (Math.random() - 0.5) * 1.2,
            center[2] + (Math.random() - 0.5) * 1.2,
          ],
          subtype,
          confidence: 0.6 + Math.random() * 0.4,
        });
      }
    });
    return generated;
  }, [points]);

  return (
    <div className="relative h-[500px] w-full rounded-xl border border-white/10 bg-black/30">
      <Canvas camera={{ position: [5, 3, 5], fov: 50 }}>
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} />
        <ManifoldPoints
          points={demoPoints}
          onPointClick={onPointClick}
          selectedPoint={selectedPoint}
        />
        <SubtypeLabels />
        <OrbitControls enableDamping dampingFactor={0.05} />
        <gridHelper args={[10, 10, '#333', '#222']} />
      </Canvas>
      <div className="absolute bottom-4 left-4 text-xs text-[var(--text-secondary)]">
        Tissue State Manifold — UMAP 3D projection
      </div>
    </div>
  );
}
