"""
Test BMIA external API endpoints
Tests Scanner, Portfolio, and Guidance APIs
"""
import pytest
import requests
import os

BASE_URL = "https://bmia.pesmifs.com"

class TestScannerAPI:
    """Scanner API tests - AI Scan and God Mode"""

    def test_ai_scan_endpoint(self):
        """Test POST /api/batch/ai-scan with Top 15 Large Caps"""
        symbols = [
            'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
            'HINDUNILVR.NS', 'ITC.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS',
            'LT.NS', 'AXISBANK.NS', 'WIPRO.NS', 'TATAMOTORS.NS', 'MARUTI.NS',
        ]
        payload = {"symbols": symbols, "mode": "ai"}
        
        response = requests.post(f"{BASE_URL}/api/batch/ai-scan", json=payload, timeout=60)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "results" in data, "Response missing 'results' field"
        assert isinstance(data["results"], list), "Results should be a list"
        assert len(data["results"]) > 0, "Results should not be empty"
        
        # Verify result structure
        result = data["results"][0]
        required_fields = ["symbol", "rank", "action", "ai_score", "conviction", "price", "change_pct", "rsi", "rationale"]
        for field in required_fields:
            assert field in result, f"Result missing required field: {field}"
        
        # Verify technical indicators
        assert "rsi" in result and isinstance(result["rsi"], (int, float)), "RSI should be numeric"
        assert "adx" in result or "adx_direction" in result, "Should have ADX data"
        assert "obv_trend" in result, "Should have OBV trend"
        
        # Verify metadata
        assert "provider" in data, "Response missing 'provider' field"
        assert "model" in data, "Response missing 'model' field"
        
        print(f"✓ AI Scan returned {len(data['results'])} results")
        print(f"✓ Provider: {data.get('provider')}, Model: {data.get('model')}")
        print(f"✓ Sample result: {result['symbol']} - {result['action']} (AI Score: {result['ai_score']}, Conviction: {result['conviction']})")


class TestPortfolioAPI:
    """Portfolio API tests - Portfolios and Walk-Forward data"""

    def test_portfolios_endpoint(self):
        """Test GET /api/portfolios - should return 6 portfolios"""
        response = requests.get(f"{BASE_URL}/api/portfolios", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "portfolios" in data, "Response missing 'portfolios' field"
        portfolios = data["portfolios"]
        assert isinstance(portfolios, list), "Portfolios should be a list"
        assert len(portfolios) == 6, f"Expected 6 portfolios, got {len(portfolios)}"
        
        # Verify portfolio types
        expected_types = ["swing", "quick_entry", "alpha_generator", "value_stocks", "long_term", "bespoke_forward_looking"]
        actual_types = [p["type"] for p in portfolios]
        for expected_type in expected_types:
            assert expected_type in actual_types, f"Missing portfolio type: {expected_type}"
        
        # Verify portfolio structure
        portfolio = portfolios[0]
        required_fields = ["type", "name", "description", "actual_invested", "current_value", "total_pnl_pct", "holdings", "construction_log", "horizon"]
        for field in required_fields:
            assert field in portfolio, f"Portfolio missing required field: {field}"
        
        # Verify construction_log structure
        assert "universe_size" in portfolio["construction_log"], "construction_log missing universe_size"
        assert "screened_candidates" in portfolio["construction_log"], "construction_log missing screened_candidates"
        assert "deep_enriched" in portfolio["construction_log"], "construction_log missing deep_enriched"
        
        # Verify holdings structure
        assert isinstance(portfolio["holdings"], list), "Holdings should be a list"
        if len(portfolio["holdings"]) > 0:
            holding = portfolio["holdings"][0]
            assert "symbol" in holding, "Holding missing symbol"
            assert "pnl_pct" in holding, "Holding missing pnl_pct"
            assert "fundamental_grade" in holding, "Holding missing fundamental_grade"
        
        print(f"✓ Portfolios endpoint returned {len(portfolios)} portfolios")
        print(f"✓ Portfolio types: {', '.join(actual_types)}")
        print(f"✓ Sample portfolio: {portfolio['name']} ({portfolio['type']}) - {len(portfolio['holdings'])} holdings")

    def test_walk_forward_endpoint(self):
        """Test GET /api/portfolios/walk-forward - should return simulation forecasts"""
        response = requests.get(f"{BASE_URL}/api/portfolios/walk-forward", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "records" in data, "Response missing 'records' field"
        records = data["records"]
        assert isinstance(records, list), "Records should be a list"
        assert len(records) > 0, "Records should not be empty"
        
        # Verify record structure
        record = records[0]
        assert "portfolio_type" in record, "Record missing portfolio_type"
        assert "forecast" in record, "Record missing forecast"
        
        # Verify forecast structure
        forecast = record["forecast"]
        required_forecast_fields = ["expected_return_pct", "median_return_pct", "var_95_pct", "probability_of_profit_pct"]
        for field in required_forecast_fields:
            assert field in forecast, f"Forecast missing required field: {field}"
            assert isinstance(forecast[field], (int, float)), f"{field} should be numeric"
        
        # Check for LSTM fields (optional but should be present)
        if "lstm_annualized_return_pct" in forecast:
            assert isinstance(forecast["lstm_annualized_return_pct"], (int, float)), "LSTM return should be numeric"
            assert "lstm_annualized_vol_pct" in forecast, "If LSTM return present, vol should be too"
        
        print(f"✓ Walk-forward endpoint returned {len(records)} records")
        print(f"✓ Sample forecast for {record['portfolio_type']}: Expected {forecast['expected_return_pct']:.1f}%, Median {forecast['median_return_pct']:.1f}%, VaR 95% {forecast['var_95_pct']:.1f}%, P(Profit) {forecast['probability_of_profit_pct']:.0f}%")


class TestGuidanceAPI:
    """Guidance API tests - BSE filings"""

    def test_guidance_endpoint_page1(self):
        """Test GET /api/guidance?page=1&limit=20 - should return BSE filings"""
        response = requests.get(f"{BASE_URL}/api/guidance?page=1&limit=20", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data, "Response missing 'items' field"
        assert "total" in data, "Response missing 'total' field"
        assert "pages" in data, "Response missing 'pages' field"
        
        items = data["items"]
        assert isinstance(items, list), "Items should be a list"
        assert len(items) == 20, f"Expected 20 items, got {len(items)}"
        
        # Verify total count
        total = data["total"]
        assert total > 6000, f"Expected >6000 total filings, got {total}"
        
        # Verify item structure
        item = items[0]
        required_fields = ["news_id", "headline", "stock_name", "stock_symbol", "category", "news_date", "pdf_url"]
        for field in required_fields:
            assert field in item, f"Item missing required field: {field}"
        
        # Verify optional fields
        assert "pdf_text_length" in item, "Item missing pdf_text_length"
        assert "pdf_extracted" in item, "Item missing pdf_extracted"
        
        print(f"✓ Guidance endpoint returned {len(items)} items (page 1)")
        print(f"✓ Total filings: {total:,}, Total pages: {data['pages']}")
        print(f"✓ Sample item: {item['headline'][:80]}... ({item['stock_name']}, {item['category']})")

    def test_guidance_pagination(self):
        """Test pagination - page 2 should return different items"""
        response1 = requests.get(f"{BASE_URL}/api/guidance?page=1&limit=20", timeout=30)
        response2 = requests.get(f"{BASE_URL}/api/guidance?page=2&limit=20", timeout=30)
        
        assert response1.status_code == 200, "Page 1 failed"
        assert response2.status_code == 200, "Page 2 failed"
        
        data1 = response1.json()
        data2 = response2.json()
        
        items1 = data1["items"]
        items2 = data2["items"]
        
        # Verify different items
        ids1 = {item["news_id"] for item in items1}
        ids2 = {item["news_id"] for item in items2}
        
        assert len(ids1.intersection(ids2)) == 0, "Page 1 and Page 2 should have different items"
        
        print(f"✓ Pagination working - Page 1 and Page 2 have different items")
