import { useEffect } from 'react';
import { X, Layers, FileText, Loader2 } from 'lucide-react';
import type { ArticleData } from '../types';
import ArticleCard from './ArticleCard';

interface ArticleDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  dataset: ArticleData[];
  ticker: string;
  isScraping?: boolean;
}

export default function ArticleDrawer({
  isOpen,
  onClose,
  dataset,
  ticker,
  isScraping = false,
}: ArticleDrawerProps) {
  // Prevent body scrolling while drawer is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex justify-end">
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-black/70 backdrop-blur-sm transition-opacity animate-in fade-in duration-200"
      />

      {/* Drawer Panel */}
      <div className="relative z-10 flex h-full w-full max-w-2xl flex-col border-l border-slate-700/80 bg-slate-950/95 shadow-2xl backdrop-blur-xl animate-in slide-in-from-right duration-300">
        {/* Drawer Header */}
        <header className="flex items-center justify-between border-b border-slate-800 px-6 py-5 bg-slate-900/60">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500/15 ring-1 ring-emerald-500/30">
              <Layers className="h-5 w-5 text-emerald-400" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
                Ingested Sources & Telemetry
                {ticker && (
                  <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-emerald-400 border border-slate-700">
                    {ticker}
                  </span>
                )}
              </h2>
              <p className="text-xs text-slate-400">
                Processed news items with extracted quant triggers
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="rounded-full border border-slate-700 bg-slate-800/80 px-3 py-1 font-mono text-xs text-slate-300 font-medium">
              {dataset.length} {dataset.length === 1 ? 'article' : 'articles'}
            </span>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
              title="Close drawer (Esc)"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </header>

        {/* Drawer Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {isScraping && dataset.length === 0 ? (
            <div className="space-y-4 animate-in fade-in duration-300">
              {/* Scraping Banner */}
              <div className="flex items-center gap-3 rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 text-emerald-400">
                <Loader2 className="h-5 w-5 animate-spin shrink-0 text-emerald-400" />
                <div>
                  <p className="text-xs font-semibold text-emerald-300">
                    Fetching global market news... This may take up to 12 seconds.
                  </p>
                  <p className="text-[11px] text-emerald-400/70 mt-0.5">
                    Querying multi-tier RSS cascades with asset resolution for {ticker}
                  </p>
                </div>
              </div>

              {/* Pulsing Skeleton Cards */}
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-4 space-y-3 animate-pulse"
                >
                  <div className="flex justify-between items-center">
                    <div className="h-4 w-3/4 bg-slate-800 rounded"></div>
                    <div className="h-4 w-16 bg-slate-800 rounded-full"></div>
                  </div>
                  <div className="h-3 w-1/3 bg-slate-800/60 rounded"></div>
                  <div className="grid grid-cols-2 gap-2 pt-2">
                    <div className="h-16 bg-slate-800/40 rounded-lg"></div>
                    <div className="h-16 bg-slate-800/40 rounded-lg"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : dataset.length === 0 ? (
            <div className="flex h-64 flex-col items-center justify-center text-slate-500">
              <FileText className="mb-3 h-10 w-10 opacity-30 text-emerald-400" />
              <p className="text-sm font-medium text-slate-400">No articles ingested yet</p>
              <p className="text-xs text-slate-500 mt-1">Run analysis on a ticker to ingest news telemetry</p>
            </div>
          ) : (
            dataset.map((article, i) => (
              <ArticleCard
                key={`${article.headline}-${i}`}
                article={article}
                index={i}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}
