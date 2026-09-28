// A cell is [x, y(up), z, highlight]. Faces carry baked light so the form reads at any angle.
export type Cell = [number, number, number, 0 | 1];

const FACES: [transform: string, light: number][] = [
  ["rotateX(90deg)", 100],
  ["rotateY(0deg)", 70],
  ["rotateY(180deg)", 70],
  ["rotateY(90deg)", 48],
  ["rotateY(-90deg)", 48],
];

export function Voxel({ cells, unit = 14 }: { cells: Cell[]; unit?: number }) {
  const mid = (i: 0 | 1 | 2) => {
    const v = cells.map((c) => c[i]);
    return (Math.min(...v) + Math.max(...v)) / 2;
  };
  const [cx, cy, cz] = [mid(0), mid(1), mid(2)];

  return (
    <div
      className="voxel-scene grid place-items-center"
      style={{ width: unit * 7, height: unit * 7 }}
      aria-hidden
    >
      <div className="voxel-rig">
        {cells.map(([x, y, z, hl], i) => (
          <div
            key={i}
            className="voxel"
            style={{
              width: unit,
              height: unit,
              left: -unit / 2,
              top: -unit / 2,
              transform: `translate3d(${(x - cx) * unit}px, ${-(y - cy) * unit}px, ${(z - cz) * unit}px)`,
            }}
          >
            {FACES.map(([t, light]) => (
              <i
                key={t}
                style={{
                  transform: `${t} translateZ(${unit / 2}px)`,
                  background: `color-mix(in oklab, ${hl ? "var(--color-accent-hi)" : "var(--color-m-partial)"} ${light}%, var(--color-bg))`,
                }}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
