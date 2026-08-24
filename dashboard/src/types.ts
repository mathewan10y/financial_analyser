export interface CriticalEvent {
  score: number;
  text_context: string;
}

export interface ArticleData {
  date: string;
  headline: string;
  link: string;
  full_text?: string;
  weighted_average?: number;
  critical_downside_event?: CriticalEvent;
  critical_upside_event?: CriticalEvent;
}

export interface FinalVerdict {
  internal_reasoning_process: string;
  decision: 'BUY' | 'HOLD' | 'SELL';
  confidence_score: number;
  executive_summary: string;
}

export interface AnalysisResponse {
  status: string;
  ticker: string;
  payload_length: number;
  dataset: ArticleData[];
  final_verdict: FinalVerdict;
}

export type PipelineStep = {
  id: number;
  label: string;
  duration: number;
};
