import { useState } from 'react';
import { ChevronDown, Brain } from 'lucide-react';
import { parseReasoningSteps } from '../utils/sentiment';

interface ReasoningAccordionProps {
  reasoning: string;
}

export default function ReasoningAccordion({ reasoning }: ReasoningAccordionProps) {
  const [isOpen, setIsOpen] = useState(false);
  const steps = parseReasoningSteps(reasoning);

  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-900/40">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between px-4 py-3.5 text-left transition-colors hover:bg-slate-800/40"
      >
        <div className="flex items-center gap-2.5">
          <Brain className="h-4 w-4 text-slate-400" />
          <span className="text-sm font-medium text-slate-300">
            View Agent Chain-of-Thought History
          </span>
        </div>
        <ChevronDown
          className={`h-4 w-4 text-slate-500 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      <div
        className={`overflow-hidden transition-all duration-300 ${
          isOpen ? 'max-h-[600px] opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="space-y-3 border-t border-slate-700/60 px-4 py-4">
          {steps.map((step, i) => (
            <div
              key={i}
              className="rounded-lg border border-slate-700/40 bg-slate-800/30 p-3"
            >
              <p className="text-xs leading-relaxed text-slate-400">{step}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
