import { useState, useCallback } from 'react';
import {
  Activity,
  Zap,
  Radio,
  AlertCircle,
  Layers,
  Sparkles,
} from 'lucide-react';
import SearchBar from './SearchBar';
import VerdictBoard from './VerdictBoard';
import MultiPersonaPipeline from './MultiPersonaPipeline';
import ArticleDrawer from './ArticleDrawer';
import { runPipelineWithProgress, type StreamUpdate } from '../api/analyze';
import type { AnalysisResponse, ArticleData } from '../types';

export default function Dashboard() {
  const [data, setData] = useState<AnalysisResponse | null>(null);
  const [articles, setArticles] = useState<ArticleData[]>([]);
  const [selectedTicker, setSelectedTicker] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<StreamUpdate['phase'] | null>(null);
  const [activeAgent, setActiveAgent] = useState<StreamUpdate['agent'] | null>(null);
  const [agentOutputs, setAgentOutputs] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [hasRunOnce, setHasRunOnce] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const handleRunPipeline = useCallback(async () => {
    if (!selectedTicker || isRunning) return;

    setIsRunning(true);
    setCurrentPhase(null);
    setActiveAgent(null);
    setAgentOutputs({});
    setError(null);
    setHasRunOnce(true);
    setData(null);
    setArticles([]);

    try {
      const result = await runPipelineWithProgress(
        selectedTicker,
        (update: StreamUpdate) => {
          setCurrentPhase(update.phase);
          setActiveAgent(update.agent ?? null);

          // Handle progressive articles ingested event
          if (update.phase === 'articles_ingested' && Array.isArray(update.articles)) {
            setArticles(
              update.articles.map((a: any) => ({
                date: a.date || new Date().toISOString(),
                headline: a.headline || a.title || 'Market Telemetry Feed',
                link: a.link || '#',
                full_text: a.full_text || '',
              })),
            );
          }

          // Handle progressive GPU sentiment telemetry event
          if (update.phase === 'sentiment_telemetry' && Array.isArray(update.telemetry)) {
            setArticles(update.telemetry);
          }

          if (update.phase === 'agent_result' && update.agent && update.text) {
            setAgentOutputs((prev) => ({
              ...prev,
              [update.agent!]: update.text!,
            }));
          }

          if (update.phase === 'error') {
            setError(update.message || 'Pipeline error occurred');
            setIsRunning(false);
          }
        },
      );
      setData(result);
      if (result?.dataset) {
        setArticles(result.dataset);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Pipeline execution failed. Ensure the backend is running on port 8000.',
      );
    } finally {
      setIsRunning(false);
      setCurrentPhase(null);
      setActiveAgent(null);
    }
  }, [selectedTicker, isRunning]);

  const activeArticleCount = data?.dataset ? data.dataset.length : articles.length;

  return (
    <div className="min-h-screen bg-terminal-bg text-slate-100 pb-12">
      {/* Subtle background ambient gradients */}
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(16,185,129,0.07)_0%,_transparent_50%)]" />
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_bottom_right,_rgba(168,85,247,0.05)_0%,_transparent_40%)]" />

      <div className="relative mx-auto max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8">
        {/* Header & Global Control Bar */}
        <header className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-5">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500/20 to-emerald-700/10 ring-1 ring-emerald-500/30 shadow-lg shadow-emerald-500/10 shrink-0">
              <Activity className="h-6 w-6 text-emerald-400" />
            </div>
            <div>
              <h1 className="text-xl font-black tracking-tight text-slate-100 flex items-center gap-2">
                SYNAPSE
                <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                  QUANT v2.5
                </span>
              </h1>
              <p className="flex flex-wrap items-center gap-1.5 text-xs sm:text-sm md:text-base text-slate-400">
                <Radio className="h-3 w-3 text-emerald-400 animate-pulse shrink-0" />
                Multi-Agent Autonomous Financial Sentiment Intelligence
              </p>
            </div>
          </div>

          {/* Quick Drawer Action Pill */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsDrawerOpen(true)}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-700/80 bg-slate-900/80 px-4 py-2.5 text-xs font-medium text-slate-300 backdrop-blur-sm transition-all hover:border-emerald-500/50 hover:bg-slate-800 hover:text-emerald-400 shadow-sm"
            >
              <Layers className="h-4 w-4 text-emerald-400" />
              <span>Ingested Sources</span>
              <span className="rounded-full bg-slate-800 px-2 py-0.5 font-mono text-[10px] text-emerald-400 border border-slate-700">
                {activeArticleCount}
              </span>
            </button>
          </div>
        </header>

        {/* Search & Launch Toolbar (Elevated z-index for dropdown layering) */}
        <section className="relative z-40 mb-8 rounded-2xl border border-slate-700/60 bg-terminal-panel/90 backdrop-blur-md p-4 shadow-xl">
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
            <div className="flex-1">
              <SearchBar
                activeTicker={selectedTicker}
                onTickerSelect={setSelectedTicker}
              />
            </div>

            <button
              onClick={handleRunPipeline}
              disabled={!selectedTicker || isRunning}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-emerald-500 px-6 py-3.5 font-semibold text-white shadow-lg shadow-emerald-500/20 transition-all hover:from-emerald-500 hover:to-emerald-400 hover:shadow-emerald-500/30 disabled:cursor-not-allowed disabled:opacity-50 min-w-[220px]"
            >
              {isRunning ? (
                <>
                  <Activity className="h-4 w-4 animate-pulse" />
                  Running Deliberation...
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4" />
                  Run Multi-Agent Pipeline
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="mt-4 flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-950/30 px-4 py-3 text-sm text-red-400">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}
        </section>

        {/* Main Deliberation Workbench */}
        <main className="relative z-10 space-y-6">
          {!hasRunOnce && !isRunning && !data ? (
            /* State A: Ready / Idle Welcome View */
            <div className="max-w-full overflow-hidden rounded-2xl border border-slate-700/60 bg-terminal-panel/80 backdrop-blur-sm p-4 sm:p-8 text-center shadow-xl">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/30 mb-4">
                <Sparkles className="h-8 w-8" />
              </div>
              <h2 className="text-xl font-bold text-slate-100 mb-2">
                Terminal Ready for Autonomous Quant Analysis
              </h2>
              <p className="text-sm text-slate-400 max-w-xl mx-auto mb-6 leading-relaxed">
                Select a stock ticker symbol above (e.g. <span className="font-mono text-emerald-400 font-semibold">NVDA</span>, <span className="font-mono text-emerald-400 font-semibold">AAPL</span>, <span className="font-mono text-emerald-400 font-semibold">TSLA</span>) to dispatch our 5-agent parallel debate sequence and synthesize an institutional capital allocation verdict.
              </p>
              <div className="inline-flex flex-col sm:flex-row flex-wrap items-center justify-center gap-4 sm:gap-2 rounded-xl border border-slate-800 bg-slate-900/60 p-4 sm:px-6 sm:py-3 text-xs text-slate-400 font-mono max-w-full">
                <span>Phase 1: Deterministic Filter & GPU</span>
                <span className="hidden sm:block text-slate-600">•</span>
                <span>Phase 2: 3-Desk Parallel Debate</span>
                <span className="hidden sm:block text-slate-600">•</span>
                <span>Phase 3: CRO Risk Stress-Test</span>
                <span className="hidden sm:block text-slate-600">•</span>
                <span>Phase 4: Synthesis</span>
              </div>
            </div>
          ) : isRunning ? (
            /* State B: Live Streaming Execution View */
            <div className="rounded-2xl border border-slate-700/60 bg-terminal-panel/90 backdrop-blur-sm p-6 shadow-2xl space-y-4">
              {currentPhase === 'scraping' && (
                <div className="flex items-center gap-3 rounded-xl border border-emerald-500/30 bg-emerald-950/30 p-3.5 text-emerald-400 animate-in fade-in duration-200">
                  <Activity className="h-4 w-4 animate-spin shrink-0 text-emerald-400" />
                  <div className="flex-1 text-xs">
                    <span className="font-semibold text-emerald-300">Fetching global market news & telemetry...</span>
                    <span className="text-emerald-400/70 ml-2">Running 12-second multi-tier RSS query search for {selectedTicker}</span>
                  </div>
                  <button
                    onClick={() => setIsDrawerOpen(true)}
                    className="text-xs text-emerald-400 hover:text-emerald-300 underline font-medium shrink-0"
                  >
                    View Ingestion Feed
                  </button>
                </div>
              )}

              <MultiPersonaPipeline
                isRunning={isRunning}
                currentPhase={currentPhase}
                activeAgent={activeAgent}
                agentOutputs={agentOutputs}
              />
            </div>
          ) : data ? (
            /* State C: Success Verdict + Persistent Deliberation Pipeline View */
            <div className="space-y-6 animate-in fade-in duration-300">
              {/* Verdict Header Board */}
              <VerdictBoard verdict={data.final_verdict} ticker={data.ticker} />

              {/* Persistent Pipeline Transcript Board */}
              <div className="rounded-2xl border border-slate-700/60 bg-terminal-panel/90 backdrop-blur-sm p-6 shadow-2xl">
                <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10">
                      <Activity className="h-4 w-4 text-emerald-400" />
                    </div>
                    <div>
                      <h2 className="text-sm font-bold text-slate-100">
                        Multi-Agent Deliberation Architecture & Transcript
                      </h2>
                      <p className="text-xs text-slate-400">
                        Complete autonomous debate transcript for {data.ticker}
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={() => setIsDrawerOpen(true)}
                    className="text-xs text-emerald-400 hover:text-emerald-300 font-medium inline-flex items-center gap-1.5 transition-colors"
                  >
                    <Layers className="h-3.5 w-3.5" />
                    View Ingested Telemetry ({data.dataset.length})
                  </button>
                </div>

                <MultiPersonaPipeline
                  isRunning={false}
                  currentPhase="complete"
                  activeAgent={null}
                  agentOutputs={agentOutputs}
                />
              </div>
            </div>
          ) : null}
        </main>

        {/* Slide-Over Ingested Sources Drawer */}
        <ArticleDrawer
          isOpen={isDrawerOpen}
          onClose={() => setIsDrawerOpen(false)}
          dataset={data?.dataset || articles}
          ticker={data?.ticker || selectedTicker}
          isScraping={currentPhase === 'scraping' || (isRunning && articles.length === 0)}
        />

        {/* Footer */}
        <footer className="mt-12 border-t border-slate-800 pt-6 text-center">
          <p className="font-mono text-[11px] uppercase tracking-widest text-slate-600">
            Synapse Quant Engine v2.5 · Parallel Multi-Agent LLM + Deterministic Ingestion
          </p>
        </footer>
      </div>
    </div>
  );
}
