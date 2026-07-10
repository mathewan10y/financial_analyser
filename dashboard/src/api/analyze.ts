import type { AnalysisResponse } from '../types';

const API_BASE = import.meta.env.VITE_API_URL ?? '';

function sanitizeJsonString(jsonString: string): string {
  let sanitized = jsonString;
  
  // Remove markdown code block markers (various formats)
  sanitized = sanitized.replace(/```json\s*/gi, '');
  sanitized = sanitized.replace(/```\s*$/g, '');
  sanitized = sanitized.replace(/```\s*json\s*$/gi, '');
  
  // Remove trailing comments (single line)
  sanitized = sanitized.replace(/\/\/.*$/gm, '');
  
  // Remove trailing comments (multi-line /* */)
  sanitized = sanitized.replace(/\/\*[\s\S]*?\*\//g, '');
  
  // Remove any trailing commas before closing braces/brackets
  sanitized = sanitized.replace(/,\s*([}\]])/g, '$1');
  
  // Remove control characters that might break JSON
  sanitized = sanitized.replace(/[\x00-\x1F\x7F]/g, '');
  
  // Trim whitespace
  sanitized = sanitized.trim();
  
  return sanitized;
}

function safeJsonParse<T>(jsonString: string, fallback: T): T {
  try {
    const sanitized = sanitizeJsonString(jsonString);
    return JSON.parse(sanitized) as T;
  } catch (error) {
    console.error('JSON parse error, using fallback:', error);
    console.error('Failed to parse:', jsonString.substring(0, 200));
    return fallback;
  }
}

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

  const rawText = await response.text();
  console.log('Raw response length:', rawText.length);
  
  try {
    // Try to parse the full response first
    const parsed = safeJsonParse<AnalysisResponse>(rawText, null as any);
    if (parsed && parsed.final_verdict) {
      console.log('Successfully parsed full response');
      return parsed;
    }
  } catch (error) {
    console.error('Full JSON parse failed, attempting partial sanitization:', error);
  }
  
  // If full parse fails, try to extract and sanitize the final_verdict field
  try {
    const fallbackResponse: AnalysisResponse = {
      status: 'error',
      ticker,
      dataset: [],
      payload_length: 0,
      final_verdict: {
        decision: 'HOLD',
        confidence_score: 0,
        executive_summary: 'Unable to parse verdict response due to formatting errors.',
        internal_reasoning_process: '',
      },
    };
    
    // Try to extract the final_verdict object with better regex for nested objects
    const verdictMatch = rawText.match(/"final_verdict"\s*:\s*(\{[^}]*\{[^}]*\}[^}]*\}|\{[^}]*\})/s);
    if (verdictMatch) {
      console.log('Found verdict match, attempting to parse');
      const verdictJson = safeJsonParse(verdictMatch[1], fallbackResponse.final_verdict);
      if (verdictJson.decision && verdictJson.confidence_score !== undefined) {
        fallbackResponse.final_verdict = verdictJson;
        console.log('Successfully parsed verdict:', verdictJson.decision, verdictJson.confidence_score);
      }
    }
    
    return fallbackResponse;
  } catch (error) {
    console.error('All parsing attempts failed:', error);
    throw new Error('Failed to parse API response');
  }
}

export async function runPipelineWithProgress(
  ticker: string,
  onStepComplete: (stepIndex: number) => void,
  maxArticles = 3,
): Promise<AnalysisResponse> {
  const stepDurations = [1200, 1800, 2400, 1000];

  // Start the API call immediately
  const apiPromise = analyzeTicker(ticker, maxArticles);

  // Run progress animation independently
  const progressPromise = (async () => {
    for (let i = 0; i < stepDurations.length; i++) {
      await new Promise((r) => setTimeout(r, stepDurations[i]));
      onStepComplete(i);
    }
  })();

  // Return API result immediately when ready, don't wait for animation
  const result = await apiPromise;
  
  // Let progress animation continue in background
  progressPromise.catch(console.error);

  return result;
}
