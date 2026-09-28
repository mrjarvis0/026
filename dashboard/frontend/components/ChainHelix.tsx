"use client";

import { Canvas, useFrame, type ThreeEvent } from "@react-three/fiber";
import { useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { BLOCK_STATE, type BlockState } from "@/lib/status";
import { SpinControls, SpinRig, Tooltip, useSpin, type SpinConfig, type SpinView } from "./Spin";

export type HelixBlock = { number: number; txs: number; state: BlockState; valueEth: number; time: string };


const SPIN: SpinConfig = {
  zoom: { min: 5, max: 18, start: 12.5 },
  tilt: { min: -0.3, max: 0.9, start: 0.25 },
  rotY: 0,
  height: 1.2,
  lookY: 0,
};
const RADIUS = 3.1;
const TURN = 0.3; // radians per block
const RISE = 0.075; // height per block

type Props = { blocks: HelixBlock[]; selected: number | null; onPick: (n: number) => void; still: boolean };

export default function ChainHelix(props: Props) {
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
        <fog attach="fog" args={["#06070a", 9, 22]} />
        <ambientLight intensity={0.5} />
        <directionalLight position={[4, 8, 5]} intensity={1.2} />
        <SpinRig view={spin.view} still={props.still || !!hover} cfg={SPIN} />
        <Helix
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

function Helix({
  blocks,
  selected,
  onPick,
  still,
  view,
  tip,
}: Props & { view: React.RefObject<SpinView>; tip: (l: string | null, x?: number, y?: number) => void }) {
  const group = useRef<THREE.Group>(null!);
  const clock = useRef(0);
  const maxTx = Math.max(1, ...blocks.map((b) => b.txs));
  const pos = useMemo(
    () =>
      blocks.map((_, i) => {
        const a = i * TURN;
        return new THREE.Vector3(Math.cos(a) * RADIUS, i * RISE - (blocks.length * RISE) / 2, Math.sin(a) * RADIUS);
      }),
    [blocks],
  );
  // Each block commits to its parent's hash: draw that link.
  const links = useMemo(() => new THREE.BufferGeometry().setFromPoints(pos.flatMap((p, i) => (i ? [pos[i - 1], p] : []))), [pos]);

  useFrame((_, dt) => {
    const v = view.current!;
    group.current.rotation.set(v.rotX, v.rotY, 0);
    clock.current += still ? 0 : dt;
  });

  return (
    <group ref={group}>
      <lineSegments geometry={links}>
        <lineBasicMaterial color="#5fb8ea" transparent opacity={0.25} />
      </lineSegments>
      {blocks.map((b, i) => (
        <BlockCube
          key={b.number}
          b={b}
          pos={pos[i]}
          height={0.12 + (b.txs / maxTx) * 0.9}
          selected={selected === b.number}
          onPick={onPick}
          tip={tip}
        />
      ))}
      <Walker pos={pos} clock={clock} />
    </group>
  );
}

function BlockCube({
  b,
  pos,
  height,
  selected,
  onPick,
  tip,
}: {
  b: HelixBlock;
  pos: THREE.Vector3;
  height: number;
  selected: boolean;
  onPick: (n: number) => void;
  tip: (l: string | null, x?: number, y?: number) => void;
}) {
  const ref = useRef<THREE.Group>(null!);
  const state = BLOCK_STATE[b.state];
  const hollow = b.state === "unfetched";
  const edges = useMemo(() => new THREE.EdgesGeometry(new THREE.BoxGeometry(0.34, height, 0.34)), [height]);
  useFrame((_, dt) => ref.current.scale.setScalar(THREE.MathUtils.damp(ref.current.scale.x, selected ? 1.5 : 1, 8, dt)));
  return (
    <group
      ref={ref}
      position={pos}
      onPointerMove={(e: ThreeEvent<PointerEvent>) => {
        e.stopPropagation();
        tip(
          `#${b.number.toLocaleString("en-US")} · ${b.txs} txs · ${b.valueEth.toFixed(2)} ETH moved · ${state.label} — click for its largest transfers`,
          e.nativeEvent.offsetX,
          e.nativeEvent.offsetY,
        );
      }}
      onPointerOut={() => tip(null)}
      onClick={(e: ThreeEvent<MouseEvent>) => {
        e.stopPropagation();
        if (e.delta < 5) onPick(b.number);
      }}
    >
      <mesh>
        <boxGeometry args={[0.34, height, 0.34]} />
        <meshStandardMaterial
          color={state.color}
          emissive={state.color}
          emissiveIntensity={selected ? 1 : 0.3}
          transparent
          opacity={hollow ? 0.06 : 0.95}
        />
      </mesh>
      <lineSegments geometry={edges}>
        <lineBasicMaterial color={selected ? "#ffffff" : state.color} transparent opacity={hollow ? 0.8 : 0.6} />
      </lineSegments>
    </group>
  );
}

// A packet walking the chain from genesis of the window to its tip.
function Walker({ pos, clock }: { pos: THREE.Vector3[]; clock: React.RefObject<number> }) {
  const ref = useRef<THREE.Mesh>(null!);
  useFrame(() => {
    const t = ((clock.current! * 6) % pos.length + pos.length) % pos.length;
    const i = Math.floor(t);
    ref.current.position.copy(pos[i]).lerp(pos[Math.min(pos.length - 1, i + 1)], t - i);
  });
  return (
    <mesh ref={ref}>
      <boxGeometry args={[0.08, 0.08, 0.08]} />
      <meshBasicMaterial color="#d6f1ff" />
    </mesh>
  );
}
