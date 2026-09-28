"use client";

import { Canvas, useFrame, type ThreeEvent } from "@react-three/fiber";
import { useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { SpinControls, SpinRig, Tooltip, useSpin, type SpinConfig, type SpinView } from "./Spin";

export type CoreModule = { name: string; bytes: number; files: number; tests: number };

const ACCENT = "#5fb8ea";
const RADIUS = 2.6;
const SPIN: SpinConfig = {
  zoom: { min: 5.5, max: 13, start: 8.5 },
  tilt: { min: -0.4, max: 0.8, start: 0.3 },
  rotY: 0.2,
  height: 1.4,
  lookY: 0,
};

const kb = (b: number) => (b >= 1024 ? `${(b / 1024).toFixed(1)} KB` : `${b} B`);

export default function OrchestratorCore({
  modules,
  selected,
  onPick,
  still,
}: {
  modules: CoreModule[];
  selected: string | null;
  onPick: (name: string) => void;
  still: boolean;
}) {
  const spin = useSpin(SPIN);
  const [hover, setHover] = useState<{ label: string; x: number; y: number } | null>(null);

  return (
    <div {...spin.wrapProps}>
      <Canvas
        frameloop={spin.visible ? "always" : "never"}
        dpr={[1, 1.75]}
        camera={{ position: [0, SPIN.height, SPIN.zoom.start], fov: 42 }}
        gl={{ antialias: true, alpha: true }}
        onPointerMissed={() => setHover(null)}
      >
        <fog attach="fog" args={["#06070a", 9, 20]} />
        <ambientLight intensity={0.45} />
        <directionalLight position={[4, 7, 5]} intensity={1.2} />
        <pointLight position={[0, 0, 0]} intensity={8} distance={5} color={ACCENT} />
        <SpinRig view={spin.view} still={still || !!hover} cfg={SPIN} />
        <Ring
          modules={modules}
          selected={selected}
          view={spin.view}
          still={still}
          onPick={onPick}
          tip={(label, x = 0, y = 0) => {
            spin.view.current.lastInput = performance.now();
            setHover(label ? { label, x, y } : null);
          }}
        />
      </Canvas>
      {hover && !spin.dragging && (
        <Tooltip at={hover} width={spin.wrap.current?.clientWidth ?? 0}>
          {hover.label}
        </Tooltip>
      )}
      <SpinControls spin={spin} />
    </div>
  );
}

function Ring({
  modules,
  selected,
  view,
  still,
  onPick,
  tip,
}: {
  modules: CoreModule[];
  selected: string | null;
  view: React.RefObject<SpinView>;
  still: boolean;
  onPick: (name: string) => void;
  tip: (label: string | null, x?: number, y?: number) => void;
}) {
  const group = useRef<THREE.Group>(null!);
  const core = useRef<THREE.Group>(null!);
  const clock = useRef(0);
  const built = modules.filter((m) => m.bytes > 0);

  useFrame((_, dt) => {
    const v = view.current!;
    group.current.rotation.set(v.rotX, v.rotY, 0);
    clock.current += dt;
    if (!still) core.current.rotation.y += dt * 0.3;
  });

  return (
    <group ref={group}>
      <group
        ref={core}
        onPointerMove={(e: ThreeEvent<PointerEvent>) => {
          e.stopPropagation();
          tip(
            `orchestrator/ · ${built.length} of ${modules.length} modules have code · ${kb(modules.reduce((s, m) => s + m.bytes, 0))}`,
            e.nativeEvent.offsetX,
            e.nativeEvent.offsetY,
          );
        }}
        onPointerOut={() => tip(null)}
      >
        {[-1, 0, 1].flatMap((x) =>
          [-1, 0, 1].map((z) => (
            <mesh key={`${x}${z}`} position={[x * 0.3, 0, z * 0.3]}>
              <boxGeometry args={[0.26, 0.26, 0.26]} />
              <meshStandardMaterial color="#9fdcff" emissive={ACCENT} emissiveIntensity={x === 0 && z === 0 ? 1.4 : 0.4} />
            </mesh>
          )),
        )}
      </group>

      {modules.map((m, i) => {
        const a = (i / modules.length) * Math.PI * 2;
        const pos = new THREE.Vector3(Math.cos(a) * RADIUS, Math.sin(a * 2) * 0.35, Math.sin(a) * RADIUS);
        return (
          <ModuleBlock
            key={m.name}
            m={m}
            pos={pos}
            selected={selected === m.name}
            clock={clock}
            phase={i * 0.45}
            still={still}
            onPick={onPick}
            tip={tip}
          />
        );
      })}
    </group>
  );
}

function ModuleBlock({
  m,
  pos,
  selected,
  clock,
  phase,
  still,
  onPick,
  tip,
}: {
  m: CoreModule;
  pos: THREE.Vector3;
  selected: boolean;
  clock: React.RefObject<number>;
  phase: number;
  still: boolean;
  onPick: (name: string) => void;
  tip: (label: string | null, x?: number, y?: number) => void;
}) {
  const built = m.bytes > 0;
  // Size follows code volume (log scale); an empty module keeps a small hollow footprint.
  const size = built ? 0.28 + Math.log10(m.bytes) * 0.09 : 0.32;
  const edges = useMemo(() => new THREE.EdgesGeometry(new THREE.BoxGeometry(size, size, size)), [size]);
  const spoke = useMemo(() => new THREE.BufferGeometry().setFromPoints([pos.clone().multiplyScalar(-1), new THREE.Vector3()]), [pos]);
  const body = useRef<THREE.Group>(null!);
  const packet = useRef<THREE.Mesh>(null!);

  useFrame((_, dt) => {
    if (!still) body.current.rotation.y += dt * 0.4;
    body.current.scale.setScalar(THREE.MathUtils.damp(body.current.scale.x, selected ? 1.35 : 1, 8, dt));
    if (packet.current) {
      const t = still ? 0.5 : (clock.current! * 0.45 + phase) % 1;
      packet.current.position.copy(pos).multiplyScalar(-(1 - t)); // core -> module, in local space
    }
  });

  const label = built
    ? `${m.name}/ · ${m.files} file${m.files === 1 ? "" : "s"} · ${kb(m.bytes)} · ${m.tests} test file${m.tests === 1 ? "" : "s"} — click for files`
    : `${m.name}/ · empty — not built yet`;

  return (
    <group position={pos}>
      <lineSegments geometry={spoke}>
        <lineBasicMaterial color={ACCENT} transparent opacity={built ? 0.35 : 0.08} />
      </lineSegments>
      {built && (
        <mesh ref={packet}>
          <boxGeometry args={[0.07, 0.07, 0.07]} />
          <meshBasicMaterial color="#d6f1ff" />
        </mesh>
      )}
      <group
        ref={body}
        onPointerMove={(e: ThreeEvent<PointerEvent>) => {
          e.stopPropagation();
          tip(label, e.nativeEvent.offsetX, e.nativeEvent.offsetY);
        }}
        onPointerOut={() => tip(null)}
        onClick={(e: ThreeEvent<MouseEvent>) => {
          e.stopPropagation();
          if (e.delta < 5) onPick(m.name);
        }}
      >
        <mesh>
          <boxGeometry args={[size, size, size]} />
          <meshStandardMaterial
            color={built ? ACCENT : "#4a505b"}
            emissive={built ? ACCENT : "#000000"}
            emissiveIntensity={selected ? 1 : 0.35}
            transparent
            opacity={built ? 0.95 : 0.06}
          />
        </mesh>
        <lineSegments geometry={edges}>
          <lineBasicMaterial color={selected ? "#ffffff" : built ? ACCENT : "#6b7280"} />
        </lineSegments>
      </group>
    </group>
  );
}
