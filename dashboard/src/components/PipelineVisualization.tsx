import { Layers, FileText } from 'lucide-react';
import type { ArticleData } from '../types';
import ArticleCard from './ArticleCard';

interface PipelineVisualizationProps {
  dataset: ArticleData[];
  ticker: string;
}

export default function PipelineVisualization({
  dataset,
  ticker,
}: PipelineVisualizationProps) {
  return (
    <section className="flex h-full flex-col rounded-2xl border border-slate-700/60 bg-terminal-panel/80 backdrop-blur-sm">
      <header className="flex items-center justify-between border-b border-slate-700/60 px-5 py-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10">
            <Layers className="h-4 w-4 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-100">
              Pipeline Architecture
            </h2>
            <p className="text-xs text-slate-500">
              Sentiment extraction flow — {ticker}
            </p>
          </div>
        </div>
        <span className="rounded-full border border-slate-700 bg-slate-800/80 px-3 py-1 font-mono text-xs text-slate-400">
          {dataset.length} articles
        </span>
      </header>

      <div className="panel-grid flex-1 space-y-3 overflow-y-auto p-4">
        {dataset.length === 0 ? (
          <div className="flex h-48 flex-col items-center justify-center text-slate-500">
            <FileText className="mb-2 h-8 w-8 opacity-40" />
            <p className="text-sm">No articles processed yet</p>
          </div>
        ) : (
          dataset.map((article, i) => (
            <ArticleCard key={`${article.headline}-${i}`} article={article} index={i} />
          ))
        )}
      </div>
    </section>
  );
}
