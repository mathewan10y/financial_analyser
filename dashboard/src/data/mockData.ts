import type { AnalysisResponse } from '../types';

export const MOCK_DATA: AnalysisResponse = {
  status: 'success',
  ticker: 'AAPL',
  payload_length: 3,
  dataset: [
    {
      date: '2026-06-17T13:13:32Z',
      headline:
        'Apple (AAPL) Stock After 129% Five-Year Rally Is There Still Value Here',
      link: '#',
      weighted_average: 0.117,
      critical_downside_event: {
        score: 0.117,
        text_context:
          'Apple (AAPL) Stock After 129% Five-Year Rally Is There Still Value Here Yahoo Finance',
      },
      critical_upside_event: {
        score: 0.117,
        text_context:
          'Apple (AAPL) Stock After 129% Five-Year Rally Is There Still Value Here - Yahoo Finance.',
      },
    },
  ],
  final_verdict: {
    internal_reasoning_process:
      '1. Synthesize Fundamental Strengths... 2. Incorporate Technical Momentum... 3. Assess Sentiment Nuance... 4. Prioritize CRO Risk Warning...',
    decision: 'SELL',
    confidence_score: 95,
    executive_summary:
      'Despite robust underlying fundamentals and positive technical momentum, the egregious premium valuation of AAPL presents an unacceptable risk to capital preservation.',
  },
};

export const POPULAR_TICKERS = [
  { symbol: 'AAPL', name: 'Apple Inc.' },
  { symbol: 'TSLA', name: 'Tesla, Inc.' },
  { symbol: 'NVDA', name: 'NVIDIA Corporation' },
  { symbol: 'MSFT', name: 'Microsoft Corporation' },
  { symbol: 'AMZN', name: 'Amazon.com, Inc.' },
  { symbol: 'GOOGL', name: 'Alphabet Inc.' },
];

export const PIPELINE_STEPS = [
  { id: 1, label: 'Step 1: Scraping Google News...', duration: 1200 },
  { id: 2, label: 'Step 2: Running Sentiment Models...', duration: 1800 },
  { id: 3, label: 'Step 3: Initiating 5-Agent Debate...', duration: 2400 },
  { id: 4, label: 'Step 4: Compiling Final Verdict...', duration: 1000 },
];
