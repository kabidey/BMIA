# BMIA - Bharat Market Intel Agent (Mobile App)

## Overview
Expo React Native Android app for the BMIA (Bharat Market Intel Agent) - an AI-powered Indian stock market intelligence platform.

## Architecture
- **Frontend**: Expo SDK 54, React Native, expo-router (file-based routing)
- **Backend**: External API at `https://bmia.pesmifs.com` (no local backend needed)
- **Navigation**: 5-tab bottom navigation (Market, Signals, Scanner, Portfolio, More)

## Authentication
- **OrgLens employee verification** + JWT token auth
- Flow: Email → OrgLens API (active SMIFS employee check) → Password (set or login) → JWT session
- JWT stored securely via `expo-secure-store` (native) / `localStorage` (web)
- Bearer token attached to all API calls automatically
- Auto-logout on token expiry (30s check interval, skip for superadmin)
- 3-step login: Email check → Password/Set-Password → Dashboard
- Logout from Settings screen

## Features
### Core Screens (5 Tabs)
1. **Market Overview** - Live cockpit dashboard with indices, breadth, VIX, PCR, sector rotation
2. **AI Signals** - Active AI-generated trading signals with BUY/SELL/HOLD/AVOID actions, God Mode consensus
3. **Batch Scanner** - AI-powered NSE stock scanner with God Mode multi-LLM ensemble
4. **Portfolio Analytics** - 4 AI-constructed portfolios (Swing, Quick Entry, Alpha Generator, Value)
5. **More** - Menu hub for secondary screens

### Secondary Screens
- **Symbol Analysis** - Deep stock analysis with technicals, fundamentals, sentiment
- **Portfolio Detail** - Individual portfolio holdings with P&L
- **Track Record** - Signal performance metrics (win rate, profit factor, equity curve)
- **Watchlist** - Saved stock tracking
- **Guidance** - AI market guidance and educational insights
- **How It Works** - Platform explanation with 7-step walkthrough
- **Audit Log** - Activity tracking
- **Settings** - App version, biometric authentication, platform info

### Additional Features
- **Biometric Authentication** (expo-local-authentication)
- **Push Notifications** (expo-notifications)
- **Version Info** (expo-application)
- **Pull-to-refresh** on data screens
- **Dark theme** (Swiss & High-Contrast design)

## API Endpoints Used
- `GET /api/market/cockpit` - Market overview data
- `GET /api/signals/active` - Active AI signals
- `GET /api/signals/track-record` - Signal performance
- `GET /api/portfolios` - Portfolio list with holdings
- `GET /api/analysis/{symbol}` - Stock analysis
- `POST /api/batch/ai-scan` - AI batch scanning
- `POST /api/batch/god-scan` - God Mode scanning
- `GET /api/audit-log` - Activity log

## Tech Stack
- Expo SDK 54
- React Native 0.81.5
- expo-router 6.x (file-based routing)
- expo-local-authentication 17.x
- expo-notifications 0.32.x
- @expo/vector-icons (Ionicons)
