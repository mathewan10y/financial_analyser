import { useState } from 'react';
import {
  Database,
  Filter,
  Cpu,
  Landmark,
  TrendingUp,
  Brain,
  ShieldAlert,
  Gavel,
  CheckCircle2,
  Loader2,
  Circle,
} from 'lucide-react';

interface Persona {
  id: string;
  name: string;
  icon: React.ReactNode;
  description: string;
  phase: number;
}

const PERSONAS: Persona[] = [
  // Phase 1: Ingestion & Math
  {
    id: 'scraping',
    name: 'News Scraper',
    icon: <Database className="h-5 w-5" />,
    description: 'Scraping Financial News & Telemetry...',
    phase: 1,
  },
  {
    id: 'filtering',
    name: 'Noise Filter',
    icon: <Filter className="h-5 w-5" />,
    description: 'Deterministic News Noise Filtering...',
    phase: 1,
  },
  {
    id: 'gpu',
    name: 'GPU Engine',
    icon: <Cpu className="h-5 w-5" />,
    description: 'Local GPU Sentiment Extraction...',
    phase: 1,
  },
  // Phase 2: Agentic Debate
  {
    id: 'fundamental',
    name: 'Fundamental Desk',
    icon: <Landmark className="h-5 w-5" />,
    description: 'Analyzing P/E & Balance Sheet...',
    phase: 2,
  },
  {
    id: 'technical',
    name: 'Technical Desk',
    icon: <TrendingUp className="h-5 w-5" />,
    description: 'Evaluating Moving Averages...',
    phase: 2,
  },
  {
    id: 'sentiment',
    name: 'Sentiment Desk',
    icon: <Brain className="h-5 w-5" />,
    description: 'Processing Public Narrative...',
    phase: 2,
  },
  {
    id: 'cro',
    name: 'Chief Risk Officer',
    icon: <ShieldAlert className="h-5 w-5" />,
    description: 'Stress Testing Bull/Bear Cases...',
    phase: 2,
  },
  // Phase 3: Synthesis
  {
    id: 'orchestrator',
    name: 'Orchestrator',
    icon: <Gavel className="h-5 w-5" />,
    description: 'Drafting Final Capital Allocation Verdict...',
    phase: 3,
  },
];

interface MultiPersonaPipelineProps {
  isRunning: boolean;
  currentPhase: string | null;
  activeAgent?: string | null;
  agentOutputs?: Record<string, string>;
}

export type PersonaStatus = 'idle' | 'processing' | 'complete';

export default function MultiPersonaPipeline({ 
  isRunning, 
  currentPhase, 
  activeAgent,
  agentOutputs = {} 
}: MultiPersonaPipelineProps) {
  // Helper to extract persona output text if available
  const getPersonaOutput = (personaId: string): string | undefined => {
    if (personaId === 'cro') {
      return agentOutputs['risk'] ?? agentOutputs['cro'];
    }
    return agentOutputs[personaId];
  };

  // Compute individual statuses for each persona based on outputs, currentPhase and activeAgent
  const getPersonaStatus = (personaId: string): PersonaStatus => {
    // If output is already available for this persona, it is definitively complete
    if (getPersonaOutput(personaId)) {
      return 'complete';
    }

    if (!currentPhase) return 'idle';

    // Phase 1 Personas
    if (personaId === 'scraping') {
      if (currentPhase === 'ingestion') return 'processing';
      if (['filtering', 'processing_article', 'gpu_processing', 'sentence_processed', 'article_complete', 'article_skipped', 'debate_parallel', 'debate', 'debate_risk', 'debate_synthesis', 'complete'].includes(currentPhase)) {
        return 'complete';
      }
      return 'idle';
    }

    if (personaId === 'filtering') {
      if (currentPhase === 'filtering' || currentPhase === 'processing_article') return 'processing';
      if (['gpu_processing', 'sentence_processed', 'article_complete', 'article_skipped', 'debate_parallel', 'debate', 'debate_risk', 'debate_synthesis', 'complete'].includes(currentPhase)) {
        return 'complete';
      }
      return 'idle';
    }

    if (personaId === 'gpu') {
      if (['gpu_processing', 'sentence_processed', 'article_complete'].includes(currentPhase)) return 'processing';
      if (['debate_parallel', 'debate', 'debate_risk', 'debate_synthesis', 'complete'].includes(currentPhase)) {
        return 'complete';
      }
      return 'idle';
    }

    // Phase 2 Parallel Analysts (Fundamental, Technical, Sentiment)
    if (['fundamental', 'technical', 'sentiment'].includes(personaId)) {
      if (currentPhase === 'debate_parallel') {
        // All 3 analysts process concurrently in parallel until their individual outputs arrive
        return 'processing';
      }
      if (currentPhase === 'debate') {
        if (activeAgent === personaId) return 'processing';
        const order = ['fundamental', 'technical', 'sentiment'];
        const activeIdx = activeAgent ? order.indexOf(activeAgent) : -1;
        const myIdx = order.indexOf(personaId);
        if (activeIdx > myIdx || ['risk', 'orchestrator'].includes(activeAgent || '')) return 'complete';
        if (activeIdx === myIdx) return 'processing';
        return 'idle';
      }
      if (['debate_risk', 'debate_synthesis', 'complete'].includes(currentPhase)) {
        return 'complete';
      }
      return 'idle';
    }

    // Phase 2 CRO (Risk)
    if (personaId === 'cro') {
      if (currentPhase === 'debate_risk' || activeAgent === 'risk') return 'processing';
      if (['debate_synthesis', 'complete'].includes(currentPhase) || activeAgent === 'orchestrator') return 'complete';
      return 'idle';
    }

    // Phase 3 Orchestrator
    if (personaId === 'orchestrator') {
      if (currentPhase === 'debate_synthesis' || activeAgent === 'orchestrator') return 'processing';
      if (currentPhase === 'complete') return 'complete';
      return 'idle';
    }

    return 'idle';
  };

  // Map streaming phases to internal phase progress (1, 2, or 3)
  const getInternalPhase = () => {
    if (['ingestion', 'filtering', 'processing_article', 'gpu_processing', 'sentence_processed', 'article_complete'].includes(currentPhase || '')) return 1;
    if (['debate_parallel', 'debate', 'debate_risk'].includes(currentPhase || '')) return 2;
    if (['debate_synthesis', 'complete'].includes(currentPhase || '')) return 3;
    return 0;
  };

  const internalPhase = getInternalPhase();

  if (!isRunning) return null;

  return (
    <div className="flex h-full flex-col">
      <div className="mb-6 text-center">
        <div className="mb-3 flex items-center justify-center gap-3">
          <Loader2 className="h-6 w-6 animate-spin text-emerald-400" />
          <h2 className="text-lg font-bold text-slate-100">
            Multi-Agent Pipeline Active
          </h2>
        </div>
        <p className="text-xs text-slate-400">
          {currentPhase === 'debate_parallel' 
            ? 'Running Fundamental, Technical & Sentiment Desks in real-time...'
            : currentPhase === 'debate_risk'
            ? 'Chief Risk Officer stress-testing analytical transcript...'
            : currentPhase === 'debate_synthesis'
            ? 'Orchestrator synthesizing capital allocation verdict...'
            : 'Executing multi-agent debate for capital allocation decision'}
        </p>
      </div>

      {/* Phase 1: Ingestion & Math */}
      <div className="mb-6">
        <div className="mb-3 flex items-center gap-2">
          <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
            Phase 1
          </span>
          <h3 className="text-xs font-semibold text-slate-300">
            Ingestion & Math
          </h3>
        </div>
        <div className="grid grid-cols-1 gap-2">
          {PERSONAS.slice(0, 3).map((persona) => {
            const status = getPersonaStatus(persona.id);
            const outputText = getPersonaOutput(persona.id);
            return (
              <PersonaCard
                key={persona.id}
                persona={persona}
                status={status}
                outputText={outputText}
                compact
              />
            );
          })}
        </div>
      </div>

      {/* Phase 2: Agentic Debate */}
      <div className="mb-6">
        <div className="mb-3 flex items-center gap-2">
          <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-semibold text-amber-400">
            Phase 2
          </span>
          <h3 className="text-xs font-semibold text-slate-300">
            The Agentic Debate {currentPhase === 'debate_parallel' && <span className="text-amber-300 animate-pulse font-mono text-[10px]">(Streaming)</span>}
          </h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
          {PERSONAS.slice(3, 7).map((persona) => {
            const status = getPersonaStatus(persona.id);
            const outputText = getPersonaOutput(persona.id);
            return (
              <PersonaCard
                key={persona.id}
                persona={persona}
                status={status}
                outputText={outputText}
                compact
              />
            );
          })}
        </div>
      </div>

      {/* Phase 3: Synthesis */}
      <div className="mb-6">
        <div className="mb-3 flex items-center gap-2">
          <span className="rounded-full bg-red-500/20 px-2 py-0.5 text-[10px] font-semibold text-red-400">
            Phase 3
          </span>
          <h3 className="text-xs font-semibold text-slate-300">
            Synthesis
          </h3>
        </div>
        <PersonaCard
          persona={PERSONAS[7]}
          status={getPersonaStatus('orchestrator')}
          outputText={getPersonaOutput('orchestrator')}
          compact
        />
      </div>

      {/* Progress Bar */}
      <div className="mt-auto">
        <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
          <div
            className="h-full rounded-full bg-gradient-to-r from-emerald-600 via-amber-500 to-red-500 transition-all duration-1000"
            style={{
              width: `${Math.min((internalPhase / 3) * 100, 100)}%`,
            }}
          />
        </div>
        <div className="mt-2 flex justify-between text-[10px] text-slate-500">
          <span>Ingestion</span>
          <span>Parallel Debate</span>
          <span>Synthesis</span>
        </div>
      </div>
    </div>
  );
}

interface PersonaCardProps {
  persona: Persona;
  status: PersonaStatus;
  outputText?: string;
  fullWidth?: boolean;
  compact?: boolean;
}

function PersonaCard({ persona, status, outputText, fullWidth = false, compact = false }: PersonaCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const isProcessing = status === 'processing';
  const isComplete = status === 'complete';
  const isLong = outputText ? outputText.length > 120 : false;

  return (
    <div
      className={`relative overflow-hidden rounded-xl border transition-all duration-300 ${
        isProcessing
          ? 'border-emerald-500/60 bg-emerald-500/10 shadow-lg shadow-emerald-500/20 ring-1 ring-emerald-500/30'
          : isComplete
            ? 'border-emerald-600/40 bg-slate-900/90 shadow-sm'
            : 'border-slate-700/50 bg-slate-900/50'
      } ${fullWidth ? 'w-full max-w-md' : ''}`}
    >
      {isProcessing && (
        <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/10 via-amber-500/5 to-transparent animate-pulse pointer-events-none" />
      )}
      
      <div className={`relative flex flex-col ${compact ? 'p-3' : 'p-4'}`}>
        <div className="flex items-start gap-2.5">
          <div
            className={`flex shrink-0 items-center justify-center rounded-lg ${
              isProcessing
                ? 'bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/40'
                : isComplete
                  ? 'bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30'
                  : 'bg-slate-800/50 text-slate-500'
            } ${compact ? 'h-8 w-8' : 'h-10 w-10'}`}
          >
            {isComplete ? (
              <CheckCircle2 className={compact ? 'h-4 w-4' : 'h-5 w-5'} />
            ) : isProcessing ? (
              <Loader2 className={`${compact ? 'h-4 w-4' : 'h-5 w-5'} animate-spin`} />
            ) : (
              <Circle className={compact ? 'h-4 w-4' : 'h-5 w-5'} />
            )}
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span
                className={`font-semibold tracking-tight ${
                  isProcessing ? 'text-emerald-300' : isComplete ? 'text-slate-100' : 'text-slate-400'
                } ${compact ? 'text-xs' : 'text-sm'}`}
              >
                {persona.name}
              </span>
              {isProcessing && (
                <span className="flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
                </span>
              )}
            </div>
            <p
              className={`leading-relaxed ${
                isProcessing ? 'text-emerald-200/90' : isComplete ? 'text-slate-400' : 'text-slate-500'
              } ${compact ? 'text-[10px]' : 'text-xs'}`}
            >
              {persona.description}
            </p>
          </div>
        </div>

        {/* Live Output Section */}
        {outputText && (
          <div className="mt-2.5 rounded-lg border border-emerald-500/20 bg-slate-950/70 p-2.5 text-[11px] transition-all">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[9px] font-mono uppercase tracking-wider font-semibold text-emerald-400 flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                Live Desk Output
              </span>
              {isLong && (
                <button
                  type="button"
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="text-[10px] font-mono text-emerald-400 hover:text-emerald-300 underline decoration-dotted transition-colors"
                >
                  {isExpanded ? 'Collapse' : 'Expand'}
                </button>
              )}
            </div>
            <p
              className={`font-mono text-[10.5px] leading-relaxed text-slate-300 ${
                !isExpanded && isLong ? 'line-clamp-3' : ''
              }`}
            >
              {outputText}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
