"""
Phase 7 Backend Tests - Guidance Page & Track Record/Learning Context
Tests BSE Corporate Announcements scraping, filtering, pagination, and signal performance endpoints.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthAndBasics:
    """Basic health check tests"""
    
    def test_health_endpoint(self):
        """Test /api/health returns ok status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "BMIA"
        print(f"✅ Health check passed: {data}")


class TestGuidanceStats:
    """Tests for /api/guidance/stats endpoint"""
    
    def test_guidance_stats_returns_data(self):
        """Test stats endpoint returns total_announcements, total_stocks, categories, recent_7d"""
        response = requests.get(f"{BASE_URL}/api/guidance/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields exist
        assert "total_announcements" in data
        assert "total_stocks" in data
        assert "categories" in data
        assert "recent_7d" in data
        
        # Verify data types and values
        assert isinstance(data["total_announcements"], int)
        assert data["total_announcements"] > 0, "Should have announcements in DB"
        assert isinstance(data["total_stocks"], int)
        assert data["total_stocks"] > 0, "Should have stocks in DB"
        assert isinstance(data["categories"], list)
        assert len(data["categories"]) > 0, "Should have categories"
        
        # Verify category structure
        for cat in data["categories"]:
            assert "name" in cat
            assert "count" in cat
            assert isinstance(cat["count"], int)
        
        print(f"✅ Guidance stats: {data['total_announcements']} announcements, {data['total_stocks']} stocks, {len(data['categories'])} categories")


class TestGuidanceItems:
    """Tests for /api/guidance endpoint with filters and pagination"""
    
    def test_guidance_items_basic(self):
        """Test basic guidance items retrieval"""
        response = requests.get(f"{BASE_URL}/api/guidance?page=1&limit=10")
        assert response.status_code == 200
        data = response.json()
        
        # Verify pagination structure
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "pages" in data
        
        assert data["page"] == 1
        assert data["limit"] == 10
        assert len(data["items"]) <= 10
        assert data["total"] > 0
        
        # Verify item structure
        if data["items"]:
            item = data["items"][0]
            assert "news_id" in item
            assert "headline" in item
            assert "stock_symbol" in item
            assert "category" in item
            assert "news_date" in item
            assert "pdf_url" in item
        
        print(f"✅ Guidance items: {data['total']} total, page {data['page']}/{data['pages']}")
    
    def test_guidance_filter_by_symbol(self):
        """Test filtering by stock symbol"""
        # First get a stock that has announcements
        stocks_response = requests.get(f"{BASE_URL}/api/guidance/stocks")
        stocks = stocks_response.json().get("stocks", [])
        assert len(stocks) > 0, "Need stocks to test filter"
        
        test_symbol = stocks[0]["symbol"]
        
        response = requests.get(f"{BASE_URL}/api/guidance?symbol={test_symbol}&limit=5")
        assert response.status_code == 200
        data = response.json()
        
        # All items should match the symbol
        for item in data["items"]:
            assert item["stock_symbol"] == test_symbol or test_symbol.lower() in item["stock_symbol"].lower()
        
        print(f"✅ Symbol filter works: {data['total']} items for {test_symbol}")
    
    def test_guidance_filter_by_category(self):
        """Test filtering by category"""
        # Get available categories
        stats_response = requests.get(f"{BASE_URL}/api/guidance/stats")
        categories = stats_response.json().get("categories", [])
        assert len(categories) > 0, "Need categories to test filter"
        
        test_category = categories[0]["name"]
        
        response = requests.get(f"{BASE_URL}/api/guidance?category={test_category}&limit=5")
        assert response.status_code == 200
        data = response.json()
        
        # All items should match the category
        for item in data["items"]:
            assert test_category.lower() in item["category"].lower()
        
        print(f"✅ Category filter works: {data['total']} items for '{test_category}'")
    
    def test_guidance_search_headlines(self):
        """Test search by headline"""
        response = requests.get(f"{BASE_URL}/api/guidance?search=dividend&limit=5")
        assert response.status_code == 200
        data = response.json()
        
        # All items should contain search term in headline
        for item in data["items"]:
            assert "dividend" in item["headline"].lower()
        
        print(f"✅ Search filter works: {data['total']} items matching 'dividend'")
    
    def test_guidance_pagination(self):
        """Test pagination works correctly"""
        # Get page 1
        page1_response = requests.get(f"{BASE_URL}/api/guidance?page=1&limit=5")
        page1_data = page1_response.json()
        
        # Get page 2
        page2_response = requests.get(f"{BASE_URL}/api/guidance?page=2&limit=5")
        page2_data = page2_response.json()
        
        assert page1_data["page"] == 1
        assert page2_data["page"] == 2
        
        # Items should be different
        if page1_data["items"] and page2_data["items"]:
            page1_ids = {item["news_id"] for item in page1_data["items"]}
            page2_ids = {item["news_id"] for item in page2_data["items"]}
            assert page1_ids.isdisjoint(page2_ids), "Page 1 and 2 should have different items"
        
        print(f"✅ Pagination works: Page 1 has {len(page1_data['items'])} items, Page 2 has {len(page2_data['items'])} items")


class TestGuidanceStocks:
    """Tests for /api/guidance/stocks endpoint"""
    
    def test_guidance_stocks_list(self):
        """Test stocks list returns stocks with announcement counts"""
        response = requests.get(f"{BASE_URL}/api/guidance/stocks")
        assert response.status_code == 200
        data = response.json()
        
        assert "stocks" in data
        assert "total" in data
        assert data["total"] > 0
        
        # Verify stock structure
        if data["stocks"]:
            stock = data["stocks"][0]
            assert "symbol" in stock
            assert "name" in stock
            assert "scrip_code" in stock
            assert "announcements" in stock
            assert "latest" in stock
            assert isinstance(stock["announcements"], int)
            assert stock["announcements"] > 0
        
        print(f"✅ Stocks list: {data['total']} stocks with announcements")


class TestGuidanceScrape:
    """Tests for /api/guidance/scrape endpoint (background job)"""
    
    def test_scrape_trigger_returns_job_id(self):
        """Test POST /api/guidance/scrape returns job_id"""
        response = requests.post(f"{BASE_URL}/api/guidance/scrape?days_back=1")
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert "status" in data
        assert data["status"] == "started"
        
        job_id = data["job_id"]
        print(f"✅ Scrape triggered: job_id={job_id}")
        
        # Test polling endpoint exists
        poll_response = requests.get(f"{BASE_URL}/api/guidance/scrape/{job_id}")
        assert poll_response.status_code == 200
        poll_data = poll_response.json()
        assert "status" in poll_data
        assert poll_data["status"] in ["running", "complete", "error"]
        
        print(f"✅ Scrape poll works: status={poll_data['status']}")
    
    def test_scrape_invalid_job_returns_404(self):
        """Test invalid job_id returns 404"""
        response = requests.get(f"{BASE_URL}/api/guidance/scrape/invalid-job-id")
        assert response.status_code == 404
        print("✅ Invalid job_id returns 404")


class TestTrackRecord:
    """Tests for /api/signals/track-record endpoint"""
    
    def test_track_record_returns_metrics(self):
        """Test track record endpoint returns comprehensive metrics"""
        response = requests.get(f"{BASE_URL}/api/signals/track-record")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "total_signals" in data
        assert "open_signals" in data
        assert "closed_signals" in data
        assert "metrics" in data
        
        # Verify metrics structure
        metrics = data["metrics"]
        assert "win_rate" in metrics
        assert "avg_return" in metrics
        assert "avg_win" in metrics
        assert "avg_loss" in metrics
        
        # Verify additional sections
        assert "streaks" in data
        assert "equity_curve" in data
        assert "by_action" in data
        assert "by_sector" in data
        
        print(f"✅ Track record: {data['total_signals']} signals, win_rate={metrics['win_rate']}")


class TestLearningContext:
    """Tests for /api/signals/learning-context endpoint"""
    
    def test_learning_context_returns_data(self):
        """Test learning context endpoint returns AI learning data"""
        response = requests.get(f"{BASE_URL}/api/signals/learning-context")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "type" in data
        assert "total_signals" in data
        assert "win_rate" in data
        assert "avg_return" in data
        assert "lessons" in data
        
        # Verify lessons is a list
        assert isinstance(data["lessons"], list)
        
        print(f"✅ Learning context: {data['total_signals']} signals analyzed, {len(data['lessons'])} lessons")


class TestPDFUrls:
    """Tests for PDF URL format"""
    
    def test_pdf_urls_are_valid_bse_format(self):
        """Test PDF URLs follow BSE format"""
        response = requests.get(f"{BASE_URL}/api/guidance?limit=10")
        data = response.json()
        
        bse_pdf_base = "https://www.bseindia.com/xml-data/corpfiling/AttachLive"
        
        for item in data["items"]:
            if item.get("pdf_url"):
                assert item["pdf_url"].startswith(bse_pdf_base), f"Invalid PDF URL: {item['pdf_url']}"
        
        print("✅ All PDF URLs follow BSE format")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
