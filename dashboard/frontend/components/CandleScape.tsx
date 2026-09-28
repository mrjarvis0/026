"use client";

import { Canvas, useFrame, type ThreeEvent } from "@react-three/fiber";
import { useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { SpinControls, SpinRig, Tooltip, useSpin, type SpinConfig, type SpinView } from "./Spin";

export type Candle = [number, number, number, number, number, number]; // ts, open, high, low, close, volume
export type Marker = { ts: number; price: number; kind: "entry" | "exit"; side: string; pnl: number | null; id: number };

// Up/down in blue/orange rather than green/red: readable with colour-blindness, labelled on hover.
const UP = "#5fb8ea";
const DOWN = "#e0803c";
const STEP = 0.11;
const HEIGHT = 4;
const SPIN: SpinConfig = {
  zoom: { min: 4, max: 16, start: 9.5 },
  tilt: { min: -0.3, max: 0.8, start: 0.15 },
  rotY: -0.25,
  height: 0.6,
  lookY: 0,
};

type Props = { candles: Candle[]; markers: Marker[]; last: number | null; still: boolean };

export default function CandleScape(props: Props) {
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
        <ambientLight intensity={0.6} />
        <directionalLight position={[3, 6, 6]} intensity={1.1} />
        <SpinRig view={spin.view} still={props.still || !!hover} cfg={SPIN} />
        <Scape
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

const price = (p: number) => p.toLocaleString("en-US", { maximumFractionDigits: p < 10 ? 6 : 2 });

function Scape({
  candles,
  markers,
  last,
  view,
  tip,
}: Props & { view: React.RefObject<SpinView>; tip: (l: string | null, x?: number, y?: number) => void }) {
  const group = useRef<THREE.Group>(null!);
  const lo = Math.min(...candles.map((c) => c[3]), ...(last ? [last] : []));
  const hi = Math.max(...candles.map((c) => c[2]), ...(last ? [last] : []));
  const span = hi - lo || 1;
  const y = (p: number) => ((p - lo) / span) * HEIGHT - HEIGHT / 2;
  const x = (i: number) => (i - (candles.length - 1) / 2) * STEP;
  const maxVol = Math.max(1e-9, ...candles.map((c) => c[5]));
  const width = candles.length * STEP;

  const wicks = useMemo(
    () =>
      new THREE.BufferGeometry().setFromPoints(
        candles.flatMap((c, i) => [new THREE.Vector3(x(i), y(c[2]), 0), new THREE.Vector3(x(i), y(c[3]), 0)]),
      ),
    [candles, lo, hi], // x and y are derived from exactly these
  );

  useFrame(() => {
    const v = view.current!;
    group.current.rotation.set(v.rotX, v.rotY, 0);
  });

  // Place a trade marker on the candle whose interval contains its timestamp.
  const interval = candles.length > 1 ? candles[1][0] - candles[0][0] : 60_000;
  const at = (ts: number) => {
    const i = Math.floor((ts - candles[0][0]) / interval);
    return i >= 0 && i < candles.length ? i : null;
  };

  return (
    <group ref={group}>
      <lineSegments geometry={wicks}>
        <lineBasicMaterial color="#8a93a0" />
      </lineSegments>

      {candles.map((c, i) => {
        const up = c[4] >= c[1];
        const top = y(Math.max(c[1], c[4]));
        const bottom = y(Math.min(c[1], c[4]));
        const h = Math.max(0.015, top - bottom);
        const t = new Date(c[0]).toISOString().slice(11, 16);
        return (
          <group key={c[0]}>
            <mesh
              position={[x(i), bottom + h / 2, 0]}
              onPointerMove={(e: ThreeEvent<PointerEvent>) => {
                e.stopPropagation();
                tip(
                  `${t} UTC · ${up ? "up" : "down"} · O ${price(c[1])} H ${price(c[2])} L ${price(c[3])} C ${price(c[4])} · vol ${c[5].toFixed(3)}`,
                  e.nativeEvent.offsetX,
                  e.nativeEvent.offsetY,
                );
              }}
              onPointerOut={() => tip(null)}
            >
              <boxGeometry args={[STEP * 0.72, h, STEP * 0.72]} />
              <meshStandardMaterial color={up ? UP : DOWN} emissive={up ? UP : DOWN} emissiveIntensity={0.25} />
            </mesh>
            {/* Volume, pushed back and dimmed: context, not the subject. */}
            <mesh position={[x(i), -HEIGHT / 2 - 0.35 + (c[5] / maxVol) * 0.3, -0.5]}>
              <boxGeometry args={[STEP * 0.6, Math.max(0.01, (c[5] / maxVol) * 0.6), STEP * 0.3]} />
              <meshBasicMaterial color="#3a4250" />
            </mesh>
          </group>
        );
      })}

      {last != null && (
        <mesh position={[0, y(last), 0]}>
          <boxGeometry args={[width + 0.4, 0.008, 0.008]} />
          <meshBasicMaterial color="#d6f1ff" />
        </mesh>
      )}

      {markers.map((m) => {
        const i = at(m.ts);
        if (i == null) return null;
        const color = m.kind === "entry" ? "#ffffff" : m.pnl != null && m.pnl >= 0 ? "#0ca30c" : "#d03b3b";
        return (
          <mesh
            key={`${m.id}-${m.kind}`}
            position={[x(i), y(m.price), 0.12]}
            onPointerMove={(e: ThreeEvent<PointerEvent>) => {
              e.stopPropagation();
              tip(
                `Trade #${m.id} ${m.kind} · ${m.side} @ ${price(m.price)}${m.kind === "exit" && m.pnl != null ? ` · P&L ${m.pnl.toFixed(2)}` : ""}`,
                e.nativeEvent.offsetX,
                e.nativeEvent.offsetY,
              );
            }}
            onPointerOut={() => tip(null)}
          >
            <octahedronGeometry args={[0.07]} />
            <meshBasicMaterial color={color} />
          </mesh>
        );
      })}
    </group>
  );
}
