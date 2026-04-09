{
  "brand": {
    "name": "Bharat Market Intel Agent (BMIA)",
    "design_personality": [
      "Bloomberg-terminal density, modern web polish",
      "trustworthy + analytical (quant lab)",
      "dark-first for low eye strain",
      "high signal-to-noise: data-rich, never cluttered",
      "India-market aware (NSE/BSE/MCX), SEBI-compliant tone"
    ],
    "north_star": "Make a retail investor feel like a Tier-1 quant: fast scanning, deep drill-down, and clear risk framing."
  },

  "inspiration_refs": {
    "dribbble_searches": [
      {
        "title": "Trading dashboard search",
        "url": "https://dribbble.com/search/trading-dashboard",
        "takeaways": [
          "Modular card grid with dense KPIs + charts",
          "Left rail navigation + top command/search bar",
          "High-contrast dark surfaces with subtle borders",
          "Heatmap blocks + sortable tables as primary scanning tools"
        ]
      },
      {
        "title": "Bloomberg terminal search",
        "url": "https://dribbble.com/search/bloomberg-terminal",
        "takeaways": [
          "Terminal-like typography for tickers + numbers",
          "Multi-panel layouts with resizable sections",
          "Color used as semantic signal (up/down/alert), not decoration"
        ]
      }
    ],
    "behance": [
      {
        "title": "Stock Trading Dashboard UI/UX Design",
        "url": "https://www.behance.net/gallery/236819273/Stock-Trading-Dashboard-UIUX-Design",
        "takeaways": [
          "Clear hierarchy: top KPIs → main chart → supporting panels",
          "Tables with badges + micro sparklines",
          "Side panels for news/insights"
        ]
      }
    ]
  },

  "typography": {
    "font_pairing": {
      "display": {
        "name": "Space Grotesk",
        "usage": "Page titles, section headers, Alpha Score headline",
        "google_fonts": "https://fonts.google.com/specimen/Space+Grotesk"
      },
      "body": {
        "name": "Inter",
        "usage": "Body text, labels, UI copy",
        "google_fonts": "https://fonts.google.com/specimen/Inter"
      },
      "mono": {
        "name": "Azeret Mono",
        "usage": "Tickers, prices, OHLC, timestamps, table numeric columns",
        "google_fonts": "https://fonts.google.com/specimen/Azeret+Mono"
      }
    },
    "text_size_hierarchy": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl",
      "h2": "text-base md:text-lg",
      "body": "text-sm md:text-base",
      "small": "text-xs md:text-sm"
    },
    "numeric_rules": [
      "All prices/percentages use tabular numbers: add Tailwind `tabular-nums`",
      "Tickers use mono font + slightly increased tracking: `font-mono tracking-wide`",
      "Avoid ALL CAPS paragraphs; only tickers/badges may be uppercase"
    ]
  },

  "color_system": {
    "mode": "dark-first",
    "notes": [
      "No purple (AI/chat restriction).",
      "Use teal/cyan as primary accent; amber as secondary; red/green strictly semantic for down/up.",
      "Gradients only as subtle section background accents (<20% viewport)."
    ],
    "tokens_css": {
      "where": "/app/frontend/src/index.css (override :root and .dark tokens)",
      "css_variables": {
        "--background": "222 18% 6%",
        "--foreground": "210 20% 98%",
        "--card": "222 18% 8%",
        "--card-foreground": "210 20% 98%",
        "--popover": "222 18% 8%",
        "--popover-foreground": "210 20% 98%",

        "--primary": "186 92% 42%",
        "--primary-foreground": "222 18% 8%",

        "--secondary": "222 14% 14%",
        "--secondary-foreground": "210 20% 98%",

        "--muted": "222 14% 14%",
        "--muted-foreground": "215 16% 70%",

        "--accent": "186 60% 18%",
        "--accent-foreground": "210 20% 98%",

        "--border": "222 14% 18%",
        "--input": "222 14% 18%",
        "--ring": "186 92% 42%",

        "--destructive": "0 72% 52%",
        "--destructive-foreground": "210 20% 98%",

        "--chart-1": "186 92% 42%",
        "--chart-2": "142 70% 45%",
        "--chart-3": "0 72% 52%",
        "--chart-4": "38 92% 55%",
        "--chart-5": "210 18% 70%",

        "--radius": "0.75rem"
      },
      "semantic_extensions": {
        "add_to_css": {
          "--surface-0": "222 18% 6%",
          "--surface-1": "222 18% 8%",
          "--surface-2": "222 14% 12%",
          "--surface-3": "222 14% 16%",

          "--success": "142 70% 45%",
          "--warning": "38 92% 55%",
          "--danger": "0 72% 52%",
          "--info": "199 89% 55%",

          "--up": "142 70% 45%",
          "--down": "0 72% 52%",
          "--neutral": "215 16% 70%",

          "--alpha-strong-buy": "142 70% 45%",
          "--alpha-neutral": "38 92% 55%",
          "--alpha-sell": "0 72% 52%"
        }
      }
    },
    "allowed_gradients": {
      "rule": "Max 20% viewport; only backgrounds/overlays; never on small elements",
      "examples": [
        "radial-gradient(900px circle at 20% 10%, rgba(34,211,238,0.14), transparent 55%)",
        "radial-gradient(700px circle at 80% 0%, rgba(251,191,36,0.10), transparent 60%)"
      ]
    },
    "prohibited_gradients": [
      "blue-500 to purple-600",
      "purple-500 to pink-500",
      "green-500 to blue-500",
      "red to pink"
    ]
  },

  "layout_and_grid": {
    "global_shell": {
      "pattern": "Left rail + top command bar + main content",
      "mobile": "Bottom sheet navigation (Sheet) + sticky top search",
      "desktop": "Resizable panels for charts/news using shadcn Resizable"
    },
    "grid": {
      "container": "max-w-[1600px] w-full",
      "page_padding": "px-4 sm:px-6 lg:px-8",
      "gutter": "gap-4 md:gap-6",
      "bento": "Use 12-col grid on lg; cards span 3/4/6/8/12 columns"
    },
    "density_controls": {
      "principle": "Let users choose density",
      "implementation": [
        "Add a `Density` ToggleGroup: Compact / Comfortable",
        "Compact reduces table row height and card padding",
        "Comfortable is default for retail"
      ]
    }
  },

  "component_system": {
    "component_path": {
      "shadcn_ui": "/app/frontend/src/components/ui",
      "primary_components": [
        "button.jsx",
        "card.jsx",
        "tabs.jsx",
        "table.jsx",
        "badge.jsx",
        "command.jsx",
        "dialog.jsx",
        "sheet.jsx",
        "drawer.jsx",
        "scroll-area.jsx",
        "resizable.jsx",
        "separator.jsx",
        "skeleton.jsx",
        "tooltip.jsx",
        "sonner.jsx",
        "calendar.jsx"
      ]
    },
    "navigation": {
      "left_rail": {
        "use": ["navigation-menu.jsx", "tooltip.jsx", "badge.jsx"],
        "items": [
          "Market Overview",
          "Symbol Analysis",
          "Batch Scanner",
          "Heatmap",
          "Formulas",
          "Settings"
        ],
        "micro": "Collapsed rail shows icons with Tooltip; expanded shows labels + hotkeys"
      },
      "top_command_bar": {
        "use": ["command.jsx", "input.jsx", "popover.jsx"],
        "behavior": [
          "Cmd/Ctrl+K opens Command palette",
          "Search supports NSE/BSE/MCX prefixes (e.g., NSE:RELIANCE, MCX:GOLD)",
          "Recent symbols + pinned watchlist"
        ]
      }
    },
    "alpha_score_gauge": {
      "visual": "Radial gauge with segmented thresholds + needle + numeric readout",
      "thresholds": {
        "strong_buy": ">= 85",
        "neutral": "40-60",
        "sell": "<= 30"
      },
      "implementation_notes": [
        "Use shadcn `Card` container",
        "Gauge can be SVG (custom) + shadcn `Tooltip` for threshold explanations",
        "Always show numeric score + label badge (Strong Buy/Neutral/Sell)",
        "Add `data-testid=\"alpha-score-gauge\"` on the gauge wrapper"
      ]
    },
    "charts": {
      "lightweight": {
        "library": "recharts",
        "use_cases": ["sparklines", "mini RSI", "scanner row charts", "overview trend cards"],
        "style": [
          "No chart backgrounds; rely on Card surface",
          "Gridlines subtle: stroke with opacity 0.15",
          "Tooltip uses shadcn `Card`-like styling"
        ]
      },
      "professional": {
        "library": "lightweight-charts (TradingView) OR TradingView widget",
        "use_cases": ["candlestick + volume", "crosshair", "timeframe switching"],
        "style": [
          "Candles: up=success, down=danger",
          "Volume bars match candle direction with 40% opacity",
          "Crosshair label uses mono font"
        ]
      },
      "indicator_panels": {
        "rsi": "Dedicated small panel under candles",
        "macd": "Dedicated small panel under RSI",
        "tabs": "Timeframes (1D/1W/1M/1Y) as shadcn Tabs"
      }
    },
    "fundamentals_panel": {
      "use": ["card.jsx", "table.jsx", "badge.jsx", "separator.jsx"],
      "layout": "Two-column metric grid + Graham intrinsic value callout",
      "callouts": [
        "Graham Value: show formula icon + LaTeX + computed value",
        "Use `Badge` for valuation status: Undervalued/Fair/Overvalued"
      ]
    },
    "news_sentiment_feed": {
      "use": ["scroll-area.jsx", "card.jsx", "badge.jsx", "skeleton.jsx"],
      "item_design": [
        "Headline left, source+time right",
        "Sentiment score pill (e.g., -1.0 to +1.0) with diverging color",
        "Expand/collapse summary using Collapsible"
      ]
    },
    "batch_scanner": {
      "use": ["table.jsx", "select.jsx", "input.jsx", "badge.jsx", "pagination.jsx"],
      "features": [
        "Sortable columns (Alpha, 1D%, Volume, RSI)",
        "Row click opens Symbol Analysis",
        "Pinned columns on desktop (Symbol, Alpha)",
        "Skeleton rows during fetch"
      ]
    },
    "market_heatmap": {
      "visual": "Treemap-like grid with sector grouping",
      "implementation": [
        "Use CSS grid for MVP heatmap blocks (fast) + optional D3 treemap later",
        "Color scale: down→danger, flat→muted, up→success",
        "Each tile shows ticker + % change + Alpha mini badge",
        "Hover shows Tooltip with OHLC + volume"
      ]
    },
    "latex_formulas": {
      "library": "KaTeX (recommended) or react-katex",
      "style": [
        "Formula blocks on `surface-2` with mono caption",
        "Copy button (ghost) to copy LaTeX",
        "Always include plain-English explanation under formula"
      ]
    },
    "ai_agent_chat": {
      "placement": "Right sidebar Sheet/Resizable panel",
      "use": ["sheet.jsx", "textarea.jsx", "button.jsx", "scroll-area.jsx", "tabs.jsx"],
      "provider_switch": "Tabs for OpenAI / Claude / Gemini",
      "message_design": [
        "Assistant messages have subtle border-left accent (primary)",
        "User messages align right with muted surface",
        "Citations/assumptions in collapsible footnotes"
      ]
    },
    "sebi_disclaimer": {
      "placement": [
        "Sticky footer bar on analysis pages",
        "Inline callout above AI recommendations"
      ],
      "use": ["alert.jsx", "badge.jsx"],
      "tone": "SEBI-style: educational, not investment advice"
    }
  },

  "motion_and_microinteractions": {
    "library": "framer-motion (recommended)",
    "principles": [
      "Motion communicates state changes (loading → ready, filter applied, panel resized)",
      "Keep durations short: 120–220ms",
      "Avoid bouncy easing; use `easeOut` / `circOut`"
    ],
    "micro": {
      "buttons": [
        "Hover: subtle background shift + border brighten",
        "Active: scale 0.98",
        "Focus: visible ring using `ring-[hsl(var(--ring))]`"
      ],
      "cards": [
        "Hover lift: shadow increases slightly (no transform on large grids if it causes jitter)",
        "On data refresh: shimmer line at top (2px) for 600ms"
      ],
      "tables": [
        "Row hover: surface highlight",
        "Sort icon rotates 180deg with 150ms transition"
      ],
      "heatmap": [
        "Hover: tile border brightens + tooltip fades in",
        "Click: opens symbol drawer with slide-in"
      ]
    },
    "loading_states": {
      "rule": "Because analysis can take 5–10s, always show progressive feedback",
      "patterns": [
        "Skeleton for layout stability",
        "Stepper text: Fetching → Computing indicators → Scoring → Summarizing",
        "Cancelable requests show `Stop` button"
      ]
    }
  },

  "accessibility": {
    "requirements": [
      "WCAG AA contrast for text and key UI",
      "Keyboard navigation: Command palette, tabs, tables",
      "Reduced motion support: respect `prefers-reduced-motion`",
      "Tooltips must be accessible; avoid hover-only critical info"
    ],
    "focus": {
      "style": "Use visible focus ring; never remove outline without replacement",
      "tailwind": "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))] focus-visible:ring-offset-2 focus-visible:ring-offset-[hsl(var(--background))]"
    }
  },

  "testing_attributes": {
    "rule": "All interactive and key informational elements MUST include data-testid (kebab-case).",
    "examples": [
      "data-testid=\"command-palette-open-button\"",
      "data-testid=\"symbol-search-input\"",
      "data-testid=\"alpha-score-value\"",
      "data-testid=\"candlestick-chart-container\"",
      "data-testid=\"scanner-table\"",
      "data-testid=\"heatmap-tile\"",
      "data-testid=\"ai-chat-send-button\"",
      "data-testid=\"sebi-disclaimer-alert\""
    ]
  },

  "images": {
    "image_urls": [
      {
        "category": "hero/empty-state",
        "description": "Dark trading desk monitors for onboarding/empty states (use with heavy overlay + blur)",
        "url": "https://images.unsplash.com/photo-1660144425546-b07680e711d1?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxOTF8MHwxfHNlYXJjaHwxfHxmaW5hbmNpYWwlMjB0cmFkaW5nJTIwZGVzayUyMG1vbml0b3JzJTIwZGFya3xlbnwwfHx8YmxhY2t8MTc3NTcyMjI2Nnww&ixlib=rb-4.1.0&q=85"
      },
      {
        "category": "analysis/visual",
        "description": "Candlestick chart photo for marketing panel or loading screen backdrop (keep subtle)",
        "url": "https://images.unsplash.com/photo-1643962577481-4ff81600e439?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2Njl8MHwxfHNlYXJjaHwxfHxjYW5kbGVzdGljayUyMGNoYXJ0JTIwc2NyZWVuJTIwZGFya3xlbnwwfHx8YmxhY2t8MTc3NTcyMjI2Nnww&ixlib=rb-4.1.0&q=85"
      },
      {
        "category": "background/texture",
        "description": "Use CSS noise overlay instead of images for most surfaces (preferred).",
        "url": "(no image; use CSS noise snippet in instructions)"
      }
    ]
  },

  "libraries_and_integrations": {
    "recommended": [
      {
        "name": "framer-motion",
        "why": "Micro-interactions, panel transitions, skeleton entrance",
        "install": "npm i framer-motion",
        "usage_snippet": "import { motion } from 'framer-motion'"
      },
      {
        "name": "katex + react-katex",
        "why": "Beautiful LaTeX rendering for formulas",
        "install": "npm i katex react-katex",
        "usage_snippet": "import 'katex/dist/katex.min.css';"
      },
      {
        "name": "lightweight-charts",
        "why": "Professional TradingView-style candlesticks with crosshair",
        "install": "npm i lightweight-charts",
        "usage_snippet": "import { createChart } from 'lightweight-charts'"
      },
      {
        "name": "recharts",
        "why": "Lightweight charts for overview + sparklines",
        "install": "npm i recharts",
        "usage_snippet": "import { LineChart, Line, ResponsiveContainer } from 'recharts'"
      }
    ],
    "optional": [
      {
        "name": "d3",
        "why": "Treemap heatmap (sector grouping) for advanced version",
        "install": "npm i d3"
      }
    ]
  },

  "css_scaffolds": {
    "noise_overlay": {
      "where": "/app/frontend/src/index.css",
      "snippet": ".noise-overlay{position:relative;}\n.noise-overlay:before{content:'';position:absolute;inset:0;pointer-events:none;opacity:.06;mix-blend-mode:overlay;background-image:url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"120\" height=\"120\"><filter id=\"n\"><feTurbulence type=\"fractalNoise\" baseFrequency=\"0.9\" numOctaves=\"3\" stitchTiles=\"stitch\"/></filter><rect width=\"120\" height=\"120\" filter=\"url(%23n)\" opacity=\"0.35\"/></svg>');}"
    },
    "terminal_numbers": {
      "tailwind": "font-mono tabular-nums tracking-wide",
      "usage": "Apply to ticker/price cells and chart labels"
    },
    "card_surface": {
      "tailwind": "bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-[var(--radius)] shadow-[0_1px_0_rgba(255,255,255,0.04)]"
    }
  },

  "page_blueprints": {
    "market_overview": {
      "sections": [
        "Top command bar (search + timeframe)",
        "KPI strip: NIFTY, BANKNIFTY, USDINR, GOLD (mini sparklines)",
        "Heatmap (sectors) + Top movers table",
        "News sentiment highlights (3–5 cards)"
      ]
    },
    "symbol_analysis": {
      "tabs": ["Technical", "Fundamental", "News", "AI Agent"],
      "technical": [
        "Alpha Score gauge + recommendation summary",
        "Candlestick + volume (professional chart)",
        "RSI + MACD panels",
        "Key levels card (support/resistance)"
      ],
      "fundamental": [
        "Metrics grid",
        "Graham intrinsic value block with LaTeX",
        "Peer comparison mini table"
      ],
      "news": [
        "Scrollable feed with sentiment pills",
        "Filters: source, sentiment range"
      ],
      "ai_agent": [
        "Chat panel + provider tabs",
        "Always show SEBI disclaimer above send box"
      ]
    },
    "batch_scanner": {
      "sections": [
        "Filters row (sector, alpha range, RSI range)",
        "Scanner table (sortable) with pagination",
        "Right drawer: quick symbol preview on row click"
      ]
    }
  },

  "instructions_to_main_agent": [
    "Replace default CRA App.css centering patterns; do NOT center the app container.",
    "Set `document.documentElement.classList.add('dark')` by default (trading dashboard preference).",
    "Override shadcn tokens in /app/frontend/src/index.css using the provided HSL values.",
    "Use Space Grotesk + Inter + Azeret Mono via Google Fonts in index.html or CSS import.",
    "Implement Command palette search using shadcn `Command` with `data-testid=\"symbol-search-command\"`.",
    "Use `Resizable` for desktop multi-panel layouts (chart/news/chat).",
    "Charts: use `lightweight-charts` for candlesticks; use `recharts` for sparklines and lightweight panels.",
    "LaTeX: use KaTeX; wrap formulas in Card with copy button.",
    "Every interactive element and key info must include `data-testid` in kebab-case.",
    "Loading: always show skeleton + stepper text for 5–10s operations; never leave blank panels.",
    "SEBI disclaimer must be visible on analysis + AI pages (Alert component)."
  ]
}

<General UI UX Design Guidelines>  
    - You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms
    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text
   - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json

 **GRADIENT RESTRICTION RULE**
NEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc
NEVER use dark gradients for logo, testimonial, footer etc
NEVER let gradients cover more than 20% of the viewport.
NEVER apply gradients to text-heavy content or reading areas.
NEVER use gradients on small UI elements (<100px width).
NEVER stack multiple gradient layers in the same viewport.

**ENFORCEMENT RULE:**
    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors

**How and where to use:**
   • Section backgrounds (not content backgrounds)
   • Hero section header content. Eg: dark to light to dark color
   • Decorative overlays and accent elements only
   • Hero section with 2-3 mild color
   • Gradients creation can be done for any angle say horizontal, vertical or diagonal

- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**

</Font Guidelines>

- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. 
   
- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.

- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.
   
- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly
    Eg: - if it implies playful/energetic, choose a colorful scheme
           - if it implies monochrome/minimal, choose a black–white/neutral scheme

**Component Reuse:**
	- Prioritize using pre-existing components from src/components/ui when applicable
	- Create new components that match the style and conventions of existing components when needed
	- Examine existing components to understand the project's component patterns before creating new ones

**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component

**Best Practices:**
	- Use Shadcn/UI as the primary component library for consistency and accessibility
	- Import path: ./components/[component-name]

**Export Conventions:**
	- Components MUST use named exports (export const ComponentName = ...)
	- Pages MUST use default exports (export default function PageName() {...})

**Toasts:**
  - Use `sonner` for toasts"
  - Sonner component are located in `/app/src/components/ui/sonner.tsx`

Use 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals.
</General UI UX Design Guidelines>
