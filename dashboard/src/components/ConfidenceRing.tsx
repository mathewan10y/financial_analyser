interface ConfidenceRingProps {
  score: number;
  decision: 'BUY' | 'HOLD' | 'SELL';
}

export default function ConfidenceRing({ score, decision }: ConfidenceRingProps) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  const strokeColor =
    decision === 'BUY'
      ? '#34d399'
      : decision === 'SELL'
        ? '#f87171'
        : '#fbbf24';

  const glowColor =
    decision === 'BUY'
      ? 'rgba(16, 185, 129, 0.3)'
      : decision === 'SELL'
        ? 'rgba(239, 68, 68, 0.3)'
        : 'rgba(245, 158, 11, 0.3)';

  return (
    <div className="relative flex flex-col items-center">
      <svg
        width="140"
        height="140"
        viewBox="0 0 140 140"
        className="-rotate-90"
        style={{ filter: `drop-shadow(0 0 12px ${glowColor})` }}
      >
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke="#1e293b"
          strokeWidth="8"
        />
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke={strokeColor}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono text-3xl font-bold text-slate-100">{score}</span>
        <span className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
          Confidence
        </span>
      </div>
    </div>
  );
}
