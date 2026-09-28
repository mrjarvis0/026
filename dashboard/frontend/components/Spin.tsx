"use client";

import { useFrame } from "@react-three/fiber";
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";

// Shared mouse control for the dashboard's 3D stages: drag to spin (flick inertia),
// Ctrl/⌘ + wheel or pinch to zoom, double-click to reset, idle auto-spin.
export type SpinConfig = {
  zoom: { min: number; max: number; start: number };
  tilt: { min: number; max: number; start: number };
  rotY: number;
  height: number;
  lookY: number;
};

export type SpinView = {
  rotY: number;
  rotX: number;
  velY: number;
  zoom: number;
  targetZoom: number;
  lastInput: number;
  held: boolean;
};

export function useSpin(cfg: SpinConfig) {
  const wrap = useRef<HTMLDivElement>(null);
  const view = useRef<SpinView>({
    rotY: cfg.rotY, rotX: cfg.tilt.start, velY: 0, zoom: cfg.zoom.start,
    targetZoom: cfg.zoom.start, lastInput: 0, held: false,
  });
  const [dragging, setDragging] = useState(false);
  const [hint, setHint] = useState(false);
  const [visible, setVisible] = useState(true);

  const zoomBy = (factor: number) => {
    const v = view.current;
    v.targetZoom = THREE.MathUtils.clamp(v.targetZoom * factor, cfg.zoom.min, cfg.zoom.max);
    v.lastInput = performance.now();
  };
  const reset = () => {
    Object.assign(view.current, {
      rotY: cfg.rotY, rotX: cfg.tilt.start, velY: 0, targetZoom: cfg.zoom.start, lastInput: performance.now(),
    });
  };

  useEffect(() => {
    const el = wrap.current!;
    const io = new IntersectionObserver(([e]) => setVisible(e.isIntersecting));
    io.observe(el);
    // Plain wheel keeps scrolling the page; Ctrl/⌘ + wheel (and trackpad pinch) zooms the model.
    let hintTimer = 0;
    const onWheel = (e: WheelEvent) => {
      if (!(e.ctrlKey || e.metaKey)) {
        setHint(true);
        clearTimeout(hintTimer);
        hintTimer = window.setTimeout(() => setHint(false), 1400);
        return;
      }
      e.preventDefault();
      zoomBy(Math.exp(e.deltaY * 0.002));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => {
      io.disconnect();
      el.removeEventListener("wheel", onWheel);
      clearTimeout(hintTimer);
    };
  }, []);

  // Listening on window (not pointer capture) keeps R3F's own hover/click working.
  const onPointerDown = (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    const v = view.current;
    let lastX = e.clientX;
    let lastY = e.clientY;
    let lastT = performance.now();
    v.held = true;
    v.velY = 0;
    setDragging(true);
    const move = (ev: PointerEvent) => {
      const now = performance.now();
      const dx = ev.clientX - lastX;
      v.rotY += dx * 0.01;
      v.rotX = THREE.MathUtils.clamp(v.rotX + (ev.clientY - lastY) * 0.005, cfg.tilt.min, cfg.tilt.max);
      v.velY = ((dx * 0.01) / Math.max(1, now - lastT)) * 16;
      v.lastInput = now;
      lastX = ev.clientX;
      lastY = ev.clientY;
      lastT = now;
    };
    const up = () => {
      v.held = false;
      if (performance.now() - lastT > 80) v.velY = 0; // paused before release: no flick
      setDragging(false);
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
  };

  return {
    wrap,
    view,
    visible,
    dragging,
    hint,
    zoomBy,
    reset,
    wrapProps: {
      ref: wrap,
      onPointerDown,
      onDoubleClick: reset,
      className: `relative h-full w-full touch-pan-y select-none ${dragging ? "cursor-grabbing" : "cursor-grab"}`,
    },
  };
}

export function SpinRig({ view, still, cfg }: { view: React.RefObject<SpinView>; still: boolean; cfg: SpinConfig }) {
  useFrame(({ camera }, dt) => {
    const v = view.current!;
    v.zoom = THREE.MathUtils.damp(v.zoom, v.targetZoom, 6, dt);
    camera.position.set(0, cfg.height, v.zoom);
    camera.lookAt(0, cfg.lookY, 0);
    if (still || v.held) return;
    // Flick inertia decays; after 4 s without input the model idles into a slow spin.
    v.rotY += v.velY;
    v.velY *= Math.exp(-dt * 3);
    if (performance.now() - v.lastInput > 4000) v.rotY += dt * 0.18;
  });
  return null;
}

export function SpinControls({ spin }: { spin: ReturnType<typeof useSpin> }) {
  return (
    <>
      <div
        className="absolute top-3 right-3 flex gap-1"
        onPointerDown={(e) => e.stopPropagation()}
        onDoubleClick={(e) => e.stopPropagation()}
      >
        {(
          [
            ["−", "Zoom out", () => spin.zoomBy(1.2)],
            ["+", "Zoom in", () => spin.zoomBy(1 / 1.2)],
            ["⟲", "Reset view", spin.reset],
          ] as const
        ).map(([sym, label, fn]) => (
          <button
            key={label}
            type="button"
            onClick={fn}
            aria-label={label}
            title={label}
            className="frame grid size-8 cursor-pointer place-items-center bg-panel/70 text-sm text-soft hover:text-ink"
          >
            {sym}
          </button>
        ))}
      </div>
      <p
        className={`pointer-events-none absolute right-3 bottom-3 text-[11px] transition-colors ${spin.hint ? "text-accent-hi" : "text-mute"}`}
      >
        Drag to rotate · {spin.hint ? "hold Ctrl to zoom" : "Ctrl + scroll to zoom"} · double-click to reset
      </p>
    </>
  );
}

export function Tooltip({
  at,
  width,
  children,
}: {
  at: { x: number; y: number };
  width: number;
  children: React.ReactNode;
}) {
  return (
    <div
      className="frame pointer-events-none absolute z-10 max-w-64 bg-panel/95 px-3 py-2 text-xs text-ink backdrop-blur-md"
      style={{ left: Math.max(8, Math.min(at.x + 14, width - 264)), top: at.y + 14 }}
    >
      {children}
    </div>
  );
}
