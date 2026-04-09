import React, { useState, useEffect } from 'react';
import { CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '../ui/command';
import { TrendingUp, Search } from 'lucide-react';
import { useApi } from '../../hooks/useApi';

export default function SearchCommand({ open, onOpenChange, onSelect }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const { searchSymbols } = useApi();

  useEffect(() => {
    if (!query || query.length < 1) {
      setResults([]);
      return;
    }
    const timeout = setTimeout(async () => {
      try {
        const data = await searchSymbols(query);
        setResults(data.symbols || []);
      } catch (e) {
        console.error(e);
      }
    }, 300);
    return () => clearTimeout(timeout);
  }, [query, searchSymbols]);

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput
        placeholder="Search stocks, commodities... (e.g., RELIANCE, Gold)"
        value={query}
        onValueChange={setQuery}
        data-testid="symbol-search-input"
      />
      <CommandList>
        <CommandEmpty>No results found. Try a different symbol.</CommandEmpty>
        <CommandGroup heading="Symbols">
          {results.map((sym) => (
            <CommandItem
              key={sym.symbol}
              value={sym.symbol}
              onSelect={() => onSelect(sym.symbol)}
              className="flex items-center gap-3 cursor-pointer"
            >
              <TrendingUp className="w-4 h-4 text-[hsl(var(--primary))]" />
              <div>
                <span className="font-mono text-sm font-medium">{sym.symbol.replace('.NS', '').replace('=F', '')}</span>
                <span className="ml-2 text-xs text-[hsl(var(--muted-foreground))]">{sym.name}</span>
              </div>
              <span className="ml-auto text-xs text-[hsl(var(--muted-foreground))]">{sym.sector}</span>
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
