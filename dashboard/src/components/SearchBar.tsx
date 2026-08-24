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

const GLOBAL_FALLBACK_TICKERS: TickerResult[] = [
  { symbol: 'NVDA', name: 'NVIDIA Corporation' },
  { symbol: 'AAPL', name: 'Apple Inc.' },
  { symbol: 'MSFT', name: 'Microsoft Corporation' },
  { symbol: 'TSLA', name: 'Tesla, Inc.' },
  { symbol: 'GOOGL', name: 'Alphabet Inc.' },
  { symbol: 'AMZN', name: 'Amazon.com, Inc.' },
  { symbol: 'META', name: 'Meta Platforms, Inc.' },
  { symbol: 'AMD', name: 'Advanced Micro Devices, Inc.' },
  { symbol: 'PLTR', name: 'Palantir Technologies Inc.' },
  { symbol: 'TCS.NS', name: 'Tata Consultancy Services Ltd.' },
  { symbol: 'RELIANCE.NS', name: 'Reliance Industries Ltd.' },
  { symbol: 'INFY.NS', name: 'Infosys Ltd.' },
  { symbol: 'HDFCBANK.NS', name: 'HDFC Bank Ltd.' },
  { symbol: 'TATAMOTORS.NS', name: 'Tata Motors Ltd.' },
  { symbol: 'GC=F', name: 'Gold Futures' },
  { symbol: 'SI=F', name: 'Silver Futures' },
  { symbol: 'CL=F', name: 'Crude Oil Futures' },
  { symbol: 'BTC-USD', name: 'Bitcoin USD' },
  { symbol: 'ETH-USD', name: 'Ethereum USD' },
  { symbol: 'SOL-USD', name: 'Solana USD' },
  { symbol: 'EURUSD=X', name: 'EUR / USD Currency Pair' },
  { symbol: 'USDINR=X', name: 'USD / INR Currency Pair' },
  { symbol: '^GSPC', name: 'S&P 500 Index' },
  { symbol: '^NSEI', name: 'NIFTY 50 Index' },
];

export default function SearchBar({ activeTicker, onTickerSelect }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [results, setResults] = useState<TickerResult[]>(GLOBAL_FALLBACK_TICKERS.slice(0, 8));
  const [isLoading, setIsLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const searchTickers = useCallback(async (searchQuery: string) => {
    const q = searchQuery.trim();
    if (!q) {
      setResults(GLOBAL_FALLBACK_TICKERS.slice(0, 8));
      return;
    }

    // Immediate local match first for 0ms responsiveness
    const localMatches = GLOBAL_FALLBACK_TICKERS.filter(
      (t) =>
        t.symbol.toLowerCase().includes(q.toLowerCase()) ||
        t.name.toLowerCase().includes(q.toLowerCase())
    );
    if (localMatches.length > 0) {
      setResults(localMatches);
    }

    setIsLoading(true);
    try {
      // Query local backend proxy endpoint
      const response = await fetch(`/api/v1/search?q=${encodeURIComponent(q)}`);
      if (response.ok) {
        const data = await response.json();
        const quotes = (data.quotes || []).map((quote: any) => ({
          symbol: quote.symbol,
          name: quote.name || quote.longname || quote.shortname || quote.symbol,
        }));
        if (quotes.length > 0) {
          setResults(quotes);
        }
      } else {
        throw new Error(`Search API returned status ${response.status}`);
      }
    } catch (error) {
      console.warn('Backend search query failed, using local asset universe:', error);
      const filtered = GLOBAL_FALLBACK_TICKERS.filter(
        (t) =>
          t.symbol.toLowerCase().includes(q.toLowerCase()) ||
          t.name.toLowerCase().includes(q.toLowerCase())
      );
      if (filtered.length > 0) {
        setResults(filtered);
      } else {
        setResults([{ symbol: q.toUpperCase(), name: `Custom Symbol (${q.toUpperCase()})` }]);
      }
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
    }, 150);

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
  }

  function handleClear() {
    setQuery('');
    setIsOpen(true);
    setResults(GLOBAL_FALLBACK_TICKERS.slice(0, 8));
  }

  return (
    <div ref={containerRef} className="relative z-50 w-full">
      <div className="relative flex items-center">
        <Search className="absolute left-4 h-5 w-5 text-slate-500" />
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value.toUpperCase());
            setIsOpen(true);
          }}
          onFocus={() => {
            setIsOpen(true);
            if (!query) {
              setResults(GLOBAL_FALLBACK_TICKERS.slice(0, 8));
            }
          }}
          placeholder="Search ticker symbol (e.g. NVDA, TCS.NS, BTC-USD, GC=F)..."
          className="w-full rounded-xl border border-slate-700/80 bg-slate-900/90 py-3.5 pl-12 pr-12 font-mono text-sm text-slate-100 placeholder:text-slate-500 shadow-inner shadow-black/30 backdrop-blur-md transition-all focus:border-emerald-500/60 focus:outline-none focus:ring-2 focus:ring-emerald-500/25"
        />
        {isLoading ? (
          <Loader2 className="absolute right-10 h-4 w-4 animate-spin text-emerald-500" />
        ) : query ? (
          <button
            onClick={handleClear}
            className="absolute right-10 rounded p-0.5 text-slate-500 hover:text-slate-300 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        ) : null}
        <ChevronDown
          className={`absolute right-4 h-4 w-4 text-slate-500 transition-transform ${isOpen ? 'rotate-180' : ''}`}
        />
      </div>

      {isOpen && (results.length > 0 || isLoading) && (
        <ul className="absolute top-full left-0 right-0 mt-2 z-[9999] bg-slate-900/95 border border-slate-700/90 shadow-2xl overflow-hidden rounded-xl backdrop-blur-xl divide-y divide-slate-800/80 max-h-80 overflow-y-auto">
          {isLoading && results.length === 0 ? (
            <li className="flex items-center justify-center px-4 py-8">
              <Loader2 className="mr-2 h-4 w-4 animate-spin text-emerald-500" />
              <span className="text-sm text-slate-400">Searching global financial tickers...</span>
            </li>
          ) : (
            results.map((ticker) => (
              <li key={ticker.symbol}>
                <button
                  type="button"
                  onClick={() => handleSelect(ticker.symbol)}
                  className={`flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-slate-800/90 ${
                    activeTicker === ticker.symbol ? 'bg-emerald-500/15' : ''
                  }`}
                >
                  <span className="font-mono text-sm font-bold text-emerald-400">
                    {ticker.symbol}
                  </span>
                  <span className="text-xs text-slate-300 truncate max-w-xs">{ticker.name}</span>
                  {activeTicker === ticker.symbol && (
                    <span className="ml-auto rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-semibold text-emerald-400 ring-1 ring-emerald-500/30">
                      Selected
                    </span>
                  )}
                </button>
              </li>
            ))
          )}
          {!isLoading && results.length === 0 && query.length >= 1 && (
            <li className="px-4 py-4 text-center text-xs text-slate-500">
              No matching assets found for "{query}"
            </li>
          )}
        </ul>
      )}
    </div>
  );
}
