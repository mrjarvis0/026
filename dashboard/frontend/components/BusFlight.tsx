"use client";

import { Canvas, useFrame, type ThreeEvent } from "@react-three/fiber";
import { useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { BUS_STATUS_COLOR as STATUS_COLOR } from "@/lib/status";
import { SpinControls, SpinRig, Tooltip, useSpin, type SpinConfig, type SpinView } from "./Spin";

const ACCENT = "#5fb8ea";
const ORCH = new THREE.Vector3(-3.2, 0, 0);
const GATE_X = -0.9;
const HOP = 0.6; // seconds per leg
const STAGGER = 0.9; // seconds between messages in a replay

const SPIN: SpinConfig = {
  zoom: { min: 6, max: 15, start: 9.5 },
  tilt: { min: -0.5, max: 0.7, start: 0.12 },
  rotY: -0.35,
  height: 0.8,
  lookY: 0,
};

export type Lane = { id: string; onBus: boolean };
export type Flight = { to: string; status: string };

type Props = {
  lanes: Lane[];
  flights: Flight[];
  play: number; // bump to replay
  onPick: (id: string) => void;
  still: boolean;
};

export default function BusFlight({ lanes, flights, play, onPick, still }: Props) {
  const spin = useSpin(SPIN);
  const [hover, setHover] = useState<{ label: string; x: number; y: number } | null>(null);
  const tip = (label: string | null, x = 0, y = 0) => {
    spin.view.current.lastInput = performance.now();
    setHover(label ? { label, x, y } : null);
  };

  return (
    <div {...spin.wrapProps}>
      <Canvas
        frameloop={spin.visible ? "always" : "never"}
        dpr={[1, 1.75]}
        camera={{ position: [0, SPIN.height, SPIN.zoom.start], fov: 42 }}
        gl={{ antialias: true, alpha: true }}
        onPointerMissed={() => setHover(null)}
      >
        <fog attach="fog" args={["#06070a", 10, 22]} />
        <ambientLight intensity={0.5} />
        <directionalLight position={[3, 6, 5]} intensity={1.1} />
        <SpinRig view={spin.view} still={still || !!hover} cfg={SPIN} />
        <Scene lanes={lanes} flights={flights} play={play} view={spin.view} still={still} onPick={onPick} tip={tip} />
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

const lanePos = (i: number, n: number) => {
  const y = n === 1 ? 0 : 1.9 - (i / (n - 1)) * 3.8;
  return new THREE.Vector3(2.7 - Math.abs(y) * 0.15, y, Math.sin((i / Math.max(1, n - 1)) * Math.PI) * 0.6);
};

function hoverProps(tip: (l: string | null, x?: number, y?: number) => void, label: string) {
  return {
    onPointerMove: (e: ThreeEvent<PointerEvent>) => {
      e.stopPropagation();
      tip(label, e.nativeEvent.offsetX, e.nativeEvent.offsetY);
    },
    onPointerOut: () => tip(null),
  };
}

function Scene({
  lanes,
  flights,
  play,
  view,
  still,
  onPick,
  tip,
}: Omit<Props, "still"> & {
  view: React.RefObject<SpinView>;
  still: boolean;
  tip: (l: string | null, x?: number, y?: number) => void;
}) {
  const group = useRef<THREE.Group>(null!);
  const ring = useRef<THREE.Mesh>(null!);
  const clock = useRef(0);
  const lastPlay = useRef(play);
  const positions = useMemo(() => new Map(lanes.map((l, i) => [l.id, lanePos(i, lanes.length)])), [lanes]);

  useFrame((_, dt) => {
    const v = view.current!;
    group.current.rotation.set(v.rotX, v.rotY, 0);
    if (lastPlay.current !== play) {
      lastPlay.current = play;
      clock.current = 0;
    }
    clock.current += still ? 60 : dt;
    if (!still) ring.current.rotation.x += dt * 0.4;
  });

  return (
    <group ref={group}>
      {/* Orchestrator: every message starts here. */}
      <mesh position={ORCH} {...hoverProps(tip, "orchestrator — sends every message onto the bus")}>
        <boxGeometry args={[0.55, 0.55, 0.55]} />
        <meshStandardMaterial color="#9fdcff" emissive={ACCENT} emissiveIntensity={0.7} />
      </mesh>

      {/* The sentinel gate every declared action must pass. */}
      <group position={[GATE_X, 0, 0]} rotation-y={Math.PI / 2}>
        <mesh ref={ring} {...hoverProps(tip, "sentinel gate — allow, hold or deny each declared action")}>
          <torusGeometry args={[1.25, 0.035, 8, 96]} />
          <meshStandardMaterial color={ACCENT} emissive={ACCENT} emissiveIntensity={0.6} />
        </mesh>
      </group>

      {lanes.map((l) => {
        const p = positions.get(l.id)!;
        return (
          <group key={l.id} position={p}>
            <Rail from={ORCH} to={p} onBus={l.onBus} />
            <mesh
              {...hoverProps(tip, `${l.id} · ${l.onBus ? "has a bus handler — click to address it" : "no bus handler yet — messages get no_handler"}`)}
              onClick={(e: ThreeEvent<MouseEvent>) => {
                e.stopPropagation();
                if (e.delta < 5) onPick(l.id);
              }}
            >
              <boxGeometry args={[0.36, 0.36, 0.36]} />
              <meshStandardMaterial
                color={l.onBus ? ACCENT : "#2a2e35"}
                emissive={l.onBus ? ACCENT : "#000000"}
                emissiveIntensity={0.35}
                transparent
                opacity={l.onBus ? 1 : 0.55}
              />
            </mesh>
          </group>
        );
      })}

      {flights.map((f, i) => (
        <Packet key={`${play}-${i}`} target={positions.get(f.to) ?? ORCH} status={f.status} start={i * STAGGER} clock={clock} />
      ))}
    </group>
  );
}

function Rail({ from, to, onBus }: { from: THREE.Vector3; to: THREE.Vector3; onBus: boolean }) {
  // Drawn in the lane's local space (the group is positioned at `to`).
  const geo = useMemo(
    () => new THREE.BufferGeometry().setFromPoints([from.clone().sub(to), new THREE.Vector3()]),
    [from, to],
  );
  return (
    <lineSegments geometry={geo}>
      <lineBasicMaterial color={ACCENT} transparent opacity={onBus ? 0.18 : 0.06} />
    </lineSegments>
  );
}

// Legs of a message, in bus order: handler check → gate → budget → handler → response.
function Packet({
  target,
  status,
  start,
  clock,
}: {
  target: THREE.Vector3;
  status: string;
  start: number;
  clock: React.RefObject<number>;
}) {
  const ref = useRef<THREE.Mesh>(null!);
  const gate = useMemo(() => new THREE.Vector3(GATE_X, target.y * 0.35, target.z * 0.35), [target]);
  const pos = useMemo(() => new THREE.Vector3(), []);
  const color = STATUS_COLOR[status] ?? "#ffffff";

  useFrame(() => {
    const t = clock.current! - start;
    let scale = 1;
    const lerp = (a: THREE.Vector3, b: THREE.Vector3, k: number) => pos.copy(a).lerp(b, Math.min(1, Math.max(0, k)));
    if (t < 0) scale = 0;
    else if (status === "no_handler") {
      // The bus refuses before the gate: the packet never really leaves.
      lerp(ORCH, gate, Math.min(t / HOP, 0.25));
      scale = Math.max(0, 1 - t / (HOP * 1.5));
    } else if (t < HOP) lerp(ORCH, gate, t / HOP);
    else if (status === "held") {
      pos.copy(gate);
      scale = (1 + Math.sin((t - HOP) * 10) * 0.35) * Math.max(0, 1 - Math.max(0, t - HOP * 4) / HOP);
    } else if (status === "denied") {
      lerp(gate, ORCH, (t - HOP) / HOP);
      scale = Math.max(0, 1 - (t - HOP) / (HOP * 1.4));
    } else if (status === "degraded") {
      lerp(gate, target, ((t - HOP) / HOP) * 0.25);
      scale = Math.max(0, 1 - (t - HOP) / (HOP * 1.5));
    } else if (t < HOP * 2) lerp(gate, target, (t - HOP) / HOP);
    else if (status === "error") {
      pos.copy(target);
      scale = Math.max(0, 1.8 - (t - HOP * 2) / HOP);
    } else {
      lerp(target, ORCH, (t - HOP * 2) / HOP); // the response travels home
      scale = t > HOP * 3 ? 0 : 1;
    }
    ref.current.position.copy(pos);
    ref.current.scale.setScalar(Math.max(0.001, scale));
  });

  return (
    <mesh ref={ref} scale={0.001}>
      <boxGeometry args={[0.18, 0.18, 0.18]} />
      <meshBasicMaterial color={color} />
    </mesh>
  );
}
