import {
  Shield,
  TrendingDown,
  TrendingUp,
  Minus,
  AlertTriangle,
} from 'lucide-react';
import type { FinalVerdict } from '../types';
import { getVerdictStyles } from '../utils/sentiment';
import ConfidenceRing from './ConfidenceRing';
import ReasoningAccordion from './ReasoningAccordion';

interface VerdictBoardProps {
  verdict: FinalVerdict;
  ticker: string;
}

function VerdictIcon({ decision }: { decision: 'BUY' | 'HOLD' | 'SELL' }) {
  switch (decision) {
    case 'BUY':
      return <TrendingUp className="h-6 w-6" />;
    case 'SELL':
      return <TrendingDown className="h-6 w-6" />;
    default:
      return <Minus className="h-6 w-6" />;
  }
}

export default function VerdictBoard({ verdict, ticker }: VerdictBoardProps) {
  const styles = getVerdictStyles(verdict.decision);

  return (
    <section
      className={`flex h-full flex-col rounded-2xl border bg-gradient-to-b ${styles.bg} ${styles.border} backdrop-blur-sm`}
    >
      <header className="flex items-center gap-2.5 border-b border-slate-700/40 px-5 py-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-800/80">
          <Shield className={`h-4 w-4 ${styles.icon}`} />
        </div>
        <div>
          <h2 className="text-sm font-semibold text-slate-100">
            Multi-Agent Debate Verdict
          </h2>
          <p className="text-xs text-slate-500">
            Orchestrator synthesis — {ticker}
          </p>
        </div>
      </header>

      <div className="flex flex-1 flex-col gap-5 overflow-y-auto p-5">
        <div className="relative overflow-hidden rounded-xl border border-slate-700/50 bg-slate-900/60 p-4">
          <div className="absolute left-0 top-0 h-full w-1 bg-gradient-to-b from-emerald-500 to-emerald-700" />
          <div className="mb-2 flex items-center gap-2">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
            <span className="text-[10px] font-bold uppercase tracking-widest text-amber-400/80">
              Executive Summary
            </span>
          </div>
          <p className="pl-1 text-sm font-medium leading-relaxed text-slate-200">
            {verdict.executive_summary}
          </p>
        </div>

        <div className={`flex flex-col items-center rounded-2xl border border-slate-700/40 bg-slate-900/40 py-8 ${styles.glow}`}>
          <span className="mb-2 text-[10px] font-bold uppercase tracking-[0.3em] text-slate-500">
            Final Decision
          </span>
          <div className={`flex items-center gap-4 ${styles.text}`}>
            <VerdictIcon decision={verdict.decision} />
            <span className="font-mono text-6xl font-black tracking-tight sm:text-7xl">
              {verdict.decision}
            </span>
          </div>
        </div>

        <div className="flex justify-center">
          <ConfidenceRing
            score={verdict.confidence_score}
            decision={verdict.decision}
          />
        </div>

        <ReasoningAccordion reasoning={verdict.internal_reasoning_process} />
      </div>
    </section>
  );
}
