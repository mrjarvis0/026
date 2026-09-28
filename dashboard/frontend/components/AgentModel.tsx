"use client";

import { Canvas, useFrame, type ThreeEvent } from "@react-three/fiber";
import { useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { Agent, Detector } from "@/lib/fleet";
import { MATURITY_COLOR, toolAccess } from "@/lib/maturity";
import { SpinControls, SpinRig, Tooltip, useSpin, type SpinConfig, type SpinView } from "./Spin";

export const STAGES = [
  "sensors", "ingestion", "validation", "normalization", "store", "skills", "intelligence", "decision",
] as const;
const SLAB_GAP = 0.36;
const slabY = (i: number) => -1.4 + i * SLAB_GAP;
const SKILLS_Y = slabY(5);
const INTEL_Y = slabY(6);

const WARNING = "#fab219";
const GOOD = "#0ca30c";
const SERIOUS = "#ec835a";
const ACCENT = "#5fb8ea";

const SPIN: SpinConfig = {
  zoom: { min: 5.5, max: 13, start: 8.5 },
  tilt: { min: -0.35, max: 0.7, start: 0.18 },
  rotY: 0.6,
  height: 1.5,
  lookY: -0.25,
};

export type Part = { kind: "stage" | "tool" | "detector"; id: string };

type Props = {
  agent: Agent;
  highlight: string | null;
  onPick: (p: Part) => void;
  still: boolean;
};

export default function AgentModel({ agent, highlight, onPick, still }: Props) {
  const spin = useSpin(SPIN);
  const [hover, setHover] = useState<{ part: Part; label: string; x: number; y: number } | null>(null);

  return (
    <div {...spin.wrapProps}>
      <Canvas
        frameloop={spin.visible ? "always" : "never"}
        dpr={[1, 1.75]}
        camera={{ position: [0, SPIN.height, SPIN.zoom.start], fov: 40 }}
        gl={{ antialias: true, alpha: true }}
        onPointerMissed={() => setHover(null)}
      >
        <fog attach="fog" args={["#06070a", 10, 22]} />
        <ambientLight intensity={0.45} />
        <directionalLight position={[4, 7, 5]} intensity={1.2} />
        <pointLight position={[0, 0.4, 0]} intensity={6} distance={5} color={ACCENT} />
        <SpinRig view={spin.view} still={still} cfg={SPIN} />
        <Model
          key={agent.id}
          agent={agent}
          view={spin.view}
          still={still || !!hover}
          reduceMotion={still}
          highlight={highlight ?? hover?.part.id ?? null}
          onHover={(part, label, x, y) => {
            // Inspecting counts as input: the orbit and idle spin hold still so the part stays under the cursor.
            spin.view.current.lastInput = performance.now();
            setHover(part ? { part, label, x, y } : null);
          }}
          onPick={onPick}
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

const ease = (t: number) => 1 - Math.pow(1 - THREE.MathUtils.clamp(t, 0, 1), 3);

function Model({
  agent,
  view,
  still,
  reduceMotion,
  highlight,
  onHover,
  onPick,
}: {
  agent: Agent;
  view: React.RefObject<SpinView>;
  still: boolean;
  reduceMotion: boolean;
  highlight: string | null;
  onHover: (part: Part | null, label: string, x: number, y: number) => void;
  onPick: (p: Part) => void;
}) {
  const group = useRef<THREE.Group>(null!);
  const orbit = useRef<THREE.Group>(null!);
  const born = useRef(0); // seconds since this agent's model appeared
  const planned = !agent.registered;
  const color = MATURITY_COLOR[agent.status];

  useFrame((_, dt) => {
    born.current += reduceMotion ? 10 : dt;
    const v = view.current!;
    group.current.rotation.set(v.rotX, v.rotY, 0);
    if (!still) orbit.current.rotation.y += dt * 0.25;
  });

  // Pointer helpers shared by every part: hover label, click-to-select (ignored after a drag).
  const bind = (part: Part, label: string) => ({
    onPointerMove: (e: ThreeEvent<PointerEvent>) => {
      e.stopPropagation();
      onHover(part, label, e.nativeEvent.offsetX, e.nativeEvent.offsetY);
    },
    onPointerOut: () => onHover(null, "", 0, 0),
    onClick: (e: ThreeEvent<MouseEvent>) => {
      e.stopPropagation();
      if (e.delta < 5) onPick(part);
    },
  });

  return (
    <group ref={group}>
      {STAGES.map((stage, i) => (
        <Slab
          key={stage}
          index={i}
          born={born}
          color={color}
          wire={planned}
          lit={highlight === stage}
          {...bind({ kind: "stage", id: stage }, `0${i + 1} · ${stage} — pipeline layer${planned ? " (agent not built)" : " (per-layer build status not tracked)"}`)}
        />
      ))}

      <group ref={orbit}>
        {agent.tools.map((tool, i) => (
          <Satellite
            key={tool}
            born={born}
            delay={0.5 + i * 0.08}
            angle={(i / agent.tools.length) * Math.PI * 2}
            radius={2}
            y={SKILLS_Y}
            lit={highlight === tool}
            {...bind({ kind: "tool", id: tool }, `${tool} · ${toolAccess(tool)} access`)}
          >
            <boxGeometry args={[0.24, 0.24, 0.24]} />
            <meshStandardMaterial color={ACCENT} emissive={ACCENT} emissiveIntensity={highlight === tool ? 1.6 : 0.4} />
          </Satellite>
        ))}
        {agent.detectors.map((d, i) => (
          <DetectorNode
            key={d.id}
            d={d}
            born={born}
            delay={0.8 + i * 0.1}
            angle={(i / agent.detectors.length) * Math.PI * 2 + 0.4}
            lit={highlight === d.id}
            bind={bind}
          />
        ))}
      </group>

      {Array.from({ length: agent.trust ?? 0 }, (_, i) => (
        <Ring key={i} born={born} delay={1 + i * 0.12} radius={1.45 + i * 0.28} y={slabY(0) - 0.25} color="#ffffff" opacity={0.18} />
      ))}
      {agent.execution && <Ring born={born} delay={1.3} radius={1.3} y={slabY(7)} color={SERIOUS} opacity={1} />}
    </group>
  );
}

type Bind = {
  onPointerMove: (e: ThreeEvent<PointerEvent>) => void;
  onPointerOut: () => void;
  onClick: (e: ThreeEvent<MouseEvent>) => void;
};

function Slab({
  index,
  born,
  color,
  wire,
  lit,
  ...handlers
}: { index: number; born: React.RefObject<number>; color: string; wire: boolean; lit: boolean } & Bind) {
  const ref = useRef<THREE.Group>(null!);
  const edges = useMemo(() => new THREE.EdgesGeometry(new THREE.BoxGeometry(1.6, 0.16, 1.6)), []);
  // Layers drop into place bottom-up, sensors first.
  useFrame(() => {
    const p = ease((born.current! - index * 0.07) / 0.6);
    ref.current.position.y = slabY(index) + (1 - p) * 3;
    ref.current.scale.setScalar(Math.max(0.001, p) * (lit ? 1.08 : 1));
  });
  return (
    <group ref={ref}>
      <mesh {...handlers}>
        <boxGeometry args={[1.6, 0.16, 1.6]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={lit ? 0.9 : 0.15}
          transparent
          opacity={wire ? 0.06 : 0.9}
          roughness={0.5}
        />
      </mesh>
      <lineSegments geometry={edges}>
        <lineBasicMaterial color={lit ? "#ffffff" : wire ? "#6b7280" : color} transparent opacity={wire ? 0.7 : 0.5} />
      </lineSegments>
    </group>
  );
}

function Satellite({
  born,
  delay,
  angle,
  radius,
  y,
  lit,
  children,
  ...handlers
}: {
  born: React.RefObject<number>;
  delay: number;
  angle: number;
  radius: number;
  y: number;
  lit: boolean;
  children: React.ReactNode;
} & Bind) {
  const ref = useRef<THREE.Mesh>(null!);
  // Parts spiral out from the core to their orbit.
  useFrame((_, dt) => {
    const p = ease((born.current! - delay) / 0.7);
    const r = radius * p;
    const a = angle - (1 - p) * 2;
    ref.current.position.set(Math.cos(a) * r, y, Math.sin(a) * r);
    ref.current.rotation.x += dt * 0.6;
    ref.current.rotation.y += dt * 0.8;
    const s = THREE.MathUtils.damp(ref.current.scale.x, lit ? 1.7 : 1, 10, dt);
    ref.current.scale.setScalar(Math.max(0.001, s * p));
  });
  return (
    <mesh ref={ref} {...handlers}>
      {children}
    </mesh>
  );
}

function DetectorNode({
  d,
  born,
  delay,
  angle,
  lit,
  bind,
}: {
  d: Detector;
  born: React.RefObject<number>;
  delay: number;
  angle: number;
  lit: boolean;
  bind: (part: Part, label: string) => Bind;
}) {
  const validated = d.maturity === "validated";
  const tint = validated ? GOOD : WARNING;
  const edges = useMemo(() => new THREE.EdgesGeometry(new THREE.OctahedronGeometry(0.2)), []);
  const label = `${d.id} · ${d.maturity}${validated ? " — may alert" : " — muted, cannot alert"}${d.ceiling != null ? ` · ceiling ${d.ceiling.toFixed(2)}` : ""}`;
  return (
    <Satellite born={born} delay={delay} angle={angle} radius={2.65} y={INTEL_Y} lit={lit} {...bind({ kind: "detector", id: d.id }, label)}>
      <octahedronGeometry args={[0.2]} />
      {/* Hollow until validated: an implemented detector is muted by the maturity gate. */}
      <meshStandardMaterial
        color={tint}
        emissive={tint}
        emissiveIntensity={lit ? 1.2 : validated ? 0.6 : 0.2}
        transparent
        opacity={validated ? 1 : 0.12}
      />
      <lineSegments geometry={edges}>
        <lineBasicMaterial color={tint} />
      </lineSegments>
    </Satellite>
  );
}

function Ring({
  born,
  delay,
  radius,
  y,
  color,
  opacity,
}: {
  born: React.RefObject<number>;
  delay: number;
  radius: number;
  y: number;
  color: string;
  opacity: number;
}) {
  const ref = useRef<THREE.Mesh>(null!);
  useFrame(() => ref.current.scale.setScalar(Math.max(0.001, ease((born.current! - delay) / 0.6))));
  return (
    <mesh ref={ref} position-y={y} rotation-x={Math.PI / 2}>
      <torusGeometry args={[radius, 0.012, 6, 96]} />
      <meshBasicMaterial color={color} transparent opacity={opacity} />
    </mesh>
  );
}
