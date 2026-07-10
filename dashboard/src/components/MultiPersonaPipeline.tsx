import { useState, useEffect } from 'react';
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
    description: 'Cloud LLM Noise Filtering...',
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
}

export default function MultiPersonaPipeline({ isRunning }: MultiPersonaPipelineProps) {
  const [currentPhase, setCurrentPhase] = useState(0);
  const [activePersonaIndex, setActivePersonaIndex] = useState(-1);

  useEffect(() => {
   if (!isRunning) {
      setCurrentPhase(0);
      setActivePersonaIndex(-1);
      return;
    }

    // Phase 1: Ingestion (0-10s) - 3 personas
    const phase1Timings = [0, 3000, 6000]; // Start times for each persona
    const phase1Duration = 10000;

    // Phase 2: Agentic Debate (10-25s) - 4 personas
    const phase2Timings = [10000, 13000, 16000, 19000];
    const phase2Duration = 15000;

    // Phase 3: Synthesis (25s+) - 1 persona

    const timers: ReturnType<typeof setTimeout>[] = [];

    // Phase 1 activation
    setCurrentPhase(1);
    phase1Timings.forEach((time, index) => {
      const timer = setTimeout(() => {
        setActivePersonaIndex(index);
      }, time);
      timers.push(timer);
    });

    // Phase 2 activation
    const phase2Start = setTimeout(() => {
      setCurrentPhase(2);
    }, phase1Duration);
    timers.push(phase2Start);

    phase2Timings.forEach((time) => {
      const timer = setTimeout(() => {
        const personaIndex = PERSONAS.findIndex(p => p.id === PERSONAS[3 + phase2Timings.indexOf(time)].id);
        setActivePersonaIndex(personaIndex);
      }, time);
      timers.push(timer);
    });

    // Phase 3 activation
    const phase3Start = setTimeout(() => {
      setCurrentPhase(3);
      setActivePersonaIndex(7); // Orchestrator
    }, phase1Duration + phase2Duration);
    timers.push(phase3Start);

    return () => {
      timers.forEach(timer => clearTimeout(timer));
    };
  }, [isRunning]);

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
          Executing agentic debate for capital allocation decision
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
            <span className="text-[10px] text-slate-500">(0-10s)</span>
          </div>
          <div className="grid grid-cols-1 gap-2">
            {PERSONAS.slice(0, 3).map((persona, index) => (
              <PersonaCard
                key={persona.id}
                persona={persona}
                isActive={currentPhase === 1 && activePersonaIndex === index}
                isComplete={currentPhase > 1 || (currentPhase === 1 && activePersonaIndex > index)}
                compact
              />
            ))}
          </div>
        </div>

        {/* Phase 2: Agentic Debate */}
        <div className="mb-6">
          <div className="mb-3 flex items-center gap-2">
            <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-semibold text-amber-400">
              Phase 2
            </span>
            <h3 className="text-xs font-semibold text-slate-300">
              The Agentic Debate
            </h3>
            <span className="text-[10px] text-slate-500">(10-25s)</span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {PERSONAS.slice(3, 7).map((persona, index) => {
              const globalIndex = index + 3;
              return (
                <PersonaCard
                  key={persona.id}
                  persona={persona}
                  isActive={currentPhase === 2 && activePersonaIndex === globalIndex}
                  isComplete={currentPhase > 2 || (currentPhase === 2 && activePersonaIndex > globalIndex)}
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
            <span className="text-[10px] text-slate-500">(25s+)</span>
          </div>
          <PersonaCard
            persona={PERSONAS[7]}
            isActive={currentPhase === 3 && activePersonaIndex === 7}
            isComplete={false}
            compact
          />
        </div>

        {/* Progress Bar */}
        <div className="mt-auto">
          <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full rounded-full bg-gradient-to-r from-emerald-600 via-amber-500 to-red-500 transition-all duration-1000"
              style={{
                width: `${Math.min((currentPhase / 3) * 100, 100)}%`,
              }}
            />
          </div>
          <div className="mt-2 flex justify-between text-[10px] text-slate-500">
            <span>Ingestion</span>
            <span>Debate</span>
            <span>Synthesis</span>
          </div>
        </div>
      </div>
  );
}

interface PersonaCardProps {
  persona: Persona;
  isActive: boolean;
  isComplete: boolean;
  fullWidth?: boolean;
  compact?: boolean;
}

function PersonaCard({ persona, isActive, isComplete, fullWidth = false, compact = false }: PersonaCardProps) {
  return (
    <div
      className={`relative overflow-hidden rounded-lg border transition-all ${
        isActive
          ? 'border-emerald-500/50 bg-emerald-500/10 shadow-lg shadow-emerald-500/20'
          : isComplete
            ? 'border-slate-600/50 bg-slate-800/50'
            : 'border-slate-700/50 bg-slate-900/50'
      } ${fullWidth ? 'w-full max-w-md' : ''}`}
    >
      {isActive && (
        <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/5 to-transparent animate-pulse" />
      )}
      
      <div className={`relative flex items-start gap-2 ${compact ? 'p-3' : 'p-4'}`}>
        <div
          className={`flex shrink-0 items-center justify-center rounded-lg ${
            isActive
              ? 'bg-emerald-500/20 text-emerald-400'
              : isComplete
                ? 'bg-slate-700/50 text-slate-400'
                : 'bg-slate-800/50 text-slate-500'
          } ${compact ? 'h-8 w-8' : 'h-10 w-10'}`}
        >
          {isComplete ? (
            <CheckCircle2 className={compact ? 'h-4 w-4' : 'h-5 w-5'} />
          ) : isActive ? (
            <Loader2 className={compact ? 'h-4 w-4' : 'h-5 w-5'} animate-spin />
          ) : (
            <Circle className={compact ? 'h-4 w-4' : 'h-5 w-5'} />
          )}
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span
              className={`font-semibold ${
                isActive ? 'text-emerald-300' : isComplete ? 'text-slate-300' : 'text-slate-400'
              } ${compact ? 'text-xs' : 'text-sm'}`}
            >
              {persona.name}
            </span>
            {isActive && (
              <span className="flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
              </span>
            )}
          </div>
          <p
            className={`leading-relaxed ${
              isActive ? 'text-emerald-200/80' : isComplete ? 'text-slate-400' : 'text-slate-500'
            } ${compact ? 'text-[10px]' : 'text-xs'}`}
          >
            {persona.description}
          </p>
        </div>
      </div>
    </div>
  );
}
