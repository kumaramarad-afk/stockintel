import { scoreColor } from "@/lib/format";

export function ScoreGauge({ score }: { score: number | null }) {
  const value = score == null ? 0 : Math.max(0, Math.min(100, score));
  const color = score == null ? "#8b8b9e" : value <= 50 ? "#f43f5e" : value <= 70 ? "#fbbf24" : "#00d4aa";
  const radius = 58;
  const start = Math.PI * 0.75;
  const sweep = Math.PI * 1.5;
  const cx = 80;
  const cy = 86;
  const arc = (ratio: number) => {
    const angle = start + sweep * ratio;
    return { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) };
  };
  const end = arc(value / 100);
  const large = value / 100 > 0.5 ? 1 : 0;
  const startPt = arc(0);

  return (
    <div className="relative mx-auto h-44 w-44">
      <svg viewBox="0 0 160 150" className="h-full w-full">
        <path
          d={`M ${startPt.x} ${startPt.y} A ${radius} ${radius} 0 1 1 ${arc(1).x} ${arc(1).y}`}
          fill="none"
          stroke="#1e1e2e"
          strokeWidth="12"
          strokeLinecap="round"
        />
        {score != null && (
          <path
            d={`M ${startPt.x} ${startPt.y} A ${radius} ${radius} 0 ${large} 1 ${end.x} ${end.y}`}
            fill="none"
            stroke={color}
            strokeWidth="12"
            strokeLinecap="round"
          />
        )}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center pt-4">
        <p className={`text-5xl font-semibold tracking-tight ${scoreColor(score)}`}>{score ?? "—"}</p>
        <p className="mt-1 text-[11px] uppercase tracking-[0.2em] text-gsr-muted">Composite</p>
      </div>
    </div>
  );
}
