import { CheckCircle2, Loader2, Circle } from 'lucide-react';
import { PIPELINE_STEPS } from '../data/mockData';

interface PipelineProgressProps {
  currentStep: number;
  isRunning: boolean;
}

export default function PipelineProgress({
  currentStep,
  isRunning,
}: PipelineProgressProps) {
  if (!isRunning && currentStep === 0) return null;

  return (
    <div className="mt-4 rounded-xl border border-slate-700/60 bg-slate-900/60 p-4 backdrop-blur-sm">
      <div className="mb-3 flex items-center gap-2">
        {isRunning ? (
          <Loader2 className="h-4 w-4 animate-spin text-emerald-400" />
        ) : (
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
        )}
        <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
          {isRunning ? 'Pipeline Executing' : 'Pipeline Complete'}
        </span>
      </div>

      <div className="space-y-2">
        {PIPELINE_STEPS.map((step, index) => {
          const isComplete = index < currentStep;
          const isActive = index === currentStep && isRunning;
          const isPending = index > currentStep;

          return (
            <div
              key={step.id}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 transition-all ${
                isActive
                  ? 'bg-emerald-500/10 border border-emerald-500/20'
                  : isComplete
                    ? 'opacity-80'
                    : 'opacity-40'
              }`}
            >
              {isComplete ? (
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
              ) : isActive ? (
                <Loader2 className="h-4 w-4 shrink-0 animate-spin text-emerald-400" />
              ) : (
                <Circle className="h-4 w-4 shrink-0 text-slate-600" />
              )}
              <span
                className={`font-mono text-xs ${
                  isActive
                    ? 'text-emerald-300'
                    : isComplete
                      ? 'text-slate-300'
                      : isPending
                        ? 'text-slate-500'
                        : 'text-slate-400'
                }`}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>

      <div className="mt-3 h-1 overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-gradient-to-r from-emerald-600 to-emerald-400 transition-all duration-500"
          style={{
            width: `${isRunning ? ((currentStep + 1) / PIPELINE_STEPS.length) * 100 : 100}%`,
          }}
        />
      </div>
    </div>
  );
}
