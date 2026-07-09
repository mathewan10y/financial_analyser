import { useState, useRef, useEffect } from 'react';
import { Search, ChevronDown, X } from 'lucide-react';
import { POPULAR_TICKERS } from '../data/mockData';

interface SearchBarProps {
  activeTicker: string;
  onTickerSelect: (symbol: string) => void;
}

export default function SearchBar({ activeTicker, onTickerSelect }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const filtered = POPULAR_TICKERS.filter(
    (t) =>
      t.symbol.toLowerCase().includes(query.toLowerCase()) ||
      t.name.toLowerCase().includes(query.toLowerCase()),
  );

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  function handleSelect(symbol: string) {
    onTickerSelect(symbol);
    setQuery(symbol);
    setIsOpen(false);
  }

  function handleClear() {
    setQuery('');
    setIsOpen(true);
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-2xl">
      <div className="relative flex items-center">
        <Search className="absolute left-4 h-5 w-5 text-slate-500" />
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value.toUpperCase());
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          placeholder="Search ticker symbol (e.g. AAPL, NVDA)..."
          className="w-full rounded-xl border border-slate-700/80 bg-slate-900/80 py-3.5 pl-12 pr-12 font-mono text-sm text-slate-100 placeholder:text-slate-500 shadow-inner shadow-black/20 backdrop-blur-sm transition-all focus:border-emerald-500/50 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
        />
        {query && (
          <button
            onClick={handleClear}
            className="absolute right-10 rounded p-0.5 text-slate-500 hover:text-slate-300"
          >
            <X className="h-4 w-4" />
          </button>
        )}
        <ChevronDown
          className={`absolute right-4 h-4 w-4 text-slate-500 transition-transform ${isOpen ? 'rotate-180' : ''}`}
        />
      </div>

      {isOpen && filtered.length > 0 && (
        <ul className="absolute z-50 mt-2 w-full overflow-hidden rounded-xl border border-slate-700/80 bg-slate-900/95 shadow-2xl shadow-black/40 backdrop-blur-md">
          {filtered.map((ticker) => (
            <li key={ticker.symbol}>
              <button
                onClick={() => handleSelect(ticker.symbol)}
                className={`flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-slate-800/80 ${
                  activeTicker === ticker.symbol ? 'bg-emerald-500/10' : ''
                }`}
              >
                <span className="font-mono text-sm font-semibold text-emerald-400">
                  {ticker.symbol}
                </span>
                <span className="text-sm text-slate-400">{ticker.name}</span>
                {activeTicker === ticker.symbol && (
                  <span className="ml-auto rounded-full bg-emerald-500/20 px-2 py-0.5 text-xs text-emerald-400">
                    Active
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
