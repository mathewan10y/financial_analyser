import type { AnalysisResponse } from '../types';

const API_BASE = import.meta.env.VITE_API_URL ?? '';

export async function analyzeTicker(
  ticker: string,
  maxArticles = 3,
): Promise<AnalysisResponse> {
  const response = await fetch(`${API_BASE}/api/v1/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticker, max_articles: maxArticles }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(
      (error as { detail?: string }).detail ??
        `Analysis failed with status ${response.status}`,
    );
  }

  return response.json() as Promise<AnalysisResponse>;
}

export async function runPipelineWithProgress(
  ticker: string,
  onStepComplete: (stepIndex: number) => void,
  maxArticles = 3,
): Promise<AnalysisResponse> {
  const stepDurations = [1200, 1800, 2400, 1000];
  let completedSteps = 0;

  const progressPromise = (async () => {
    for (let i = 0; i < stepDurations.length - 1; i++) {
      await new Promise((r) => setTimeout(r, stepDurations[i]));
      completedSteps = i + 1;
      onStepComplete(i);
    }
  })();

  const apiPromise = analyzeTicker(ticker, maxArticles);

  const [result] = await Promise.all([apiPromise, progressPromise]);

  onStepComplete(stepDurations.length - 1);
  await new Promise((r) => setTimeout(r, stepDurations[stepDurations.length - 1]));

  return result;
}
