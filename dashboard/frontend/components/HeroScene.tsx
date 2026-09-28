"use client";

import { Canvas, useFrame, useThree, type ThreeEvent } from "@react-three/fiber";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { Agent } from "@/lib/fleet";
import { MATURITY_COLOR, type Maturity } from "@/lib/maturity";

const ACCENT = "#5fb8ea";
const SERIOUS = "#ec835a";
const SIZE: Record<Maturity, number> = {
  planned: 0.2,
  scaffold: 0.24,
  partial: 0.3,
  substantial: 0.36,
  complete: 0.4,
};

type Props = {
  agents: Agent[];
  onHover: (a: Agent | null) => void;
  onOpen?: (a: Agent) => void;
  still: boolean;
};

export default function HeroScene({ agents, onHover, onOpen, still }: Props) {
  const wrap = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(true);
  const [ready, setReady] = useState(false);
  // Freeze the orbits while a node is inspected — a moving target is hard to read.
  const [paused, setPaused] = useState(false);
  const inspect = (a: Agent | null) => {
    setPaused(!!a);
    onHover(a);
  };

  useEffect(() => {
    const io = new IntersectionObserver(([e]) => setVisible(e.isIntersecting));
    io.observe(wrap.current!);
    return () => io.disconnect();
  }, []);

  return (
    <div
      ref={wrap}
      className="h-full w-full transition-opacity duration-[1500ms]"
      style={{ opacity: ready ? 1 : 0 }}
    >
      <Canvas
        frameloop={visible ? "always" : "never"}
        dpr={[1, 1.75]}
        camera={{ position: [0, 1.4, 10], fov: 42 }}
        gl={{ antialias: true, alpha: true }}
        onCreated={() => setReady(true)}
        onPointerMissed={() => inspect(null)}
      >
        <fog attach="fog" args={["#06070a", 8, 19]} />
        <ambientLight intensity={0.35} />
        <directionalLight position={[4, 6, 5]} intensity={1.1} />
        <pointLight position={[0, 0, 0]} intensity={14} distance={7} color={ACCENT} />
        <Constellation agents={agents} onHover={inspect} onOpen={onOpen} still={still || paused} />
        <Dust still={still} />
        <Rig still={still} />
      </Canvas>
    </div>
  );
}

function Rig({ still }: { still: boolean }) {
  useFrame(({ camera, pointer }, dt) => {
    if (still) return;
    camera.position.x = THREE.MathUtils.damp(camera.position.x, pointer.x * 0.9, 2, dt);
    camera.position.y = THREE.MathUtils.damp(camera.position.y, 1.4 + pointer.y * 0.6, 2, dt);
    camera.lookAt(0, 0, 0);
  });
  return null;
}

function Constellation({ agents, onHover, onOpen, still }: Props) {
  const offset = useThree((s) => (s.viewport.aspect > 1.1 ? s.viewport.width * 0.27 : 0));
  return (
    <group position={[offset, offset ? 0 : 1.6, 0]}>
      <Core still={still} />
      <Ring
        agents={agents.filter((a) => a.registered)}
        radius={2.4}
        tilt={[0.35, 0, 0.12]}
        speed={0.07}
        linked
        onHover={onHover}
        onOpen={onOpen}
        still={still}
      />
      <Ring
        agents={agents.filter((a) => !a.registered)}
        radius={3.9}
        tilt={[-0.18, 0, -0.08]}
        speed={-0.035}
        onHover={onHover}
        onOpen={onOpen}
        still={still}
      />
    </group>
  );
}

let glowTexture: THREE.Texture | null = null;
function glow() {
  if (glowTexture) return glowTexture;
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const ctx = c.getContext("2d")!;
  const g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, "rgba(166,225,255,1)");
  g.addColorStop(0.25, "rgba(95,184,234,0.4)");
  g.addColorStop(1, "rgba(95,184,234,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 128, 128);
  return (glowTexture = new THREE.CanvasTexture(c));
}

function Glow({ scale, opacity }: { scale: number; opacity: number }) {
  return (
    <sprite scale={scale}>
      <spriteMaterial
        map={glow()}
        transparent
        opacity={opacity}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </sprite>
  );
}

// Orchestrator = voxel core (3x3x3 minus corners); sentinel = the geodesic shell around it.
function Core({ still }: { still: boolean }) {
  const core = useRef<THREE.Group>(null!);
  const shell = useRef<THREE.Mesh>(null!);
  const box = useMemo(() => new THREE.BoxGeometry(0.3, 0.3, 0.3), []);
  const cells = useMemo(() => {
    const out: [number, number, number][] = [];
    for (let x = -1; x <= 1; x++)
      for (let y = -1; y <= 1; y++)
        for (let z = -1; z <= 1; z++)
          if (Math.abs(x) + Math.abs(y) + Math.abs(z) < 3) out.push([x, y, z]);
    return out;
  }, []);

  useFrame((_, dt) => {
    if (still) return;
    core.current.rotation.y += dt * 0.25;
    core.current.rotation.x += dt * 0.1;
    shell.current.rotation.y -= dt * 0.08;
  });

  return (
    <group>
      <group ref={core}>
        {cells.map(([x, y, z]) => (
          <mesh key={`${x}${y}${z}`} geometry={box} position={[x * 0.36, y * 0.36, z * 0.36]}>
            <meshStandardMaterial
              color="#9fdcff"
              emissive={ACCENT}
              emissiveIntensity={x === 0 && y === 0 && z === 0 ? 2 : 0.55}
              roughness={0.35}
              metalness={0.2}
            />
          </mesh>
        ))}
      </group>
      <Glow scale={3.4} opacity={0.5} />
      <mesh ref={shell}>
        <icosahedronGeometry args={[1.3, 1]} />
        <meshBasicMaterial color={ACCENT} wireframe transparent opacity={0.16} />
      </mesh>
    </group>
  );
}

function Ring({
  agents,
  radius,
  tilt,
  speed,
  linked = false,
  onHover,
  onOpen,
  still,
}: {
  agents: Agent[];
  radius: number;
  tilt: [number, number, number];
  speed: number;
  linked?: boolean;
  onHover: Props["onHover"];
  onOpen: Props["onOpen"];
  still: boolean;
}) {
  const spin = useRef<THREE.Group>(null!);
  const dashed = useRef<THREE.LineSegments>(null!);
  const nodes = useMemo(
    () =>
      agents.map((a, i) => {
        const t = (i / agents.length) * Math.PI * 2;
        return { agent: a, pos: new THREE.Vector3(Math.cos(t) * radius, 0, Math.sin(t) * radius) };
      }),
    [agents, radius],
  );
  const orbit = useMemo(() => {
    const pts = Array.from({ length: 160 }, (_, i) => {
      const t = (i / 160) * Math.PI * 2;
      return new THREE.Vector3(Math.cos(t) * radius, 0, Math.sin(t) * radius);
    });
    return new THREE.BufferGeometry().setFromPoints(pts);
  }, [radius]);
  // Solid spoke = on the shared bus (kernel-wired); dashed = declared but not yet wired.
  const [wired, unwired] = useMemo(() => {
    const spokes = (on: boolean) =>
      new THREE.BufferGeometry().setFromPoints(
        nodes
          .filter((n) => linked && n.agent.kernelWired === on)
          .flatMap((n) => [new THREE.Vector3(), n.pos]),
      );
    return [spokes(true), spokes(false)];
  }, [nodes, linked]);

  useLayoutEffect(() => {
    dashed.current.computeLineDistances();
  }, [unwired]);

  useFrame((_, dt) => {
    if (!still) spin.current.rotation.y += dt * speed;
  });

  return (
    <group rotation={tilt}>
      <lineLoop geometry={orbit}>
        <lineBasicMaterial color="#ffffff" transparent opacity={0.07} />
      </lineLoop>
      <group ref={spin}>
        <lineSegments geometry={wired}>
          <lineBasicMaterial color={ACCENT} transparent opacity={0.55} />
        </lineSegments>
        <lineSegments ref={dashed} geometry={unwired}>
          <lineDashedMaterial color={ACCENT} dashSize={0.08} gapSize={0.1} transparent opacity={0.28} />
        </lineSegments>
        {nodes.map((n, i) => (
          <AgentNode
            key={n.agent.id}
            agent={n.agent}
            pos={n.pos}
            phase={i * 0.37}
            onHover={onHover}
            onOpen={onOpen}
            still={still}
          />
        ))}
      </group>
    </group>
  );
}

function AgentNode({
  agent,
  pos,
  phase,
  onHover,
  onOpen,
  still,
}: {
  agent: Agent;
  pos: THREE.Vector3;
  phase: number;
  onHover: Props["onHover"];
  onOpen: Props["onOpen"];
  still: boolean;
}) {
  const [hot, setHot] = useState(false);
  const body = useRef<THREE.Group>(null!);
  const size = SIZE[agent.status];
  const color = MATURITY_COLOR[agent.status];
  const planned = agent.status === "planned";
  const edges = useMemo(() => new THREE.EdgesGeometry(new THREE.BoxGeometry(size, size, size)), [size]);

  useFrame((_, dt) => {
    if (!still) {
      body.current.rotation.x += dt * 0.4;
      body.current.rotation.y += dt * 0.6;
    }
    const s = THREE.MathUtils.damp(body.current.scale.x, hot ? 1.7 : 1, 8, dt);
    body.current.scale.setScalar(s);
  });

  const over = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    setHot(true);
    onHover(agent);
    document.body.style.cursor = "pointer";
  };
  const out = () => {
    setHot(false);
    onHover(null);
    document.body.style.cursor = "";
  };

  return (
    <group position={pos}>
      {/* Generous invisible hit target: small cubes are hard to hover. */}
      <mesh onPointerOver={over} onPointerOut={out} onClick={() => onOpen?.(agent)}>
        <sphereGeometry args={[0.38, 12, 12]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>
      <group ref={body}>
        {planned ? (
          <lineSegments geometry={edges}>
            <lineBasicMaterial color={hot ? "#a3a9b4" : color} />
          </lineSegments>
        ) : (
          <mesh>
            <boxGeometry args={[size, size, size]} />
            <meshStandardMaterial
              color={color}
              emissive={color}
              emissiveIntensity={hot ? 1.4 : 0.45}
              roughness={0.4}
            />
          </mesh>
        )}
      </group>
      {!planned && <Glow scale={size * 4.5} opacity={hot ? 0.9 : 0.35} />}
      {agent.execution && (
        <mesh rotation-x={Math.PI / 2}>
          <torusGeometry args={[size * 1.3, 0.012, 6, 48]} />
          <meshBasicMaterial color={SERIOUS} />
        </mesh>
      )}
      {agent.kernelWired && <Pulses pos={pos} phase={phase} still={still} />}
    </group>
  );
}

// Bus traffic: one packet out (core -> agent), one back. Only kernel-wired agents get any.
function Pulses({ pos, phase, still }: { pos: THREE.Vector3; phase: number; still: boolean }) {
  const a = useRef<THREE.Mesh>(null!);
  const b = useRef<THREE.Mesh>(null!);
  useFrame(({ clock }) => {
    const t = still ? 0.5 : clock.elapsedTime * 0.35 + phase;
    a.current.position.copy(pos).multiplyScalar((t % 1) - 1);
    b.current.position.copy(pos).multiplyScalar(-((t + 0.5) % 1));
  });
  return (
    <>
      {[a, b].map((r, i) => (
        <mesh key={i} ref={r}>
          <boxGeometry args={[0.06, 0.06, 0.06]} />
          <meshBasicMaterial color="#d6f1ff" />
        </mesh>
      ))}
    </>
  );
}

function Dust({ still }: { still: boolean }) {
  const ref = useRef<THREE.Points>(null!);
  const geo = useMemo(() => {
    const n = 700;
    const p = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const r = 6 + Math.random() * 10;
      const th = Math.random() * Math.PI * 2;
      const ph = Math.acos(2 * Math.random() - 1);
      p.set([r * Math.sin(ph) * Math.cos(th), r * Math.cos(ph) * 0.6, r * Math.sin(ph) * Math.sin(th)], i * 3);
    }
    return new THREE.BufferGeometry().setAttribute("position", new THREE.BufferAttribute(p, 3));
  }, []);
  useFrame((_, dt) => {
    if (!still) ref.current.rotation.y += dt * 0.01;
  });
  return (
    <points ref={ref} geometry={geo}>
      <pointsMaterial size={0.025} color="#9fb4c8" transparent opacity={0.55} depthWrite={false} />
    </points>
  );
}
