{
  "design_system_name": "Market Intelligence Cockpit (India) — Terminal Dark",
  "brand_attributes": [
    "institutional",
    "diagnostic",
    "fast-scanning",
    "data-dense-not-cluttered",
    "trustworthy",
    "terminal-craft (Bloomberg-inspired)"
  ],
  "north_star": {
    "one_sentence": "A single-screen market diagnostic cockpit that surfaces liquidity flow, sentiment, and rotation signals in <10 seconds.",
    "success_actions": [
      "Trader identifies risk-on/off regime (VIX + breadth + flows)",
      "Trader spots sector rotation (treemap + relative strength)",
      "Trader confirms derivatives positioning (PCR + OI quadrant)",
      "Trader catches actionable events (block/bulk + earnings highlights)"
    ]
  },
  "layout_strategy": {
    "page_type": "single dashboard",
    "reading_flow": "left-to-right scan within each module; top-to-bottom across 4 stacked sections",
    "density_rules": [
      "Prefer 2-row KPI matrices over tall cards.",
      "Use mono font for numbers; keep labels short; show units.",
      "Use separators + subtle borders instead of heavy shadows.",
      "Avoid large hero areas; reserve motion for streaming deltas only."
    ],
    "grid": {
      "container": "max-w-[1920px] mx-auto px-3 sm:px-4 lg:px-6",
      "section_spacing": "space-y-4 lg:space-y-5",
      "module_grid": "grid grid-cols-1 lg:grid-cols-12 gap-3 lg:gap-4",
      "recommended_breakpoints": {
        "mobile": "single column; collapsible subpanels",
        "md": "2 columns for charts + tables",
        "lg": "12-col cockpit; keep key diagnostics above the fold",
        "xl_2k": "increase table visible rows; keep font sizes stable"
      }
    },
    "section_stack": [
      {
        "id": "macro-view",
        "title": "Macro View",
        "layout": "12-col: Indices Matrix (8) + Flows/VIX/Breadth (4)",
        "notes": "Indices matrix is the primary scan surface; right rail is regime diagnostics."
      },
      {
        "id": "micro-view",
        "title": "Micro View",
        "layout": "12-col: Sector Treemap (7) + Volume Shockers/Breakouts (5) + 52W clusters below",
        "notes": "Treemap must be interactive with hover-card details; lists are sortable."
      },
      {
        "id": "derivatives-sentiment",
        "title": "Derivatives & Sentiment",
        "layout": "12-col: PCR gauges (4) + OI Buildup Quadrant (8)",
        "notes": "Quadrant is the decision tool; PCR is quick context."
      },
      {
        "id": "corporate-actions-news",
        "title": "Corporate Actions & News",
        "layout": "12-col: Block/Bulk feed (7) + Earnings/Actions highlights (5)",
        "notes": "Use compact feed rows with time, symbol, value, and tag chips."
      }
    ]
  },
  "typography": {
    "font_pairing": {
      "display": "Space Grotesk",
      "body": "Inter",
      "data": "Azeret Mono (already in repo) — use as JetBrains Mono substitute for now"
    },
    "tailwind_usage": {
      "display_class": "font-display",
      "mono_class": "font-mono tabular-nums"
    },
    "scale": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl font-display tracking-tight",
      "h2": "text-base md:text-lg font-display text-foreground/90",
      "kpi_value": "text-xl sm:text-2xl font-mono",
      "kpi_label": "text-xs uppercase tracking-widest text-muted-foreground",
      "table": "text-xs sm:text-sm",
      "micro": "text-[11px] leading-4"
    },
    "number_formatting": {
      "rules": [
        "Always tabular numbers for price/percent/volume.",
        "Use compact units: Cr, L, K; show ₹ where relevant.",
        "Show sign + color for deltas; keep neutral gray for 0."
      ]
    }
  },
  "color_system": {
    "mode": "dark-first",
    "tokens_css": {
      "note": "These extend existing /src/index.css tokens; keep current teal primary and terminal surfaces.",
      "additions": {
        "--surface-4": "222 14% 20%",
        "--ink": "210 20% 98%",
        "--ink-dim": "215 16% 70%",
        "--teal": "186 92% 42%",
        "--teal-dim": "186 60% 18%",
        "--up": "142 70% 45%",
        "--down": "0 72% 52%",
        "--amber": "38 92% 55%",
        "--info": "199 89% 55%",
        "--focus": "186 92% 42%",
        "--gridline": "222 14% 18%",
        "--shadow-soft": "0 0% 0% / 0.35"
      }
    },
    "semantic_usage": {
      "positive": "use --up for price up, breadth positive, long buildup",
      "negative": "use --down for price down, breadth negative, short buildup",
      "warning": "use --amber for stretched/overheated, high VIX zones",
      "info": "use --info for neutral informational markers",
      "accent": "use teal for selection, active tabs, focus rings, key outlines"
    },
    "gradients": {
      "allowed": [
        "Very subtle section header wash only (<=20% viewport): linear-gradient(90deg, hsla(186,92%,42%,0.10), transparent 55%)",
        "Decorative corner glow behind top bar: radial-gradient(circle at 20% 0%, hsla(186,92%,42%,0.12), transparent 55%)"
      ],
      "prohibited": [
        "Any saturated purple/pink combos",
        "Gradients on tables/cards with dense text",
        "Gradients on small UI elements (<100px)"
      ]
    },
    "data_viz_palette": {
      "categorical": [
        "hsl(var(--chart-1))",
        "hsl(var(--chart-2))",
        "hsl(var(--chart-4))",
        "hsl(var(--chart-5))",
        "hsl(var(--info))"
      ],
      "heatmap": {
        "down": "#ef4444",
        "neutral": "#334155",
        "up": "#22c55e",
        "rule": "Use a 3-stop diverging scale; clamp extremes; never use neon saturation across the whole treemap."
      }
    }
  },
  "components": {
    "component_path": {
      "shadcn_primary": "/app/frontend/src/components/ui/",
      "use": [
        "card.jsx",
        "tabs.jsx",
        "table.jsx",
        "badge.jsx",
        "button.jsx",
        "separator.jsx",
        "scroll-area.jsx",
        "tooltip.jsx",
        "hover-card.jsx",
        "skeleton.jsx",
        "resizable.jsx",
        "collapsible.jsx",
        "dropdown-menu.jsx",
        "sonner.jsx"
      ]
    },
    "module_shell": {
      "pattern": "TerminalPanel",
      "description": "A consistent module wrapper: header (title + last-updated + actions) + content + footer legend.",
      "tailwind": "rounded-xl border border-border bg-card/70 backdrop-blur-[2px]",
      "header": {
        "tailwind": "flex items-center justify-between gap-3 px-3 py-2 border-b border-border",
        "title": "text-sm font-display tracking-wide",
        "meta": "text-[11px] text-muted-foreground font-mono"
      }
    },
    "indices_matrix": {
      "use": ["Card", "Table", "Badge", "Tooltip"],
      "row_design": {
        "left": "index name + mini sparkline (Recharts LineChart)",
        "right": "LTP, %Chg, Chg, 1D range bar (Progress), breadth mini",
        "density": "Use 44–48px row height on desktop; 52px on touch."
      },
      "streaming_effect": {
        "rule": "On update, flash background for 450ms then decay.",
        "classes": {
          "up": "bg-[hsla(142,70%,45%,0.10)]",
          "down": "bg-[hsla(0,72%,52%,0.10)]",
          "neutral": "bg-[hsla(215,16%,70%,0.06)]"
        }
      }
    },
    "flows_chart": {
      "library": "Recharts",
      "chart": "stacked/paired bars for FII vs DII",
      "styling": {
        "grid": "stroke: hsl(var(--border)); strokeDasharray: '3 3'",
        "bars": "FII teal, DII slate; negative values use down red"
      }
    },
    "vix_gauge": {
      "implementation": "Recharts RadialBarChart + custom needle overlay (SVG) OR PieChart with needle",
      "zones": [
        {"label": "Calm", "range": "0-12", "color": "hsl(var(--success))"},
        {"label": "Watch", "range": "12-18", "color": "hsl(var(--chart-4))"},
        {"label": "Risk", "range": "18-30", "color": "hsl(var(--danger))"}
      ],
      "microcopy": "India VIX (Regime)"
    },
    "advance_decline": {
      "component": "Progress + numeric ratio",
      "rule": "Show Adv, Dec, Unch counts; ratio chip with color."
    },
    "sector_treemap": {
      "library": "Recharts Treemap",
      "interaction": [
        "HoverCard shows sector, avg %chg, leaders/laggards, volume impulse",
        "Click filters right-side lists (shockers/breakouts)"
      ],
      "labeling": "Only show labels for tiles > 6% area; others on hover.",
      "legend": "Compact diverging legend with 5 ticks (-3, -1, 0, +1, +3)."
    },
    "volume_shockers_breakouts": {
      "component": "Table inside ScrollArea",
      "columns": ["Symbol", "Vol xAvg", "%Chg", "Price", "Trigger"],
      "badges": {
        "3x": "Badge variant secondary",
        "5x": "Badge variant default with teal outline"
      }
    },
    "clusters_52w": {
      "component": "Tabs (Highs / Lows) + Table",
      "rule": "Use chips for distance-to-high/low buckets (0-1%, 1-3%, 3-5%)."
    },
    "pcr": {
      "component": "2 compact gauges (Nifty, BankNifty)",
      "thresholds": [
        {"label": "Put-heavy", "value": "> 1.2", "color": "hsl(var(--success))"},
        {"label": "Neutral", "value": "0.9–1.2", "color": "hsl(var(--chart-5))"},
        {"label": "Call-heavy", "value": "< 0.9", "color": "hsl(var(--danger))"}
      ]
    },
    "oi_quadrant": {
      "implementation": "Recharts ScatterChart with 2 reference lines (x=0, y=0) to form quadrants",
      "quadrants": [
        {"name": "Long Buildup", "x": "+Price", "y": "+OI", "color": "hsl(var(--success))"},
        {"name": "Short Covering", "x": "+Price", "y": "-OI", "color": "hsl(var(--info))"},
        {"name": "Short Buildup", "x": "-Price", "y": "+OI", "color": "hsl(var(--danger))"},
        {"name": "Long Unwinding", "x": "-Price", "y": "-OI", "color": "hsl(var(--chart-4))"}
      ],
      "interaction": [
        "Hover tooltip shows symbol, price%, OI%, volume, IV",
        "Brush/zoom optional on desktop",
        "Click adds to watchlist toast (sonner)"
      ]
    },
    "feeds": {
      "block_bulk": {
        "component": "ScrollArea + compact rows",
        "row": "time | symbol | side | qty | value | tag",
        "tags": "Badge for Block/Bulk; side colored dot"
      },
      "earnings_actions": {
        "component": "Accordion or Collapsible",
        "rule": "Group by Today / This Week; show EPS surprise, dividend, split, board meet."
      }
    }
  },
  "motion_microinteractions": {
    "principles": [
      "Motion communicates change, not decoration.",
      "Keep durations short: 120–220ms for hover; 300–450ms for streaming flash.",
      "Avoid layout shift; animate opacity/background-color only (no transform on dense tables)."
    ],
    "streaming_updates": {
      "pattern": "cell flash + delta tick",
      "implementation_hint": "Store previous value; if changed, apply class for 450ms; show ▲/▼ glyph via lucide-react icons.",
      "do_not": ["Do not animate entire card", "Do not use transition: all"]
    },
    "hover": {
      "cards": "border-color shift + subtle inner glow",
      "rows": "bg-muted/30 on hover",
      "charts": "crosshair cursor + tooltip fade"
    },
    "scroll": {
      "rule": "Use ScrollArea for tables; keep header sticky (CSS position: sticky)."
    }
  },
  "accessibility": {
    "contrast": [
      "All text must meet WCAG AA; use muted-foreground only for secondary labels.",
      "Never rely on color alone: add ▲/▼ icons and +/- signs."
    ],
    "focus": "Use visible focus ring: ring-2 ring-[hsl(var(--ring))] ring-offset-2 ring-offset-background",
    "reduced_motion": "Respect prefers-reduced-motion: disable streaming flash and use subtle outline instead.",
    "keyboard": "All tabs, dropdowns, tables with row actions must be keyboard reachable."
  },
  "testing_attributes": {
    "rule": "All interactive and key informational elements MUST include data-testid (kebab-case).",
    "examples": [
      "data-testid=\"macro-indices-matrix\"",
      "data-testid=\"indices-row-nifty-50\"",
      "data-testid=\"flows-fii-dii-chart\"",
      "data-testid=\"vix-gauge\"",
      "data-testid=\"sector-treemap\"",
      "data-testid=\"volume-shockers-table\"",
      "data-testid=\"oi-quadrant-chart\"",
      "data-testid=\"block-bulk-feed\"",
      "data-testid=\"refresh-interval-select\"",
      "data-testid=\"auto-refresh-toggle\""
    ]
  },
  "image_urls": {
    "background_textures": [
      {
        "category": "subtle module backdrop (optional)",
        "description": "Use as very low-opacity background image in top bar only (<=10% opacity).",
        "url": "https://images.unsplash.com/photo-1563942833988-0803533bd016?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA3MDB8MHwxfHNlYXJjaHwxfHxhYnN0cmFjdCUyMGRhcmslMjBncmlkJTIwdGV4dHVyZXxlbnwwfHx8Ymx1ZXwxNzc1NzM1MTU5fDA&ixlib=rb-4.1.0&q=85"
      },
      {
        "category": "grain/texture alternative",
        "description": "If you need a subtle texture behind the header; keep opacity <= 0.06.",
        "url": "https://images.unsplash.com/photo-1598270106705-020a72bae1bf?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA3MDB8MHwxfHNlYXJjaHwzfHxhYnN0cmFjdCUyMGRhcmslMjBncmlkJTIwdGV4dHVyZXxlbnwwfHx8Ymx1ZXwxNzc1NzM1MTU5fDA&ixlib=rb-4.1.0&q=85"
      }
    ]
  },
  "libraries": {
    "required": [
      {
        "name": "framer-motion",
        "why": "Entrance animations for modules + subtle number change transitions without layout shift.",
        "install": "npm i framer-motion",
        "usage": "Use motion.div for module fade-in; avoid transforms on dense tables; prefer opacity."
      }
    ],
    "already_available": [
      {
        "name": "recharts",
        "why": "All charts: flows bars, treemap, scatter quadrant, radial gauges, sparklines."
      }
    ]
  },
  "instructions_to_main_agent": [
    "Keep existing dark theme tokens in /src/index.css; only add missing tokens if needed (surface-4 etc).",
    "Build a reusable TerminalPanel wrapper component (JS) to standardize headers, borders, and spacing.",
    "Implement streaming update flash by comparing previous vs next values; apply class for 450ms; respect prefers-reduced-motion.",
    "No top gainers/losers module anywhere; replace with diagnostics (breadth, flows, rotation, OI quadrant).",
    "Optimize for 1920px+: use 12-col grid, sticky section headers, and ScrollArea for tables.",
    "Every button, tab trigger, dropdown, toggle, row action, and key metric must include data-testid.",
    "Use shadcn components from /components/ui only for dropdowns, tabs, tables, tooltips, etc."
  ],
  "references": {
    "inspiration": [
      {
        "name": "Fortress Dashboard (Bloomberg-inspired) mention",
        "url": "https://adminlte.io/blog/fintech-banking-dashboard-templates/"
      },
      {
        "name": "Dribbble trading dashboard tag",
        "url": "https://dribbble.com/tags/trading-dashboard"
      },
      {
        "name": "Dribbble treemap tag",
        "url": "https://dribbble.com/tags/treemap"
      }
    ]
  },
  "general_ui_ux_design_guidelines_appendix": "<General UI UX Design Guidelines>\n    - You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms\n    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text\n   - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json\n\n **GRADIENT RESTRICTION RULE**\nNEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc\nNEVER use dark gradients for logo, testimonial, footer etc\nNEVER let gradients cover more than 20% of the viewport.\nNEVER apply gradients to text-heavy content or reading areas.\nNEVER use gradients on small UI elements (<100px width).\nNEVER stack multiple gradient layers in the same viewport.\n\n**ENFORCEMENT RULE:**\n    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors\n\n**How and where to use:**\n   • Section backgrounds (not content backgrounds)\n   • Hero section header content. Eg: dark to light to dark color\n   • Decorative overlays and accent elements only\n   • Hero section with 2-3 mild color\n   • Gradients creation can be done for any angle say horizontal, vertical or diagonal\n\n- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**\n\n</Font Guidelines>\n\n- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. \n   \n- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.\n\n- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.\n   \n- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly\n    Eg: - if it implies playful/energetic, choose a colorful scheme\n           - if it implies monochrome/minimal, choose a black–white/neutral scheme\n\n**Component Reuse:**\n\t- Prioritize using pre-existing components from src/components/ui when applicable\n\t- Create new components that match the style and conventions of existing components when needed\n\t- Examine existing components to understand the project's component patterns before creating new ones\n\n**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component\n\n**Best Practices:**\n\t- Use Shadcn/UI as the primary component library for consistency and accessibility\n\t- Import path: ./components/[component-name]\n\n**Export Conventions:**\n\t- Components MUST use named exports (export const ComponentName = ...)\n\t- Pages MUST use default exports (export default function PageName() {...})\n\n**Toasts:**\n  - Use `sonner` for toasts\"\n  - Sonner component are located in `/app/src/components/ui/sonner.tsx`\n\nUse 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals.\n</General UI UX Design Guidelines>"
}
