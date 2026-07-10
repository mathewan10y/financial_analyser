import { useState, useCallback } from 'react';
import {
  Activity,
  Zap,
  Radio,
  AlertCircle,
  Search,
  FileText,
} from 'lucide-react';
import SearchBar from './SearchBar';
import PipelineProgress from './PipelineProgress';
import PipelineVisualization from './PipelineVisualization';
import VerdictBoard from './VerdictBoard';
import MultiPersonaPipeline from './MultiPersonaPipeline';
import { runPipelineWithProgress } from '../api/analyze';
import type { AnalysisResponse } from '../types';

export default function Dashboard() {
  const [data, setData] = useState<AnalysisResponse | null>(null);
  const [selectedTicker, setSelectedTicker] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [hasRunOnce, setHasRunOnce] = useState(false);
  const [isFetching, setIsFetching] = useState(false); // Separate fetch state from animation

  const handleRunPipeline = useCallback(async () => {
    if (!selectedTicker || isRunning) return;

    setIsRunning(true);
    setIsFetching(true);
    setCurrentStep(0);
    setError(null);
    setHasRunOnce(true);
    setData(null); // Clear previous data

    try {
      const result = await runPipelineWithProgress(
        selectedTicker,
        (stepIndex) => setCurrentStep(stepIndex + 1),
      );
      setData(result);
      setIsFetching(false); // Data arrived, stop showing skeleton
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Pipeline execution failed. Ensure the backend is running on port 8000.',
      );
      setIsFetching(false);
    } finally {
      setIsRunning(false);
    }
  }, [selectedTicker, isRunning]);


  return (
    <div className="min-h-screen bg-terminal-bg">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(16,185,129,0.06)_0%,_transparent_50%)]" />
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_bottom_right,_rgba(239,68,68,0.04)_0%,_transparent_40%)]" />

      <div className="relative mx-auto max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8">
        {/* Header */}
        <header className="mb-6">
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
        </header>

        {/* Main 2-Column Grid */}
        <main className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:gap-8">
          {/* LEFT COLUMN - Search & Articles (span 5) */}
          <div className="lg:col-span-5 flex flex-col gap-6">
            {/* Search Bar Section */}
            <div className="rounded-2xl border border-slate-700/60 bg-terminal-panel/80 backdrop-blur-sm p-4">
              <SearchBar
                activeTicker={selectedTicker}
                onTickerSelect={setSelectedTicker}
              />
              {selectedTicker && (
                <button
                  onClick={handleRunPipeline}
                  disabled={isRunning}
                  className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-emerald-500 px-6 py-3.5 font-semibold text-white shadow-lg shadow-emerald-500/20 transition-all hover:from-emerald-500 hover:to-emerald-400 hover:shadow-emerald-500/30 disabled:cursor-not-allowed disabled:opacity-50"
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
              <PipelineProgress currentStep={currentStep} isRunning={isRunning} />
              {error && (
                <div className="mt-4 flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-950/30 px-4 py-3 text-sm text-red-400">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  {error}
                </div>
              )}
            </div>

            {/* Article Cards Section */}
            <div className="flex-1 rounded-2xl border border-slate-700/60 bg-terminal-panel/80 backdrop-blur-sm p-4">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-slate-100">Pipeline Architecture</h2>
                <span className="rounded-full border border-slate-700 bg-slate-800/80 px-3 py-1 font-mono text-xs text-slate-400">
                  {data?.dataset.length || 0} articles
                </span>
              </div>
              
              {isFetching ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="rounded-xl border border-slate-700/60 bg-slate-900/50 p-4 animate-pulse">
                      <div className="mb-3 h-4 w-3/4 rounded bg-slate-700/50" />
                      <div className="mb-2 h-3 w-1/2 rounded bg-slate-700/50" />
                      <div className="grid grid-cols-2 gap-2">
                        <div className="h-16 rounded-lg border border-slate-700/30 bg-slate-800/30" />
                        <div className="h-16 rounded-lg border border-slate-700/30 bg-slate-800/30" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : data ? (
                <PipelineVisualization dataset={data.dataset} ticker={data.ticker} />
              ) : (
                <div className="flex h-48 flex-col items-center justify-center text-slate-500">
                  <FileText className="mb-2 h-8 w-8 opacity-40" />
                  <p className="text-sm">Select an asset to begin quant analysis</p>
                </div>
              )}
            </div>
          </div>

          {/* RIGHT COLUMN - Intelligence Hub (span 7) */}
          <div className="lg:col-span-7">
            <div className="h-full rounded-2xl border border-slate-700/60 bg-terminal-panel/80 backdrop-blur-sm p-4">
              {!hasRunOnce ? (
                // State A: Idle
                <div className="flex h-full flex-col items-center justify-center text-slate-500">
                  <Search className="mb-4 h-16 w-16 opacity-30" />
                  <h3 className="mb-2 text-lg font-semibold text-slate-400">Ready to Analyze</h3>
                  <p className="text-sm">Select a ticker and run the sentiment pipeline</p>
                </div>
              ) : isRunning ? (
                // State B: Loading - MultiPersonaPipeline confined to panel
                <MultiPersonaPipeline 
                  isRunning={isRunning} 
                />
              ) : data ? (
                // State C: Success - VerdictBoard
                <VerdictBoard verdict={data.final_verdict} ticker={data.ticker} />
              ) : null}
            </div>
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
