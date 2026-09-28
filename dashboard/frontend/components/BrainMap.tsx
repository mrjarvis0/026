"use client";

import { Canvas, useFrame, type ThreeEvent } from "@react-three/fiber";
import { useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { SpinControls, SpinRig, Tooltip, useSpin, type SpinConfig, type SpinView } from "./Spin";

export type MapAgent = { id: string; reads: string[]; writes: string[] };
export type MapSpace = { ns: string; readers: string[]; writers: string[] };

const ACCENT = "#5fb8ea";
const READ = "#7b8a9c";
const SPIN: SpinConfig = {
  zoom: { min: 6, max: 15, start: 10 },
  tilt: { min: -0.5, max: 0.9, start: 0.45 },
  rotY: 0,
  height: 1.3,
  lookY: 0,
};

type Props = {
  agents: MapAgent[];
  spaces: MapSpace[];
  focus: string | null;
  onFocus: (id: string | null) => void;
  still: boolean;
};

export default function BrainMap(props: Props) {
  const spin = useSpin(SPIN);
  const [hover, setHover] = useState<{ label: string; x: number; y: number } | null>(null);
  return (
    <div {...spin.wrapProps}>
      <Canvas
        frameloop={spin.visible ? "always" : "never"}
        dpr={[1, 1.75]}
        camera={{ position: [0, SPIN.height, SPIN.zoom.start], fov: 42 }}
        gl={{ antialias: true, alpha: true }}
        onPointerMissed={() => {
          setHover(null);
          props.onFocus(null);
        }}
      >
        <fog attach="fog" args={["#06070a", 10, 22]} />
        <ambientLight intensity={0.5} />
        <directionalLight position={[4, 7, 5]} intensity={1.1} />
        <SpinRig view={spin.view} still={props.still || !!hover} cfg={SPIN} />
        <Graph
          {...props}
          view={spin.view}
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

const ring = (i: number, n: number, r: number, lift: number) => {
  const a = (i / n) * Math.PI * 2;
  return new THREE.Vector3(Math.cos(a) * r, Math.sin(a * 3) * lift, Math.sin(a) * r);
};

function Graph({
  agents,
  spaces,
  focus,
  onFocus,
  still,
  view,
  tip,
}: Props & { view: React.RefObject<SpinView>; tip: (label: string | null, x?: number, y?: number) => void }) {
  const group = useRef<THREE.Group>(null!);
  const clock = useRef(0);
  const at = useMemo(() => {
    const m = new Map<string, THREE.Vector3>();
    spaces.forEach((s, i) => m.set(s.ns, ring(i, spaces.length, 1.6, 0.35)));
    agents.forEach((a, i) => m.set(a.id, ring(i + 0.5, agents.length, 3.5, 0.6)));
    return m;
  }, [agents, spaces]);
  const edges = useMemo(
    () =>
      agents.flatMap((a) => [
        ...a.writes.map((ns) => ({ agent: a.id, ns, write: true })),
        ...a.reads.filter((ns) => !a.writes.includes(ns)).map((ns) => ({ agent: a.id, ns, write: false })),
      ]),
    [agents],
  );

  useFrame((_, dt) => {
    const v = view.current!;
    group.current.rotation.set(v.rotX, v.rotY, 0);
    clock.current += still ? 0 : dt;
  });

  const lit = (e: { agent: string; ns: string }) => !focus || focus === e.agent || focus === e.ns;
  const bind = (id: string, label: string) => ({
    onPointerMove: (e: ThreeEvent<PointerEvent>) => {
      e.stopPropagation();
      tip(label, e.nativeEvent.offsetX, e.nativeEvent.offsetY);
    },
    onPointerOut: () => tip(null),
    onClick: (e: ThreeEvent<MouseEvent>) => {
      e.stopPropagation();
      if (e.delta < 5) onFocus(focus === id ? null : id);
    },
  });

  return (
    <group ref={group}>
      {edges.map((e, i) => (
        <Edge key={`${e.agent}-${e.ns}`} from={at.get(e.agent)!} to={at.get(e.ns)!} write={e.write} lit={lit(e)} clock={clock} phase={i * 0.31} />
      ))}

      {spaces.map((s) => {
        const orphan = s.writers.length === 0;
        const size = 0.16 + s.readers.length * 0.035;
        const dim = focus && focus !== s.ns && !s.readers.includes(focus) && !s.writers.includes(focus);
        return (
          <mesh
            key={s.ns}
            position={at.get(s.ns)}
            {...bind(
              s.ns,
              `${s.ns} · written by ${s.writers.join(", ") || "nobody — stays empty"} · read by ${s.readers.join(", ") || "nobody"}`,
            )}
          >
            <icosahedronGeometry args={[size, 1]} />
            <meshStandardMaterial
              color={ACCENT}
              emissive={ACCENT}
              emissiveIntensity={focus === s.ns ? 1.2 : 0.45}
              wireframe={orphan}
              transparent
              opacity={dim ? 0.15 : 1}
            />
          </mesh>
        );
      })}

      {agents.map((a) => {
        const silent = a.reads.length + a.writes.length === 0;
        const dim = focus && focus !== a.id && !a.reads.includes(focus) && !a.writes.includes(focus);
        return (
          <mesh
            key={a.id}
            position={at.get(a.id)}
            {...bind(a.id, `${a.id} · reads ${a.reads.join(", ") || "nothing"} · writes ${a.writes.join(", ") || "nothing"}`)}
          >
            <boxGeometry args={[0.32, 0.32, 0.32]} />
            <meshStandardMaterial
              color={silent ? "#2a2e35" : "#9fdcff"}
              emissive={silent ? "#000000" : ACCENT}
              emissiveIntensity={focus === a.id ? 1 : 0.25}
              transparent
              opacity={dim ? 0.15 : 1}
            />
          </mesh>
        );
      })}
    </group>
  );
}

// A write carries data agent → namespace; a read carries it namespace → agent.
function Edge({
  from,
  to,
  write,
  lit,
  clock,
  phase,
}: {
  from: THREE.Vector3;
  to: THREE.Vector3;
  write: boolean;
  lit: boolean;
  clock: React.RefObject<number>;
  phase: number;
}) {
  const geo = useMemo(() => new THREE.BufferGeometry().setFromPoints([from, to]), [from, to]);
  const packet = useRef<THREE.Mesh>(null!);
  useFrame(() => {
    const t = (clock.current! * (write ? 0.5 : 0.3) + phase) % 1;
    packet.current.position.copy(write ? from : to).lerp(write ? to : from, t);
  });
  const color = write ? ACCENT : READ;
  return (
    <>
      <lineSegments geometry={geo}>
        <lineBasicMaterial color={color} transparent opacity={lit ? (write ? 0.7 : 0.28) : 0.04} />
      </lineSegments>
      <mesh ref={packet} visible={lit}>
        <boxGeometry args={write ? [0.07, 0.07, 0.07] : [0.045, 0.045, 0.045]} />
        <meshBasicMaterial color={write ? "#d6f1ff" : READ} />
      </mesh>
    </>
  );
}
