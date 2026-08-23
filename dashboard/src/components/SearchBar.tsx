import { useState, useRef, useEffect, useCallback } from 'react';
import { Search, ChevronDown, X, Loader2 } from 'lucide-react';

interface TickerResult {
  symbol: string;
  name: string;
}

interface SearchBarProps {
  activeTicker: string;
  onTickerSelect: (symbol: string) => void;
}

const FALLBACK_TICKERS: TickerResult[] = [
  { symbol: 'AAPL', name: 'Apple Inc.' },
  { symbol: 'NVDA', name: 'NVIDIA Corporation' },
  { symbol: 'MSFT', name: 'Microsoft Corporation' },
  { symbol: 'TSLA', name: 'Tesla, Inc.' },
  { symbol: 'GOOGL', name: 'Alphabet Inc.' },
  { symbol: 'AMZN', name: 'Amazon.com, Inc.' },
];

export default function SearchBar({ activeTicker, onTickerSelect }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [results, setResults] = useState<TickerResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const searchTickers = useCallback(async (searchQuery: string) => {
    if (searchQuery.length < 1) {
      setResults([]);
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(
        `https://corsproxy.io/?https://query2.finance.yahoo.com/v1/finance/search?q=${encodeURIComponent(searchQuery)}`
      );
      const data = await response.json();
      
      const quotes = (data.quotes || []).slice(0, 8).map((quote: any) => ({
        symbol: quote.symbol,
        name: quote.longname || quote.shortname || quote.symbol,
      }));
      
      setResults(quotes);
    } catch (error) {
      console.error('Search failed, using fallback:', error);
      // Fallback to hardcoded list filtered by query
      const filtered = FALLBACK_TICKERS.filter(
        (t) =>
          t.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
          t.name.toLowerCase().includes(searchQuery.toLowerCase()),
      );
      setResults(filtered);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      searchTickers(query);
    }, 300);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [query, searchTickers]);

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
    setResults([]);
    // Close dropdown immediately
  }

  function handleClear() {
    setQuery('');
    setIsOpen(true);
    setResults([]);
  }

  return (
    <div ref={containerRef} className="relative z-50 w-full max-w-2xl">
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
        {isLoading ? (
          <Loader2 className="absolute right-10 h-4 w-4 animate-spin text-emerald-500" />
        ) : query ? (
          <button
            onClick={handleClear}
            className="absolute right-10 rounded p-0.5 text-slate-500 hover:text-slate-300"
          >
            <X className="h-4 w-4" />
          </button>
        ) : null}
        <ChevronDown
          className={`absolute right-4 h-4 w-4 text-slate-500 transition-transform ${isOpen ? 'rotate-180' : ''}`}
        />
      </div>

      {isOpen && (results.length > 0 || isLoading) && (
        <ul className="absolute top-full left-0 right-0 mt-2 z-[100] bg-slate-800 border border-slate-700 shadow-2xl overflow-hidden rounded-md">
          {isLoading && results.length === 0 ? (
            <li className="flex items-center justify-center px-4 py-8">
              <Loader2 className="mr-2 h-4 w-4 animate-spin text-emerald-500" />
              <span className="text-sm text-slate-400">Searching...</span>
            </li>
          ) : (
            results.map((ticker) => (
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
            ))
          )}
          {!isLoading && results.length === 0 && query.length >= 1 && (
            <li className="px-4 py-3 text-sm text-slate-500">
              No results found for "{query}"
            </li>
          )}
        </ul>
      )}
    </div>
  );
}
