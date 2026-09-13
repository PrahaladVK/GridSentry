export function Skeleton({ width = "100%", height = 16, radius = 8, style }) {
  return <div className="skeleton" style={{ width, height, borderRadius: radius, ...style }} />;
}

export function TopProgress({ active }) {
  if (!active) return null;
  return <div className="top-progress" />;
}
