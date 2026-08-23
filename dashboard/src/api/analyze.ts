import type { AnalysisResponse } from '../types';

const API_BASE = import.meta.env.VITE_API_URL ?? '';

export interface StreamUpdate {
  phase: string;
  message?: string;
  agent?: string;
  text?: string;
  article_index?: number;
  sentence_index?: number;
  sentence?: string;
  score?: number;
  total_sentences?: number;
  payload?: AnalysisResponse;
  [key: string]: any;
}

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

export async function analyzeTicker(
  ticker: string,
  maxArticles = 3,
  onUpdate: (update: StreamUpdate) => void,
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

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  
  if (!reader) {
    throw new Error('Response body is not readable');
  }

  let finalPayload: AnalysisResponse | null = null;
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      // Keep the incomplete chunk in buffer
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
          const update: StreamUpdate = JSON.parse(trimmed);
          onUpdate(update);

          if (update.phase === 'complete' && update.payload) {
            const sanitizedPayload = sanitizePayload(update.payload);
            finalPayload = sanitizedPayload;
          }
        } catch (parseError) {
          console.error('Failed to parse stream line:', trimmed, parseError);
        }
      }
    }

    // Process any remaining tail in buffer
    if (buffer.trim()) {
      try {
        const update: StreamUpdate = JSON.parse(buffer.trim());
        onUpdate(update);
        if (update.phase === 'complete' && update.payload) {
          const sanitizedPayload = sanitizePayload(update.payload);
          finalPayload = sanitizedPayload;
        }
      } catch (parseError) {
        console.error('Failed to parse remaining stream buffer:', buffer, parseError);
      }
    }
  } finally {
    reader.releaseLock();
  }

  if (!finalPayload) {
    throw new Error('Stream completed without final payload');
  }

  return finalPayload;
}

function sanitizePayload(payload: AnalysisResponse): AnalysisResponse {
  // Sanitize the final_verdict if it exists
  if (payload.final_verdict) {
    try {
      const verdictString = JSON.stringify(payload.final_verdict);
      const sanitized = sanitizeJsonString(verdictString);
      payload.final_verdict = JSON.parse(sanitized);
    } catch (error) {
      console.error('Failed to sanitize final_verdict, using fallback:', error);
      payload.final_verdict = {
        decision: 'HOLD',
        confidence_score: 0,
        executive_summary: 'Unable to parse verdict response due to formatting errors.',
        internal_reasoning_process: '',
      };
    }
  }
  return payload;
}

export async function runPipelineWithProgress(
  ticker: string,
  onUpdate: (update: StreamUpdate) => void,
  maxArticles = 3,
): Promise<AnalysisResponse> {
  return analyzeTicker(ticker, maxArticles, onUpdate);
}
