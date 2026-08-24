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
import TypewriterText from './TypewriterText';

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
  // Phase 2: Parallel Agentic Debate Desks
  {
    id: 'fundamental',
    name: 'Fundamental Desk',
    icon: <Landmark className="h-5 w-5" />,
    description: 'Analyzing P/E, Debt & Balance Sheet Health...',
    phase: 2,
  },
  {
    id: 'technical',
    name: 'Technical Desk',
    icon: <TrendingUp className="h-5 w-5" />,
    description: 'Evaluating 50/200 Day Moving Averages...',
    phase: 2,
  },
  {
    id: 'sentiment',
    name: 'Sentiment Desk',
    icon: <Brain className="h-5 w-5" />,
    description: 'Decoding Narrative & Quant Tailwinds...',
    phase: 2,
  },
  // Phase 3: Risk Assessment Desk
  {
    id: 'cro',
    name: 'Chief Risk Officer (CRO)',
    icon: <ShieldAlert className="h-5 w-5" />,
    description: 'Stress-Testing Contradictions & Downside Tail Risks...',
    phase: 3,
  },
  // Phase 4: Synthesis Desk
  {
    id: 'orchestrator',
    name: 'Orchestrator Desk',
    icon: <Gavel className="h-5 w-5" />,
    description: 'Resolving Conflicts & Final Capital Allocation Verdict...',
    phase: 4,
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
    // If output is already available for this persona, it is complete
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

    // Phase 3 CRO (Risk)
    if (personaId === 'cro') {
      if (currentPhase === 'debate_risk' || activeAgent === 'risk') return 'processing';
      if (['debate_synthesis', 'complete'].includes(currentPhase) || activeAgent === 'orchestrator') return 'complete';
      return 'idle';
    }

    // Phase 4 Orchestrator
    if (personaId === 'orchestrator') {
      if (currentPhase === 'debate_synthesis' || activeAgent === 'orchestrator') return 'processing';
      if (currentPhase === 'complete') return 'complete';
      return 'idle';
    }

    return 'idle';
  };

  // Map streaming phases to progress percentage (0 - 100)
  const getProgressPercentage = () => {
    if (!currentPhase) return 0;
    if (currentPhase === 'ingestion') return 15;
    if (currentPhase === 'filtering' || currentPhase === 'processing_article') return 30;
    if (currentPhase === 'gpu_processing' || currentPhase === 'sentence_processed' || currentPhase === 'article_complete') return 45;
    if (currentPhase === 'debate_parallel') return 70;
    if (currentPhase === 'debate_risk') return 85;
    if (currentPhase === 'debate_synthesis') return 95;
    if (currentPhase === 'complete') return 100;
    return 50;
  };

  return (
    <div className="flex flex-col space-y-6">
      {/* Active Pipeline Banner (only when running) */}
      {isRunning && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-3.5 backdrop-blur-sm flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Loader2 className="h-5 w-5 animate-spin text-emerald-400" />
            <div>
              <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                Multi-Agent Pipeline Active
                <span className="inline-flex items-center rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-mono font-semibold text-emerald-400">
                  LIVE STREAM
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                {currentPhase === 'debate_parallel' 
                  ? 'Dispatching Fundamental, Technical & Sentiment Desks in parallel...'
                  : currentPhase === 'debate_risk'
                  ? 'Chief Risk Officer stress-testing analytical transcript...'
                  : currentPhase === 'debate_synthesis'
                  ? 'Orchestrator synthesizing capital allocation verdict...'
                  : 'Executing multi-agent quantitative underwriting sequence...'}
              </p>
            </div>
          </div>

          <div className="hidden sm:block text-right font-mono text-xs text-emerald-400 font-semibold">
            {getProgressPercentage()}%
          </div>
        </div>
      )}

      {/* Phase 1: Ingestion & Math Layer */}
      <div>
        <div className="mb-3 flex items-center gap-2">
          <span className="rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-400">
            Phase 1
          </span>
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Ingestion & Telemetry Math Layer
          </h3>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {PERSONAS.slice(0, 3).map((persona) => {
            const status = getPersonaStatus(persona.id);
            const outputText = getPersonaOutput(persona.id);
            return (
              <PersonaCard
                key={persona.id}
                persona={persona}
                status={status}
                outputText={outputText}
                theme="emerald"
                compact
              />
            );
          })}
        </div>
      </div>

      {/* Phase 2: Parallel Agentic Debate Desks (3-Column Horizontal Row) */}
      <div>
        <div className="mb-3 flex items-center gap-2">
          <span className="rounded-full bg-amber-500/20 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-400">
            Phase 2
          </span>
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            Parallel Agentic Debate Desks
            {currentPhase === 'debate_parallel' && (
              <span className="text-amber-400 animate-pulse font-mono text-[10px] normal-case tracking-normal">
                (Concurrent Execution)
              </span>
            )}
          </h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {PERSONAS.slice(3, 6).map((persona) => {
            const status = getPersonaStatus(persona.id);
            const outputText = getPersonaOutput(persona.id);
            return (
              <PersonaCard
                key={persona.id}
                persona={persona}
                status={status}
                outputText={outputText}
                theme="emerald"
              />
            );
          })}
        </div>
      </div>

      {/* Phase 3: Risk Assessment Desk (Full Width CRO Card - Crimson Accents) */}
      <div>
        <div className="mb-3 flex items-center gap-2">
          <span className="rounded-full bg-rose-500/20 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-rose-400">
            Phase 3
          </span>
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Capital Preservation & Risk Assessment
          </h3>
        </div>
        <PersonaCard
          persona={PERSONAS[6]}
          status={getPersonaStatus('cro')}
          outputText={getPersonaOutput('cro')}
          theme="rose"
        />
      </div>

      {/* Phase 4: Synthesis & Capital Allocation Desk (Full Width Orchestrator Card - Violet Accents) */}
      <div>
        <div className="mb-3 flex items-center gap-2">
          <span className="rounded-full bg-purple-500/20 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-purple-400">
            Phase 4
          </span>
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Orchestration & Decision Synthesis
          </h3>
        </div>
        <PersonaCard
          persona={PERSONAS[7]}
          status={getPersonaStatus('orchestrator')}
          outputText={getPersonaOutput('orchestrator')}
          theme="purple"
        />
      </div>

      {/* Progress Bar */}
      {isRunning && (
        <div className="mt-4 pt-2">
          <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full rounded-full bg-gradient-to-r from-emerald-500 via-amber-500 to-purple-500 transition-all duration-700"
              style={{
                width: `${getProgressPercentage()}%`,
              }}
            />
          </div>
          <div className="mt-2 flex justify-between text-[10px] font-mono text-slate-500">
            <span>Ingestion</span>
            <span>Parallel Desks</span>
            <span>Risk Stress-Test</span>
            <span>Orchestration</span>
          </div>
        </div>
      )}
    </div>
  );
}

interface PersonaCardProps {
  persona: Persona;
  status: PersonaStatus;
  outputText?: string;
  theme?: 'emerald' | 'rose' | 'purple' | 'slate';
  fullWidth?: boolean;
  compact?: boolean;
}

function PersonaCard({ 
  persona, 
  status, 
  outputText, 
  theme = 'emerald',
  fullWidth = false, 
  compact = false 
}: PersonaCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const isProcessing = status === 'processing';
  const isComplete = status === 'complete';
  const isLong = outputText ? outputText.length > 130 : false;

  // Theme configuration for borders, badges, and glows
  const themeStyles = {
    emerald: {
      activeBorder: 'border-emerald-500/70 bg-emerald-950/20 ring-1 ring-emerald-500/40 shadow-emerald-500/20',
      completeBorder: 'border-emerald-600/40 bg-slate-900/90 shadow-sm',
      activeIcon: 'bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/40',
      completeIcon: 'bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30',
      activeTitle: 'text-emerald-300',
      tag: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
      pulseDot: 'bg-emerald-400',
      outputBorder: 'border-emerald-500/20 bg-slate-950/70',
      headerTag: 'text-emerald-400',
    },
    rose: {
      activeBorder: 'border-rose-500/70 bg-rose-950/25 ring-1 ring-rose-500/40 shadow-rose-500/20',
      completeBorder: 'border-rose-600/40 bg-slate-900/90 shadow-sm',
      activeIcon: 'bg-rose-500/20 text-rose-400 ring-1 ring-rose-500/40',
      completeIcon: 'bg-rose-500/15 text-rose-400 ring-1 ring-rose-500/30',
      activeTitle: 'text-rose-300',
      tag: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
      pulseDot: 'bg-rose-400',
      outputBorder: 'border-rose-500/20 bg-slate-950/70',
      headerTag: 'text-rose-400',
    },
    purple: {
      activeBorder: 'border-purple-500/70 bg-purple-950/25 ring-1 ring-purple-500/40 shadow-purple-500/20',
      completeBorder: 'border-purple-600/40 bg-slate-900/90 shadow-sm',
      activeIcon: 'bg-purple-500/20 text-purple-400 ring-1 ring-purple-500/40',
      completeIcon: 'bg-purple-500/15 text-purple-400 ring-1 ring-purple-500/30',
      activeTitle: 'text-purple-300',
      tag: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
      pulseDot: 'bg-purple-400',
      outputBorder: 'border-purple-500/20 bg-slate-950/70',
      headerTag: 'text-purple-400',
    },
    slate: {
      activeBorder: 'border-slate-500/60 bg-slate-800/40 ring-1 ring-slate-500/30',
      completeBorder: 'border-slate-700/60 bg-slate-900/80',
      activeIcon: 'bg-slate-700/50 text-slate-300',
      completeIcon: 'bg-slate-800/50 text-slate-400',
      activeTitle: 'text-slate-200',
      tag: 'bg-slate-800 text-slate-400 border-slate-700',
      pulseDot: 'bg-slate-400',
      outputBorder: 'border-slate-700/40 bg-slate-950/70',
      headerTag: 'text-slate-400',
    },
  }[theme];

  return (
    <div
      className={`relative overflow-hidden rounded-xl border transition-all duration-300 shadow-md ${
        isProcessing
          ? `${themeStyles.activeBorder} shadow-lg`
          : isComplete
            ? themeStyles.completeBorder
            : 'border-slate-800 bg-slate-900/60'
      } ${fullWidth ? 'w-full' : ''}`}
    >
      {isProcessing && (
        <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/5 via-amber-500/5 to-transparent animate-pulse pointer-events-none" />
      )}
      
      <div className={`relative flex flex-col ${compact ? 'p-3' : 'p-4'}`}>
        <div className="flex items-start gap-3">
          <div
            className={`flex shrink-0 items-center justify-center rounded-xl transition-all ${
              isProcessing
                ? themeStyles.activeIcon
                : isComplete
                  ? themeStyles.completeIcon
                  : 'bg-slate-800/60 text-slate-500'
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
                  isProcessing ? themeStyles.activeTitle : isComplete ? 'text-slate-100' : 'text-slate-400'
                } ${compact ? 'text-xs' : 'text-sm'}`}
              >
                {persona.name}
              </span>
              {isProcessing && (
                <span className="flex h-2 w-2">
                  <span className={`absolute inline-flex h-full w-full animate-ping rounded-full ${themeStyles.pulseDot} opacity-75`} />
                  <span className={`relative inline-flex h-2 w-2 rounded-full ${themeStyles.pulseDot}`} />
                </span>
              )}
            </div>
            <p
              className={`leading-relaxed ${
                isProcessing ? 'text-slate-300' : isComplete ? 'text-slate-400' : 'text-slate-500'
              } ${compact ? 'text-[10px]' : 'text-xs'}`}
            >
              {persona.description}
            </p>
          </div>
        </div>

        {/* Live Monospace Typewriter Output Section */}
        {outputText && (
          <div className={`mt-3 rounded-lg border ${themeStyles.outputBorder} p-3 text-[11px] transition-all`}>
            <div className="flex items-center justify-between mb-1.5 border-b border-slate-800/80 pb-1">
              <span className={`text-[9px] font-mono uppercase tracking-wider font-bold ${themeStyles.headerTag} flex items-center gap-1.5`}>
                <span className="h-1.5 w-1.5 rounded-full bg-current" />
                Live Desk Finding
              </span>
              {isLong && (
                <button
                  type="button"
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="text-[10px] font-mono text-slate-400 hover:text-slate-200 underline decoration-dotted transition-colors"
                >
                  {isExpanded ? 'Collapse' : 'Expand'}
                </button>
              )}
            </div>
            <div
              className={`font-mono text-[10.5px] leading-relaxed text-slate-200 ${
                !isExpanded && isLong ? 'line-clamp-3' : ''
              }`}
            >
              <TypewriterText text={outputText} speed={8} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

