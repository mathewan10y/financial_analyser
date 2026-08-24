export function getSentimentLabel(score: number): string {
  if (score > 0.15) return 'Bullish';
  if (score < -0.15) return 'Bearish';
  return 'Neutral';
}

export function getSentimentColors(score: number) {
  if (score > 0.15) {
    return {
      badge: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
      dot: 'bg-emerald-400',
    };
  }
  if (score < -0.15) {
    return {
      badge: 'bg-red-500/15 text-red-400 border-red-500/30',
      dot: 'bg-red-400',
    };
  }
  return {
    badge: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    dot: 'bg-amber-400',
  };
}

export function getVerdictStyles(decision: 'BUY' | 'HOLD' | 'SELL') {
  switch (decision) {
    case 'BUY':
      return {
        text: 'text-emerald-400 text-glow-emerald',
        ring: 'stroke-emerald-400',
        glow: 'shadow-glow-emerald',
        bg: 'from-emerald-500/10 to-emerald-900/5',
        border: 'border-emerald-500/30',
        icon: 'text-emerald-400',
      };
    case 'SELL':
      return {
        text: 'text-red-400 text-glow-crimson',
        ring: 'stroke-red-400',
        glow: 'shadow-glow-crimson',
        bg: 'from-red-500/10 to-red-900/5',
        border: 'border-red-500/30',
        icon: 'text-red-400',
      };
    default:
      return {
        text: 'text-amber-400 text-glow-amber',
        ring: 'stroke-amber-400',
        glow: 'shadow-glow-amber',
        bg: 'from-amber-500/10 to-amber-900/5',
        border: 'border-amber-500/30',
        icon: 'text-amber-400',
      };
  }
}

export function formatDate(iso?: string): string {
  if (!iso || iso === 'Live' || iso === 'N/A') return 'Live Telemetry';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return 'Live Telemetry';
    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return 'Live Telemetry';
  }
}

export function parseReasoningSteps(text: string): string[] {
  const numbered = text.split(/(?=\d+\.\s)/).filter((s) => s.trim());
  if (numbered.length > 1) return numbered.map((s) => s.trim());
  return text.split(/\n\n+/).filter((s) => s.trim());
}
