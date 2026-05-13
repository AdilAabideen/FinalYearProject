// Provides diagram helpers.
export type DiagramPoint = { x: number; y: number };

// Gets schema label.
export function getSchemaLabel(schema: Record<string, unknown>) {
  const title = schema.title;
  if (typeof title === 'string' && title.trim().length) return title;

  const ref = schema.$ref;
  if (typeof ref === 'string' && ref.trim().length) return ref.split('/').at(-1) ?? 'Input';

  return 'Input';
}

// Clamps logic.
export function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

// Computes radial positions.
export function computeRadialPositions(count: number): DiagramPoint[] {
  if (count <= 0) return [];

  const itemsPerRing = 8;
  const ringCount = Math.max(1, Math.ceil(count / itemsPerRing));

  const minRadius = 26;
  const maxRadius = 46;
// Handles from.
  const radii = Array.from({ length: ringCount }, (_, ring) => {
    if (ringCount === 1) return 38;
    return minRadius + (ring * (maxRadius - minRadius)) / (ringCount - 1);
  });

  const points: DiagramPoint[] = [];

  for (let ring = 0; ring < ringCount; ring += 1) {
    const start = ring * itemsPerRing;
    const end = Math.min(count, start + itemsPerRing);
    const ringItems = end - start;
    const radius = radii[ring] ?? 38;

    for (let i = 0; i < ringItems; i += 1) {
      const angle = -Math.PI / 2 + (2 * Math.PI * i) / ringItems;
      points.push({
        x: 50 + radius * Math.cos(angle),
        y: 50 + radius * Math.sin(angle),
      });
    }
  }

  return points;
}

// Handles curved connector path.
export function curvedConnectorPath(from: DiagramPoint, to: DiagramPoint, curve: number) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const dist = Math.hypot(dx, dy) || 1;

  const px = -dy / dist;
  const py = dx / dist;

  const c1 = {
    x: from.x + dx * 0.28 + px * curve,
    y: from.y + dy * 0.28 + py * curve,
  };

  const c2 = {
    x: from.x + dx * 0.72 + px * curve,
    y: from.y + dy * 0.72 + py * curve,
  };

  return `M ${from.x} ${from.y} C ${c1.x} ${c1.y} ${c2.x} ${c2.y} ${to.x} ${to.y}`;
}

// Builds initial positions.
export function makeInitialPositions(count: number) {
// Maps logic.
  return computeRadialPositions(count).map((p) => {
    const dx = p.x - 50;
    const dy = p.y - 50;
    const x = 50 + dx * 0.82;
    const y = 50 + dy * 0.9;

    return {
      x: clamp(x, 14, 86),
      y: clamp(y, 12, 88),
    };
  });
}

// Formats tool name.
export function formatToolName(toolName: string) {
  return toolName
    .replace(/_/g, ' ')
// Handles replace.
    .replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.slice(1));
}
