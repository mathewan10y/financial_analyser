import {
  Shield,
  TrendingDown,
  TrendingUp,
  Minus,
  AlertTriangle,
  FileCheck2,
} from 'lucide-react';
import type { FinalVerdict } from '../types';
import { getVerdictStyles } from '../utils/sentiment';
import ConfidenceRing from './ConfidenceRing';

interface VerdictBoardProps {
  verdict: FinalVerdict;
  ticker: string;
}

function VerdictIcon({ decision }: { decision: 'BUY' | 'HOLD' | 'SELL' }) {
  switch (decision) {
    case 'BUY':
      return <TrendingUp className="h-7 w-7" />;
    case 'SELL':
      return <TrendingDown className="h-7 w-7" />;
    default:
      return <Minus className="h-7 w-7" />;
  }
}

export default function VerdictBoard({ verdict, ticker }: VerdictBoardProps) {
  const styles = getVerdictStyles(verdict.decision);

  return (
    <section
      className={`relative overflow-hidden rounded-2xl border bg-gradient-to-b ${styles.bg} ${styles.border} backdrop-blur-md shadow-2xl p-6 mb-6`}
    >
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-700/50 pb-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-900/80 ring-1 ring-slate-700">
            <Shield className={`h-5 w-5 ${styles.icon}`} />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              Multi-Agent Quantitative Verdict
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-emerald-400 border border-slate-700">
                {ticker}
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Orchestrator capital allocation decision synthesized from 5 autonomous personas
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 px-3 py-1 text-xs font-mono text-emerald-400 font-semibold">
            <FileCheck2 className="h-3.5 w-3.5" />
            SYNTHESIS FINALIZED
          </span>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        {/* Left / Primary: Final Decision & Confidence Ring */}
        <div className="lg:col-span-5 flex flex-col sm:flex-row lg:flex-col items-center justify-center gap-6 rounded-xl border border-slate-800/80 bg-slate-950/60 p-6 shadow-inner">
          <div className={`flex flex-col items-center ${styles.glow}`}>
            <span className="mb-2 text-[10px] font-mono font-bold uppercase tracking-[0.25em] text-slate-400">
              Allocation Ruling
            </span>
            <div className={`flex items-center gap-3 ${styles.text}`}>
              <VerdictIcon decision={verdict.decision} />
              <span className="font-mono text-5xl sm:text-6xl font-black tracking-tight">
                {verdict.decision}
              </span>
            </div>
          </div>

          <div className="flex flex-col items-center">
            <ConfidenceRing
              score={verdict.confidence_score}
              decision={verdict.decision}
            />
          </div>
        </div>

        {/* Right / Secondary: Executive Summary & Resolution Logic */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          <div className="relative overflow-hidden rounded-xl border border-amber-500/30 bg-amber-950/15 p-4 shadow-sm">
            <div className="absolute left-0 top-0 h-full w-1.5 bg-gradient-to-b from-amber-400 to-amber-600" />
            <div className="mb-1.5 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-400" />
              <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-amber-300">
                Executive Justification
              </span>
            </div>
            <p className="pl-1 text-sm font-medium leading-relaxed text-slate-100">
              {verdict.executive_summary}
            </p>
          </div>

          {verdict.internal_reasoning_process && (
            <div className="rounded-xl border border-slate-700/60 bg-slate-900/60 p-4">
              <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-slate-400 mb-1.5 block">
                Internal Conflict Resolution Breakdown
              </span>
              <p className="font-mono text-xs leading-relaxed text-slate-300">
                {verdict.internal_reasoning_process}
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
