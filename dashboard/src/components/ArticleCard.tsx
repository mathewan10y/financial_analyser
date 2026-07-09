import { ExternalLink, TrendingDown, TrendingUp } from 'lucide-react';
import type { ArticleData } from '../types';
import {
  formatDate,
  getSentimentColors,
  getSentimentLabel,
} from '../utils/sentiment';

interface ArticleCardProps {
  article: ArticleData;
  index: number;
}

export default function ArticleCard({ article, index }: ArticleCardProps) {
  const colors = getSentimentColors(article.weighted_average);
  const label = getSentimentLabel(article.weighted_average);

  return (
    <article
      className="group rounded-xl border border-slate-700/60 bg-slate-900/50 p-4 transition-all hover:border-slate-600/80 hover:bg-slate-900/70"
      style={{ animationDelay: `${index * 80}ms` }}
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="line-clamp-2 text-sm font-semibold leading-snug text-slate-100">
            {article.headline}
          </h3>
          <time className="mt-1 block font-mono text-xs text-slate-500">
            {formatDate(article.date)}
          </time>
        </div>
        <span
          className={`shrink-0 rounded-full border px-2.5 py-1 font-mono text-xs font-medium ${colors.badge}`}
        >
          {label} ({article.weighted_average > 0 ? '+' : ''}
          {article.weighted_average.toFixed(3)})
        </span>
      </div>

      <a
        href={article.link}
        target="_blank"
        rel="noopener noreferrer"
        className="mb-4 inline-flex items-center gap-1.5 text-xs text-emerald-500/80 transition-colors hover:text-emerald-400"
      >
        <ExternalLink className="h-3 w-3" />
        View Source
      </a>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <div className="rounded-lg border border-red-500/30 bg-red-950/20 p-3">
          <div className="mb-1.5 flex items-center gap-1.5">
            <TrendingDown className="h-3.5 w-3.5 text-red-400" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-red-400">
              Downside Trigger
            </span>
          </div>
          <p className="line-clamp-3 text-xs leading-relaxed text-slate-400">
            {article.critical_downside_event.text_context}
          </p>
          <span className="mt-1.5 block font-mono text-[10px] text-red-400/70">
            Score: {article.critical_downside_event.score.toFixed(3)}
          </span>
        </div>

        <div className="rounded-lg border border-emerald-500/30 bg-emerald-950/20 p-3">
          <div className="mb-1.5 flex items-center gap-1.5">
            <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-400">
              Upside Trigger
            </span>
          </div>
          <p className="line-clamp-3 text-xs leading-relaxed text-slate-400">
            {article.critical_upside_event.text_context}
          </p>
          <span className="mt-1.5 block font-mono text-[10px] text-emerald-400/70">
            Score: {article.critical_upside_event.score.toFixed(3)}
          </span>
        </div>
      </div>
    </article>
  );
}
