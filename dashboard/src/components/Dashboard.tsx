import { useState, useCallback } from 'react';
import {
  Activity,
  Zap,
  Radio,
  BarChart3,
  AlertCircle,
} from 'lucide-react';
import SearchBar from './SearchBar';
import PipelineProgress from './PipelineProgress';
import PipelineVisualization from './PipelineVisualization';
import VerdictBoard from './VerdictBoard';
import { MOCK_DATA } from '../data/mockData';
import { runPipelineWithProgress } from '../api/analyze';
import type { AnalysisResponse } from '../types';

export default function Dashboard() {
  const [data, setData] = useState<AnalysisResponse>(MOCK_DATA);
  const [selectedTicker, setSelectedTicker] = useState('AAPL');
  const [isRunning, setIsRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const handleRunPipeline = useCallback(async () => {
    if (!selectedTicker || isRunning) return;

    setIsRunning(true);
    setCurrentStep(0);
    setError(null);

    try {
      const result = await runPipelineWithProgress(
        selectedTicker,
        (stepIndex) => setCurrentStep(stepIndex + 1),
      );
      setData(result);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Pipeline execution failed. Ensure the backend is running on port 8000.',
      );
    } finally {
      setIsRunning(false);
    }
  }, [selectedTicker, isRunning]);

  return (
    <div className="min-h-screen bg-terminal-bg">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(16,185,129,0.06)_0%,_transparent_50%)]" />
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_bottom_right,_rgba(239,68,68,0.04)_0%,_transparent_40%)]" />

      <div className="relative mx-auto max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-8">
          <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500/20 to-emerald-700/10 ring-1 ring-emerald-500/30">
                <Activity className="h-5 w-5 text-emerald-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-tight text-slate-100">
                  Synapse Financial Intelligence
                </h1>
                <p className="flex items-center gap-1.5 text-xs text-slate-500">
                  <Radio className="h-3 w-3 text-emerald-500" />
                  Multi-Agent Sentiment Terminal
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="hidden items-center gap-2 rounded-lg border border-slate-700/60 bg-slate-900/60 px-3 py-2 sm:flex">
                <BarChart3 className="h-3.5 w-3.5 text-slate-500" />
                <span className="font-mono text-xs text-slate-400">
                  {data.ticker} · {data.payload_length} signals
                </span>
              </div>
              <div className="flex items-center gap-1.5 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-2">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
                </span>
                <span className="text-xs font-medium text-emerald-400">Live</span>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
            <SearchBar
              activeTicker={selectedTicker}
              onTickerSelect={setSelectedTicker}
            />

            {selectedTicker && (
              <button
                onClick={handleRunPipeline}
                disabled={isRunning}
                className="flex shrink-0 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-emerald-500 px-6 py-3.5 font-semibold text-white shadow-lg shadow-emerald-500/20 transition-all hover:from-emerald-500 hover:to-emerald-400 hover:shadow-emerald-500/30 disabled:cursor-not-allowed disabled:opacity-50 lg:min-w-[220px]"
              >
                {isRunning ? (
                  <>
                    <Activity className="h-4 w-4 animate-pulse" />
                    Running Pipeline...
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4" />
                    Run Sentiment Pipeline
                  </>
                )}
              </button>
            )}
          </div>

          <PipelineProgress currentStep={currentStep} isRunning={isRunning} />

          {error && (
            <div className="mt-4 flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-950/30 px-4 py-3 text-sm text-red-400">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}
        </header>

        <main className="grid grid-cols-1 gap-6 lg:grid-cols-5 lg:gap-8">
          <div className="lg:col-span-2">
            <PipelineVisualization dataset={data.dataset} ticker={data.ticker} />
          </div>
          <div className="lg:col-span-3">
            <VerdictBoard verdict={data.final_verdict} ticker={data.ticker} />
          </div>
        </main>

        <footer className="mt-8 border-t border-slate-800 pt-4 text-center">
          <p className="font-mono text-[10px] uppercase tracking-widest text-slate-600">
            Synapse Quant Engine v1.0 · Local GPU + Cloud Orchestrator
          </p>
        </footer>
      </div>
    </div>
  );
}
