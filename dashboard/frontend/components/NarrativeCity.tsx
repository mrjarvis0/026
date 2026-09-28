"use client";

import { Canvas, useFrame, type ThreeEvent } from "@react-three/fiber";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { CATEGORY_LABEL, VERDICT, VERDICTS, type VerdictId } from "@/lib/verdict";

type Cube = { id: number; claim: string; category: string; verdict: VerdictId };
type Props = {
  narratives: Cube[];
  active: string | null;
  onPick: (category: string) => void;
  still: boolean;
};

const SIDE = 4; // a tower layer is SIDE x SIDE narratives
const PITCH = SIDE + 3;
const ORDER = Object.fromEntries(VERDICTS.map((v, i) => [v.id, i]));

export default function NarrativeCity({ narratives, active, onPick, still }: Props) {
  const wrap = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(true);
  const [tip, setTip] = useState<{ cube: Cube; x: number; y: number } | null>(null);

  useEffect(() => {
    const io = new IntersectionObserver(([e]) => setVisible(e.isIntersecting));
    io.observe(wrap.current!);
    return () => io.disconnect();
  }, []);

  return (
    <div ref={wrap} className="relative h-full w-full">
      <Canvas
        frameloop={visible ? "always" : "never"}
        dpr={[1, 1.75]}
        camera={{ position: [26, 22, 26], fov: 38 }}
        gl={{ antialias: true, alpha: true }}
        onPointerMissed={() => setTip(null)}
      >
        <fog attach="fog" args={["#06070a", 40, 90]} />
        <ambientLight intensity={0.55} />
        <directionalLight position={[10, 25, 8]} intensity={1.3} />
        <directionalLight position={[-12, 6, -10]} intensity={0.35} color="#5fb8ea" />
        <City
          narratives={narratives}
          active={active}
          onPick={onPick}
          still={still || !!tip}
          onTip={setTip}
        />
      </Canvas>
      {tip && (
        <div
          className="frame pointer-events-none absolute z-10 w-72 bg-panel/95 p-3 text-xs backdrop-blur-md"
          style={{ left: Math.max(8, Math.min(tip.x + 14, (wrap.current?.clientWidth ?? 0) - 296)), top: tip.y + 14 }}
        >
          <p className="flex items-center gap-2 font-pixel text-[10px] uppercase text-soft">
            <span className="size-2" style={{ background: VERDICT[tip.cube.verdict]?.color }} />
            {VERDICT[tip.cube.verdict]?.label ?? tip.cube.verdict} ·{" "}
            {CATEGORY_LABEL[tip.cube.category] ?? tip.cube.category}
          </p>
          <p className="mt-2 line-clamp-3 leading-relaxed text-ink">{tip.cube.claim}</p>
          <p className="mt-2 text-[10px] text-mute">Click to filter this topic</p>
        </div>
      )}
    </div>
  );
}

function City({
  narratives,
  active,
  onPick,
  still,
  onTip,
}: Props & { onTip: (t: { cube: Cube; x: number; y: number } | null) => void }) {
  const group = useRef<THREE.Group>(null!);
  const mesh = useRef<THREE.InstancedMesh>(null!);
  const [hovered, setHovered] = useState<number | null>(null);

  // Towers: one per topic, tallest first, laid on a square grid; cubes stacked real -> fake.
  const cubes = useMemo(() => {
    const byTopic = new Map<string, Cube[]>();
    for (const n of narratives) byTopic.set(n.category, [...(byTopic.get(n.category) ?? []), n]);
    const towers = [...byTopic.values()].sort((a, b) => b.length - a.length);
    const cols = Math.ceil(Math.sqrt(towers.length));
    const mid = (cols - 1) / 2;
    // Tallest towers take the cells nearest the centre, so the skyline reads from the middle out.
    const cells = Array.from({ length: cols * cols }, (_, i) => [i % cols - mid, Math.floor(i / cols) - mid])
      .sort((a, b) => Math.hypot(a[0], a[1]) - Math.hypot(b[0], b[1]));
    return towers.flatMap((tower, t) => {
      const ox = cells[t][0] * PITCH;
      const oz = cells[t][1] * PITCH;
      return [...tower]
        .sort((a, b) => ORDER[a.verdict] - ORDER[b.verdict])
        .map((cube, i) => ({
          cube,
          pos: new THREE.Vector3(
            ox + (i % SIDE) - (SIDE - 1) / 2,
            Math.floor(i / (SIDE * SIDE)) + 0.5,
            oz + (Math.floor(i / SIDE) % SIDE) - (SIDE - 1) / 2,
          ),
        }));
    });
  }, [narratives]);

  useLayoutEffect(() => {
    const m = new THREE.Matrix4();
    const c = new THREE.Color();
    cubes.forEach(({ cube, pos }, i) => {
      mesh.current.setMatrixAt(i, m.makeTranslation(pos.x, pos.y, pos.z));
      c.set(VERDICT[cube.verdict]?.color ?? "#454a52");
      if (active && cube.category !== active) c.multiplyScalar(0.18);
      if (i === hovered) c.set("#ffffff");
      mesh.current.setColorAt(i, c);
    });
    mesh.current.instanceMatrix.needsUpdate = true;
    mesh.current.instanceColor!.needsUpdate = true;
    mesh.current.computeBoundingSphere();
  }, [cubes, active, hovered]);

  useFrame((_, dt) => {
    if (!still) group.current.rotation.y += dt * 0.05;
  });

  const move = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    if (e.instanceId === undefined) return;
    setHovered(e.instanceId);
    onTip({ cube: cubes[e.instanceId].cube, x: e.nativeEvent.offsetX, y: e.nativeEvent.offsetY });
    document.body.style.cursor = "pointer";
  };
  const out = () => {
    setHovered(null);
    onTip(null);
    document.body.style.cursor = "";
  };

  return (
    <group ref={group} position={[0, -6, 0]}>
      <instancedMesh
        key={cubes.length}
        ref={mesh}
        args={[undefined, undefined, cubes.length]}
        onPointerMove={move}
        onPointerOut={out}
        onClick={(e) => e.instanceId !== undefined && onPick(cubes[e.instanceId].cube.category)}
      >
        <boxGeometry args={[0.86, 0.86, 0.86]} />
        <meshStandardMaterial roughness={0.45} metalness={0.1} />
      </instancedMesh>
      <gridHelper args={[60, 60, "#1b2029", "#11151b"]} />
    </group>
  );
}
