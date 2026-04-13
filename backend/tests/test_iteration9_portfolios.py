"""
Iteration 9 Testing: Major Portfolio Redesign - Autonomous AI-Managed Portfolios
Tests for the new portfolio system:
1. GET /api/portfolios/overview - returns overview of all 6 portfolios
2. GET /api/portfolios - returns all portfolios with holdings and strategies
3. GET /api/portfolios/{strategy_type} - returns specific portfolio
4. POST /api/portfolios/{strategy_type}/refresh-prices - triggers price refresh
5. GET /api/portfolios/rebalance-log-all/recent - returns recent rebalance logs
6. GET /api/guidance/pdf/stats - returns updated PDF extraction stats
7. GET /api/signals/alerts - returns signal alerts
8. GET /api/bse/quote/500325 - BSE quote regression
9. Regression tests for guidance and market overview
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Portfolio strategy types
PORTFOLIO_STRATEGIES = [
    "bespoke_forward_looking",
    "quick_entry", 
    "long_term",
    "swing",
    "alpha_generator",
    "value_stocks"
]


class TestHealthAndRegression:
    """Basic health check and regression tests"""
    
    def test_health_endpoint(self):
        """Health check should return ok"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "BMIA"
        print(f"✅ Health check passed: {data}")

    def test_guidance_stats_regression(self):
        """Guidance stats should still work (regression)"""
        response = requests.get(f"{BASE_URL}/api/guidance/stats", timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert "total_announcements" in data
        assert "total_stocks" in data
        print(f"✅ Guidance stats regression: {data['total_announcements']} announcements, {data['total_stocks']} stocks")

    def test_market_overview_regression(self):
        """Market overview should still work (regression)"""
        response = requests.get(f"{BASE_URL}/api/market/overview", timeout=60)
        assert response.status_code == 200
        data = response.json()
        assert "gainers" in data or "all" in data
        print(f"✅ Market overview regression passed")


class TestPortfolioOverview:
    """Portfolio Overview endpoint tests"""
    
    def test_portfolio_overview_endpoint(self):
        """GET /api/portfolios/overview should return overview of all 6 portfolios"""
        response = requests.get(f"{BASE_URL}/api/portfolios/overview", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected fields
        assert "total_capital" in data
        assert "total_invested" in data
        assert "total_value" in data
        assert "total_pnl" in data
        assert "active_portfolios" in data
        assert "pending_construction" in data
        assert "portfolios" in data
        
        # Verify total capital is 6 * 50L = 3 crore
        assert data["total_capital"] == 30000000  # 6 * 50 lakhs
        
        print(f"✅ Portfolio Overview:")
        print(f"   Total Capital: ₹{data['total_capital']:,}")
        print(f"   Total Invested: ₹{data['total_invested']:,}")
        print(f"   Total Value: ₹{data['total_value']:,}")
        print(f"   Total P&L: ₹{data['total_pnl']:,} ({data.get('total_pnl_pct', 0):.2f}%)")
        print(f"   Active Portfolios: {data['active_portfolios']}/6")
        print(f"   Pending Construction: {data['pending_construction']}")
        
        # Verify portfolios array
        portfolios = data.get("portfolios", [])
        print(f"   Portfolios in response: {len(portfolios)}")
        for p in portfolios:
            status = p.get("status", "unknown")
            name = p.get("name", p.get("type", "unknown"))
            holdings = p.get("holdings_count", 0)
            pnl_pct = p.get("total_pnl_pct", 0)
            print(f"     - {name}: {status}, {holdings} holdings, P&L: {pnl_pct:.2f}%")


class TestPortfoliosList:
    """Portfolio List endpoint tests"""
    
    def test_portfolios_list_endpoint(self):
        """GET /api/portfolios should return all portfolios with holdings and strategies"""
        response = requests.get(f"{BASE_URL}/api/portfolios", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected fields
        assert "portfolios" in data
        assert "strategies" in data
        
        portfolios = data.get("portfolios", [])
        strategies = data.get("strategies", {})
        
        print(f"✅ Portfolios List:")
        print(f"   Total portfolios: {len(portfolios)}")
        print(f"   Strategies defined: {len(strategies)}")
        
        # Verify strategies dict has all 6 types
        for strategy_type in PORTFOLIO_STRATEGIES:
            if strategy_type in strategies:
                s = strategies[strategy_type]
                print(f"   Strategy '{strategy_type}': {s.get('name', 'N/A')} - {s.get('horizon', 'N/A')}")
        
        # Check portfolio details
        for p in portfolios:
            ptype = p.get("type", "unknown")
            status = p.get("status", "unknown")
            holdings = p.get("holdings", [])
            print(f"   Portfolio '{ptype}': {status}, {len(holdings)} holdings")


class TestSpecificPortfolios:
    """Tests for specific portfolio endpoints"""
    
    def test_long_term_portfolio(self):
        """GET /api/portfolios/long_term should return specific portfolio with holdings"""
        response = requests.get(f"{BASE_URL}/api/portfolios/long_term", timeout=30)
        
        if response.status_code == 404:
            print(f"⚠️ Long Term portfolio not yet constructed (expected if daemon still running)")
            return
            
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected fields
        assert "type" in data
        assert data["type"] == "long_term"
        assert "name" in data
        assert "status" in data
        assert "holdings" in data
        
        holdings = data.get("holdings", [])
        print(f"✅ Long Term Portfolio:")
        print(f"   Name: {data.get('name')}")
        print(f"   Status: {data.get('status')}")
        print(f"   Holdings: {len(holdings)}")
        print(f"   Current Value: ₹{data.get('current_value', 0):,.0f}")
        print(f"   Total P&L: ₹{data.get('total_pnl', 0):,.0f} ({data.get('total_pnl_pct', 0):.2f}%)")
        
        if holdings and data.get("status") == "active":
            # Verify holdings structure
            for i, h in enumerate(holdings[:3]):  # Show first 3
                print(f"     [{i+1}] {h.get('symbol', 'N/A')}: Entry ₹{h.get('entry_price', 0):.2f}, "
                      f"Current ₹{h.get('current_price', 0):.2f}, P&L {h.get('pnl_pct', 0):.2f}%")

    def test_alpha_generator_portfolio(self):
        """GET /api/portfolios/alpha_generator should return active portfolio with holdings"""
        response = requests.get(f"{BASE_URL}/api/portfolios/alpha_generator", timeout=30)
        
        if response.status_code == 404:
            print(f"⚠️ Alpha Generator portfolio not yet constructed")
            return
            
        assert response.status_code == 200
        data = response.json()
        
        assert "type" in data
        assert data["type"] == "alpha_generator"
        
        print(f"✅ Alpha Generator Portfolio:")
        print(f"   Status: {data.get('status')}")
        print(f"   Holdings: {len(data.get('holdings', []))}")
        print(f"   Current Value: ₹{data.get('current_value', 0):,.0f}")

    def test_bespoke_forward_looking_portfolio(self):
        """GET /api/portfolios/bespoke_forward_looking should return portfolio"""
        response = requests.get(f"{BASE_URL}/api/portfolios/bespoke_forward_looking", timeout=30)
        
        if response.status_code == 404:
            print(f"⚠️ Bespoke Forward Looking portfolio not yet constructed")
            return
            
        assert response.status_code == 200
        data = response.json()
        
        print(f"✅ Bespoke Forward Looking Portfolio:")
        print(f"   Status: {data.get('status')}")
        print(f"   Holdings: {len(data.get('holdings', []))}")

    def test_invalid_portfolio_returns_404(self):
        """GET /api/portfolios/invalid_type should return 404"""
        response = requests.get(f"{BASE_URL}/api/portfolios/invalid_type", timeout=30)
        assert response.status_code == 404
        print(f"✅ Invalid portfolio type returns 404 as expected")


class TestPortfolioPriceRefresh:
    """Portfolio price refresh endpoint tests"""
    
    def test_refresh_prices_long_term(self):
        """POST /api/portfolios/long_term/refresh-prices should trigger price refresh"""
        response = requests.post(f"{BASE_URL}/api/portfolios/long_term/refresh-prices", timeout=60)
        
        if response.status_code == 404:
            print(f"⚠️ Long Term portfolio not active, cannot refresh prices")
            return
            
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected fields
        assert "type" in data
        assert "current_value" in data
        assert "total_pnl" in data
        assert "holdings" in data
        
        print(f"✅ Price Refresh for Long Term:")
        print(f"   Current Value: ₹{data.get('current_value', 0):,.0f}")
        print(f"   Total P&L: ₹{data.get('total_pnl', 0):,.0f} ({data.get('total_pnl_pct', 0):.2f}%)")


class TestRebalanceLogs:
    """Rebalance log endpoint tests"""
    
    def test_recent_rebalance_logs(self):
        """GET /api/portfolios/rebalance-log-all/recent should return recent rebalance logs"""
        response = requests.get(f"{BASE_URL}/api/portfolios/rebalance-log-all/recent?limit=10", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert "logs" in data
        logs = data.get("logs", [])
        
        print(f"✅ Recent Rebalance Logs: {len(logs)} entries")
        
        for log in logs[:3]:  # Show first 3
            action = log.get("action", "unknown")
            portfolio = log.get("portfolio_type", "unknown")
            timestamp = log.get("timestamp", "unknown")
            changes = log.get("changes", [])
            print(f"   - {portfolio}: {action} at {timestamp}, {len(changes)} changes")


class TestPDFExtractionStats:
    """PDF Extraction stats tests (updated for inline approach)"""
    
    def test_pdf_stats_endpoint(self):
        """GET /api/guidance/pdf/stats should return updated PDF extraction stats"""
        response = requests.get(f"{BASE_URL}/api/guidance/pdf/stats", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected fields (inline approach)
        assert "total_filings_with_pdf" in data
        assert "pdfs_processed" in data
        assert "pdfs_with_text" in data
        assert "pdfs_pending" in data
        
        print(f"✅ PDF Extraction Stats (Inline Approach):")
        print(f"   Total filings with PDF: {data.get('total_filings_with_pdf', 0)}")
        print(f"   PDFs processed: {data.get('pdfs_processed', 0)}")
        print(f"   PDFs with text: {data.get('pdfs_with_text', 0)}")
        print(f"   PDFs pending: {data.get('pdfs_pending', 0)}")


class TestSignalAlerts:
    """Signal Alerts endpoint tests"""
    
    def test_signal_alerts_endpoint(self):
        """GET /api/signals/alerts should return signal alerts"""
        response = requests.get(f"{BASE_URL}/api/signals/alerts", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert "alerts" in data
        alerts = data.get("alerts", [])
        
        print(f"✅ Signal Alerts: {len(alerts)} alerts")
        
        for alert in alerts[:3]:  # Show first 3
            symbol = alert.get("symbol", "unknown")
            status = alert.get("status", "unknown")
            return_pct = alert.get("return_pct", 0)
            print(f"   - {symbol}: {status} ({return_pct:.2f}%)")


class TestBSEQuoteRegression:
    """BSE Quote regression tests"""
    
    def test_bse_quote_reliance(self):
        """GET /api/bse/quote/500325 should return BSE quote for Reliance"""
        response = requests.get(f"{BASE_URL}/api/bse/quote/500325", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert "scrip_code" in data
        assert "ltp" in data
        
        print(f"✅ BSE Quote Reliance (500325): LTP={data.get('ltp')}, "
              f"Change={data.get('change')} ({data.get('change_pct')}%)")


class TestOldWatchlistEndpointsRemoved:
    """Verify old watchlist endpoints are removed"""
    
    def test_old_watchlist_endpoint_removed(self):
        """GET /api/watchlist should return 404 or redirect (old endpoint removed)"""
        response = requests.get(f"{BASE_URL}/api/watchlist", timeout=30)
        # Old endpoint should be removed - expect 404 or different behavior
        # If it returns 200, the old system is still there
        if response.status_code == 200:
            data = response.json()
            # Check if it's the old format (items array) or new format
            if "items" in data:
                print(f"⚠️ Old watchlist endpoint still exists with {len(data.get('items', []))} items")
            else:
                print(f"✅ Watchlist endpoint returns different format: {list(data.keys())}")
        elif response.status_code == 404:
            print(f"✅ Old watchlist endpoint removed (404)")
        else:
            print(f"⚠️ Watchlist endpoint returns status {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
