"use client";

import { Canvas, useFrame, type ThreeEvent } from "@react-three/fiber";
import { useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { STATE_COLOR } from "@/lib/status";
import { SpinControls, SpinRig, Tooltip, useSpin, type SpinConfig, type SpinView } from "./Spin";

export type DomeAgent = { id: string; verdict: string | null; trust: number | null };
export type Packet = { nonce: number; agent: string; decision: "allow" | "hold" | "deny" };

const UNSCANNED = "#4a505b";
const ACCENT = "#5fb8ea";
const SHELL = 3;
const ORBIT = 1.7;

const SPIN: SpinConfig = {
  zoom: { min: 6, max: 16, start: 11 },
  tilt: { min: -0.4, max: 0.8, start: 0.35 },
  rotY: 0.3,
  height: 1.2,
  lookY: 0,
};

type Props = {
  agents: DomeAgent[];
  selected: string;
  packet: Packet | null;
  onPick: (id: string) => void;
  still: boolean;
};

export default function SentinelDome({ agents, selected, packet, onPick, still }: Props) {
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
        <ambientLight intensity={0.5} />
        <directionalLight position={[4, 7, 5]} intensity={1.1} />
        <SpinRig view={spin.view} still={still || !!hover} cfg={SPIN} />
        <Dome
          agents={agents}
          selected={selected}
          packet={packet}
          view={spin.view}
          still={still}
          onPick={onPick}
          onHover={(label, x, y) => {
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

const slot = (i: number, n: number) => {
  const a = (i / n) * Math.PI * 2;
  return new THREE.Vector3(Math.cos(a) * ORBIT, 0, Math.sin(a) * ORBIT);
};

function Dome({
  agents,
  selected,
  packet,
  view,
  still,
  onPick,
  onHover,
}: Omit<Props, "still"> & {
  view: React.RefObject<SpinView>;
  still: boolean;
  onHover: (label: string | null, x: number, y: number) => void;
}) {
  const group = useRef<THREE.Group>(null!);
  const shell = useRef<THREE.Mesh>(null!);
  const flash = useRef(0);

  useFrame((_, dt) => {
    const v = view.current!;
    group.current.rotation.set(v.rotX, v.rotY, 0);
    if (!still) shell.current.rotation.y -= dt * 0.05;
    flash.current = Math.max(0, flash.current - dt);
    (shell.current.material as THREE.MeshBasicMaterial).opacity = 0.14 + flash.current * 0.25;
  });

  const from = packet ? slot(agents.findIndex((a) => a.id === packet.agent), agents.length) : null;

  return (
    <group ref={group}>
      {/* The sentinel: every action from inside has to cross this shell. */}
      <mesh ref={shell}>
        <icosahedronGeometry args={[SHELL, 2]} />
        <meshBasicMaterial color={ACCENT} wireframe transparent opacity={0.14} />
      </mesh>
      <mesh>
        <sphereGeometry args={[SHELL - 0.02, 48, 32]} />
        <meshBasicMaterial color={ACCENT} transparent opacity={0.025} side={THREE.BackSide} depthWrite={false} />
      </mesh>

      {/* The bus at the centre: agents never talk to each other directly. */}
      <mesh
        onPointerMove={(e: ThreeEvent<PointerEvent>) => {
          e.stopPropagation();
          onHover("Message bus — every action is routed here, then gated", e.nativeEvent.offsetX, e.nativeEvent.offsetY);
        }}
        onPointerOut={() => onHover(null, 0, 0)}
      >
        <octahedronGeometry args={[0.32]} />
        <meshStandardMaterial color="#9fdcff" emissive={ACCENT} emissiveIntensity={0.8} />
      </mesh>

      {agents.map((a, i) => (
        <AgentCube
          key={a.id}
          agent={a}
          pos={slot(i, agents.length)}
          selected={a.id === selected}
          onPick={onPick}
          onHover={onHover}
        />
      ))}

      {packet && from && (
        <Shot key={packet.nonce} from={from} decision={packet.decision} still={still} onImpact={() => (flash.current = 1)} />
      )}
    </group>
  );
}

function AgentCube({
  agent,
  pos,
  selected,
  onPick,
  onHover,
}: {
  agent: DomeAgent;
  pos: THREE.Vector3;
  selected: boolean;
  onPick: (id: string) => void;
  onHover: (label: string | null, x: number, y: number) => void;
}) {
  const ref = useRef<THREE.Group>(null!);
  const color = agent.verdict ? STATE_COLOR[agent.verdict] : UNSCANNED;
  const edges = useMemo(() => new THREE.EdgesGeometry(new THREE.BoxGeometry(0.34, 0.34, 0.34)), []);
  const spoke = useMemo(() => new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), pos.clone().multiplyScalar(-1)]), [pos]);

  useFrame((_, dt) => {
    ref.current.rotation.y += dt * 0.5;
    const s = THREE.MathUtils.damp(ref.current.scale.x, selected ? 1.5 : 1, 8, dt);
    ref.current.scale.setScalar(s);
  });

  return (
    <group position={pos}>
      <lineSegments geometry={spoke}>
        <lineBasicMaterial color={ACCENT} transparent opacity={0.25} />
      </lineSegments>
      <group
        ref={ref}
        onPointerMove={(e: ThreeEvent<PointerEvent>) => {
          e.stopPropagation();
          onHover(
            `${agent.id} · ${agent.verdict ?? "not scanned yet"} · trust ${agent.trust ?? "—"} — click to test its gate`,
            e.nativeEvent.offsetX,
            e.nativeEvent.offsetY,
          );
        }}
        onPointerOut={() => onHover(null, 0, 0)}
        onClick={(e: ThreeEvent<MouseEvent>) => {
          e.stopPropagation();
          if (e.delta < 5) onPick(agent.id);
        }}
      >
        <mesh>
          <boxGeometry args={[0.34, 0.34, 0.34]} />
          <meshStandardMaterial color={color} emissive={color} emissiveIntensity={selected ? 0.9 : 0.35} />
        </mesh>
        <lineSegments geometry={edges}>
          <lineBasicMaterial color={selected ? "#ffffff" : color} />
        </lineSegments>
      </group>
    </group>
  );
}

// One action's trip to the shell. allow: crosses and leaves. hold: parks on the shell and pulses.
// deny: strikes the shell and falls back to its sender.
function Shot({
  from,
  decision,
  still,
  onImpact,
}: {
  from: THREE.Vector3;
  decision: Packet["decision"];
  still: boolean;
  onImpact: () => void;
}) {
  const ref = useRef<THREE.Mesh>(null!);
  const t = useRef(still ? 1.2 : 0);
  const hit = useRef(false);
  const dir = useMemo(() => from.clone().normalize(), [from]);
  const color = STATE_COLOR[decision];

  useFrame((_, dt) => {
    t.current += dt;
    const travel = Math.min(1, t.current / 1.1); // reach the shell in 1.1 s
    let dist = ORBIT + (SHELL - ORBIT) * (1 - Math.pow(1 - travel, 2));
    let scale = 1;
    let fade = 1;
    const after = t.current - 1.1;
    if (after > 0) {
      if (!hit.current) {
        hit.current = true;
        onImpact();
      }
      if (decision === "allow") {
        dist = SHELL + after * 2.2;
        fade = Math.max(0, 1 - after / 1.2);
      } else if (decision === "deny") {
        dist = SHELL - Math.min(1, after / 0.9) * (SHELL - ORBIT);
        fade = Math.max(0, 1 - after / 1.4);
      } else {
        dist = SHELL;
        scale = 1 + Math.sin(after * 10) * 0.35;
        fade = Math.max(0, 1 - Math.max(0, after - 2.2) / 0.8);
      }
    }
    ref.current.position.copy(dir).multiplyScalar(dist);
    ref.current.scale.setScalar(Math.max(0.001, scale * fade));
  });

  return (
    <mesh ref={ref}>
      <boxGeometry args={[0.16, 0.16, 0.16]} />
      <meshBasicMaterial color={color} />
    </mesh>
  );
}
