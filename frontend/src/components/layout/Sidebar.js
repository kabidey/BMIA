import React, { useState, useEffect } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { BarChart3, Search, TrendingUp, LayoutGrid, ChevronLeft, ChevronRight, Zap, Trophy, Menu, X } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';
import SearchCommand from './SearchCommand';

const navItems = [
  { to: '/', icon: LayoutGrid, label: 'Market Overview', shortcut: '1' },
  { to: '/analyze', icon: TrendingUp, label: 'Symbol Analysis', shortcut: '2' },
  { to: '/signals', icon: Zap, label: 'AI Signals', shortcut: '3' },
  { to: '/scanner', icon: BarChart3, label: 'Batch Scanner', shortcut: '4' },
  { to: '/track-record', icon: Trophy, label: 'Track Record', shortcut: '5' },
];

export default function Sidebar() {
  const [expanded, setExpanded] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  // Detect screen size
  useEffect(() => {
    const lgMq = window.matchMedia('(min-width: 1024px)');
    const mobileMq = window.matchMedia('(max-width: 639px)');

    const handleResize = () => {
      setIsMobile(mobileMq.matches);
      setExpanded(lgMq.matches);
      if (mobileMq.matches) setMobileOpen(false);
    };

    handleResize();
    lgMq.addEventListener('change', handleResize);
    mobileMq.addEventListener('change', handleResize);
    return () => {
      lgMq.removeEventListener('change', handleResize);
      mobileMq.removeEventListener('change', handleResize);
    };
  }, []);

  // Close mobile sidebar on navigation
  useEffect(() => {
    if (isMobile) setMobileOpen(false);
  }, [location.pathname, isMobile]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const sidebarContent = (
    <>
      <div className="flex items-center h-14 px-4 border-b border-[hsl(var(--border))]">
        <div className="w-8 h-8 rounded-lg bg-[hsl(var(--primary))] flex items-center justify-center flex-shrink-0">
          <Zap className="w-5 h-5 text-[hsl(var(--primary-foreground))]" />
        </div>
        {(expanded || mobileOpen) && (
          <span className="ml-3 font-display font-semibold text-sm tracking-wide text-[hsl(var(--foreground))]">
            Bharat Market Intel
          </span>
        )}
        {isMobile && mobileOpen && (
          <button onClick={() => setMobileOpen(false)} className="ml-auto text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]" data-testid="sidebar-close-btn">
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      <div className="px-3 py-3">
        <button
          data-testid="command-palette-open-button"
          onClick={() => setSearchOpen(true)}
          className="flex items-center gap-2 w-full rounded-lg px-3 py-2 text-sm text-[hsl(var(--muted-foreground))] bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] border border-[hsl(var(--border))]"
          style={{ transition: 'background-color 0.15s ease' }}
        >
          <Search className="w-4 h-4 flex-shrink-0" />
          {(expanded || mobileOpen) && (
            <>
              <span className="flex-1 text-left">Search...</span>
              <kbd className="text-xs bg-[hsl(var(--surface-3))] px-1.5 py-0.5 rounded hidden sm:inline">Ctrl+K</kbd>
            </>
          )}
        </button>
      </div>

      <nav className="flex-1 px-3 py-2 space-y-1">
        {navItems.map((item) => (
          <Tooltip key={item.to}>
            <TooltipTrigger asChild>
              <NavLink
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium ${
                    isActive
                      ? 'bg-[hsl(var(--accent))] text-[hsl(var(--primary))]'
                      : 'text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--foreground))]'
                  }`
                }
                style={{ transition: 'background-color 0.15s ease, color 0.15s ease' }}
              >
                <item.icon className="w-5 h-5 flex-shrink-0" />
                {(expanded || mobileOpen) && <span>{item.label}</span>}
              </NavLink>
            </TooltipTrigger>
            {!expanded && !mobileOpen && (
              <TooltipContent side="right">{item.label}</TooltipContent>
            )}
          </Tooltip>
        ))}
      </nav>

      {!isMobile && (
        <div className="px-3 py-3 border-t border-[hsl(var(--border))]">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))]"
            style={{ transition: 'background-color 0.15s ease' }}
            data-testid="sidebar-toggle-btn"
          >
            {expanded ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            {expanded && <span>Collapse</span>}
          </button>
        </div>
      )}

      {(expanded || mobileOpen) && (
        <div className="px-4 py-3 border-t border-[hsl(var(--border))]">
          <p className="text-[10px] text-[hsl(var(--muted-foreground))] leading-tight" data-testid="sebi-disclaimer-sidebar">
            Not investment advice. For educational purposes only. Consult a SEBI-registered advisor.
          </p>
        </div>
      )}
    </>
  );

  return (
    <TooltipProvider delayDuration={0}>
      {/* Mobile hamburger button */}
      {isMobile && !mobileOpen && (
        <button
          onClick={() => setMobileOpen(true)}
          className="fixed top-3 left-3 z-[60] w-10 h-10 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] flex items-center justify-center text-[hsl(var(--foreground))]"
          data-testid="sidebar-hamburger-btn"
        >
          <Menu className="w-5 h-5" />
        </button>
      )}

      {/* Mobile overlay */}
      {isMobile && mobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-[55]"
          onClick={() => setMobileOpen(false)}
          data-testid="sidebar-overlay"
        />
      )}

      {/* Sidebar */}
      <aside
        data-testid="sidebar"
        className={`
          fixed left-0 top-0 h-screen bg-[hsl(var(--surface-1))] border-r border-[hsl(var(--border))] flex flex-col z-[56]
          ${isMobile
            ? `w-64 ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`
            : expanded ? 'w-56' : 'w-16'
          }
        `}
        style={{ transition: isMobile ? 'transform 0.25s ease-out' : 'width 0.2s ease-out' }}
      >
        {sidebarContent}
      </aside>

      <SearchCommand open={searchOpen} onOpenChange={setSearchOpen} onSelect={(sym) => {
        setSearchOpen(false);
        navigate(`/analyze/${encodeURIComponent(sym)}`);
      }} />
    </TooltipProvider>
  );
}
