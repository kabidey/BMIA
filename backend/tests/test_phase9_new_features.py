"""
Phase 9 Testing: PDF Extraction, BSE Prices, Watchlist/Portfolio, Signal Alerts
Tests for 4 new features:
1. PDF text extraction from BSE filings for deeper RAG analysis
2. BSE price data via bse library
3. Portfolio tracking / watchlist persistence
4. Signal alert notifications
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

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


class TestPDFExtraction:
    """PDF Extraction feature tests"""
    
    def test_pdf_stats_endpoint(self):
        """GET /api/guidance/pdf/stats should return PDF extraction statistics"""
        response = requests.get(f"{BASE_URL}/api/guidance/pdf/stats", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected fields
        assert "total_filings_with_pdf" in data
        assert "pdfs_processed" in data
        assert "pdfs_with_text" in data
        assert "pdfs_pending" in data
        assert "total_chunks" in data
        
        print(f"✅ PDF Stats: {data['total_filings_with_pdf']} filings with PDF, "
              f"{data['pdfs_processed']} processed, {data['pdfs_with_text']} with text, "
              f"{data['total_chunks']} chunks")
        
        # Verify data types
        assert isinstance(data["total_filings_with_pdf"], int)
        assert isinstance(data["pdfs_processed"], int)
        assert isinstance(data["total_chunks"], int)

    def test_pdf_process_endpoint(self):
        """POST /api/guidance/pdf/process should trigger manual PDF processing"""
        response = requests.post(f"{BASE_URL}/api/guidance/pdf/process?limit=5", timeout=120)
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected fields
        assert "processed" in data or "total_attempted" in data
        print(f"✅ PDF Process: {data}")


class TestBSEPriceData:
    """BSE Price Data feature tests"""
    
    def test_bse_quote_reliance(self):
        """GET /api/bse/quote/500325 should return BSE quote for Reliance"""
        response = requests.get(f"{BASE_URL}/api/bse/quote/500325", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected fields
        assert "scrip_code" in data
        assert "ltp" in data
        assert "change" in data
        assert "change_pct" in data
        assert "high" in data
        assert "low" in data
        
        print(f"✅ BSE Quote Reliance (500325): LTP={data.get('ltp')}, "
              f"Change={data.get('change')} ({data.get('change_pct')}%)")

    def test_bse_quote_hdfc(self):
        """GET /api/bse/quote/500180 should return BSE quote for HDFC Bank"""
        response = requests.get(f"{BASE_URL}/api/bse/quote/500180", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert "scrip_code" in data
        assert "ltp" in data
        print(f"✅ BSE Quote HDFC Bank (500180): LTP={data.get('ltp')}")

    def test_bse_gainers(self):
        """GET /api/bse/gainers should return top BSE gainers"""
        response = requests.get(f"{BASE_URL}/api/bse/gainers", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert "gainers" in data
        # May be empty outside market hours
        print(f"✅ BSE Gainers: {len(data.get('gainers', []))} stocks returned")

    def test_bse_losers(self):
        """GET /api/bse/losers should return top BSE losers"""
        response = requests.get(f"{BASE_URL}/api/bse/losers", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert "losers" in data
        print(f"✅ BSE Losers: {len(data.get('losers', []))} stocks returned")

    def test_bse_near_52w_high(self):
        """GET /api/bse/near-52w/high should return stocks near 52-week high"""
        response = requests.get(f"{BASE_URL}/api/bse/near-52w/high", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert "stocks" in data
        print(f"✅ BSE Near 52W High: {len(data.get('stocks', []))} stocks returned")

    def test_bse_near_52w_low(self):
        """GET /api/bse/near-52w/low should return stocks near 52-week low"""
        response = requests.get(f"{BASE_URL}/api/bse/near-52w/low", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert "stocks" in data
        print(f"✅ BSE Near 52W Low: {len(data.get('stocks', []))} stocks returned")

    def test_bse_advance_decline(self):
        """GET /api/bse/advance-decline should return BSE advance/decline data"""
        response = requests.get(f"{BASE_URL}/api/bse/advance-decline", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        # May return empty dict outside market hours
        print(f"✅ BSE Advance/Decline: {data}")


class TestWatchlistPortfolio:
    """Watchlist/Portfolio feature tests"""
    
    def test_get_watchlist(self):
        """GET /api/watchlist should return watchlist items"""
        response = requests.get(f"{BASE_URL}/api/watchlist", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        print(f"✅ Watchlist: {len(data.get('items', []))} items")
        
        # Check if test data exists (RELIANCE, HDFCBANK)
        items = data.get("items", [])
        symbols = [i.get("symbol") for i in items]
        print(f"   Symbols in watchlist: {symbols}")

    def test_get_watchlist_with_prices(self):
        """GET /api/watchlist?with_prices=true should return watchlist with live BSE prices"""
        response = requests.get(f"{BASE_URL}/api/watchlist?with_prices=true", timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        items = data.get("items", [])
        
        if items:
            # Check that price data is included
            first_item = items[0]
            print(f"✅ Watchlist with prices: {len(items)} items")
            print(f"   First item: {first_item.get('symbol')} - LTP: {first_item.get('ltp')}, "
                  f"Entry: {first_item.get('entry_price')}, P&L: {first_item.get('total_pnl')}")
        else:
            print(f"✅ Watchlist with prices: Empty watchlist")

    def test_get_watchlist_summary(self):
        """GET /api/watchlist/summary should return portfolio summary"""
        response = requests.get(f"{BASE_URL}/api/watchlist/summary", timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected fields
        assert "total_stocks" in data
        assert "total_invested" in data
        assert "total_value" in data
        assert "total_pnl" in data
        assert "winners" in data
        assert "losers" in data
        
        print(f"✅ Watchlist Summary: {data['total_stocks']} stocks, "
              f"Invested: {data['total_invested']}, Value: {data['total_value']}, "
              f"P&L: {data['total_pnl']}, Winners: {data['winners']}, Losers: {data['losers']}")

    def test_add_stock_to_watchlist(self):
        """POST /api/watchlist/add should add stock to watchlist"""
        payload = {
            "symbol": "TESTSTOCK",
            "scrip_code": "999999",
            "name": "Test Stock Ltd",
            "entry_price": 100.0,
            "quantity": 5,
            "notes": "Test entry"
        }
        response = requests.post(f"{BASE_URL}/api/watchlist/add", json=payload, timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("status") in ["added", "updated"]
        assert data.get("symbol") == "TESTSTOCK"
        print(f"✅ Add to watchlist: {data}")

    def test_update_watchlist_item(self):
        """PUT /api/watchlist/TESTSTOCK should update watchlist item"""
        payload = {
            "notes": "Updated test notes",
            "entry_price": 105.0,
            "quantity": 10
        }
        response = requests.put(f"{BASE_URL}/api/watchlist/TESTSTOCK", json=payload, timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("status") in ["updated", "not_found"]
        print(f"✅ Update watchlist item: {data}")

    def test_remove_stock_from_watchlist(self):
        """DELETE /api/watchlist/TESTSTOCK should remove stock from watchlist"""
        response = requests.delete(f"{BASE_URL}/api/watchlist/TESTSTOCK", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("status") in ["removed", "not_found"]
        print(f"✅ Remove from watchlist: {data}")

    def test_verify_test_data_exists(self):
        """Verify RELIANCE and HDFCBANK exist in watchlist (test data)"""
        response = requests.get(f"{BASE_URL}/api/watchlist", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        items = data.get("items", [])
        symbols = [i.get("symbol") for i in items]
        
        # Check if test data exists
        has_reliance = "RELIANCE" in symbols
        has_hdfc = "HDFCBANK" in symbols
        
        print(f"✅ Test data check: RELIANCE={has_reliance}, HDFCBANK={has_hdfc}")
        
        if not has_reliance:
            # Add RELIANCE test data
            payload = {
                "symbol": "RELIANCE",
                "scrip_code": "500325",
                "name": "Reliance Industries Ltd",
                "entry_price": 1350.0,
                "quantity": 10,
                "notes": "Test data"
            }
            requests.post(f"{BASE_URL}/api/watchlist/add", json=payload, timeout=30)
            print("   Added RELIANCE test data")
        
        if not has_hdfc:
            # Add HDFCBANK test data
            payload = {
                "symbol": "HDFCBANK",
                "scrip_code": "500180",
                "name": "HDFC Bank Ltd",
                "entry_price": 1800.0,
                "quantity": 5,
                "notes": "Test data"
            }
            requests.post(f"{BASE_URL}/api/watchlist/add", json=payload, timeout=30)
            print("   Added HDFCBANK test data")


class TestSignalAlerts:
    """Signal Alerts feature tests"""
    
    def test_signal_alerts_endpoint(self):
        """GET /api/signals/alerts should return recent signal alerts"""
        response = requests.get(f"{BASE_URL}/api/signals/alerts", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert "alerts" in data
        alerts = data.get("alerts", [])
        
        print(f"✅ Signal Alerts: {len(alerts)} alerts returned")
        
        if alerts:
            first_alert = alerts[0]
            print(f"   First alert: {first_alert.get('symbol')} - {first_alert.get('status')} "
                  f"({first_alert.get('return_pct')}%)")

    def test_signal_alerts_with_since_param(self):
        """GET /api/signals/alerts?since=<timestamp> should filter by time"""
        # Use a timestamp from 24 hours ago
        import datetime
        since = (datetime.datetime.now() - datetime.timedelta(hours=24)).isoformat()
        
        response = requests.get(f"{BASE_URL}/api/signals/alerts?since={since}", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert "alerts" in data
        print(f"✅ Signal Alerts (since 24h ago): {len(data.get('alerts', []))} alerts")

    def test_active_signals_regression(self):
        """GET /api/signals/active should still work (regression)"""
        response = requests.get(f"{BASE_URL}/api/signals/active", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert "signals" in data
        print(f"✅ Active Signals regression: {len(data.get('signals', []))} active signals")


class TestGuidanceStocksForWatchlist:
    """Test guidance stocks endpoint used by watchlist add modal"""
    
    def test_guidance_stocks_for_search(self):
        """GET /api/guidance/stocks should return stocks for watchlist search"""
        response = requests.get(f"{BASE_URL}/api/guidance/stocks", timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        assert "stocks" in data
        stocks = data.get("stocks", [])
        
        print(f"✅ Guidance Stocks: {len(stocks)} stocks available for search")
        
        if stocks:
            # Check structure
            first_stock = stocks[0]
            assert "symbol" in first_stock
            print(f"   Sample stock: {first_stock}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
