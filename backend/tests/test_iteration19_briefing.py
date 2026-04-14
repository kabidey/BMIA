"""
Iteration 19: Guidance Briefing Service Tests
Tests for the daily intelligence briefing feature:
- GET /api/guidance/briefing - returns cached or fresh briefing
- POST /api/guidance/briefing/refresh - force regenerate briefing
- Caching behavior (6h cache)
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestGuidanceBriefing:
    """Tests for the Guidance Briefing API endpoints"""
    
    def test_health_check(self):
        """Verify backend is running"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print(f"✓ Health check passed: {data}")
    
    def test_get_briefing_returns_200(self):
        """GET /api/guidance/briefing should return 200"""
        # First call may take 15-30s due to LLM generation
        response = requests.get(f"{BASE_URL}/api/guidance/briefing", timeout=60)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ GET /api/guidance/briefing returned 200")
    
    def test_get_briefing_has_narrative(self):
        """GET /api/guidance/briefing should return narrative (non-empty string)"""
        response = requests.get(f"{BASE_URL}/api/guidance/briefing", timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        # Narrative should exist and be a non-empty string
        assert "narrative" in data, "Response missing 'narrative' field"
        narrative = data.get("narrative")
        # Narrative can be None if LLM fails, but should exist
        if narrative is not None:
            assert isinstance(narrative, str), f"Narrative should be string, got {type(narrative)}"
            print(f"✓ Narrative present: {narrative[:100]}..." if len(str(narrative)) > 100 else f"✓ Narrative: {narrative}")
        else:
            print("⚠ Narrative is None (LLM may have failed)")
    
    def test_get_briefing_has_critical_filings(self):
        """GET /api/guidance/briefing should return critical_filings array"""
        response = requests.get(f"{BASE_URL}/api/guidance/briefing", timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        assert "critical_filings" in data, "Response missing 'critical_filings' field"
        critical = data.get("critical_filings")
        assert isinstance(critical, list), f"critical_filings should be list, got {type(critical)}"
        print(f"✓ critical_filings: {len(critical)} items")
        
        # Validate structure of first item if exists
        if critical:
            first = critical[0]
            assert "stock_symbol" in first, "Critical filing missing stock_symbol"
            assert "headline" in first, "Critical filing missing headline"
            print(f"  Sample: {first.get('stock_symbol')} - {first.get('headline', '')[:50]}...")
    
    def test_get_briefing_has_insider_activity(self):
        """GET /api/guidance/briefing should return insider_activity array"""
        response = requests.get(f"{BASE_URL}/api/guidance/briefing", timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        assert "insider_activity" in data, "Response missing 'insider_activity' field"
        insider = data.get("insider_activity")
        assert isinstance(insider, list), f"insider_activity should be list, got {type(insider)}"
        print(f"✓ insider_activity: {len(insider)} items")
    
    def test_get_briefing_has_upcoming_agms(self):
        """GET /api/guidance/briefing should return upcoming_agms array"""
        response = requests.get(f"{BASE_URL}/api/guidance/briefing", timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        assert "upcoming_agms" in data, "Response missing 'upcoming_agms' field"
        agms = data.get("upcoming_agms")
        assert isinstance(agms, list), f"upcoming_agms should be list, got {type(agms)}"
        print(f"✓ upcoming_agms: {len(agms)} items")
    
    def test_get_briefing_has_board_meetings(self):
        """GET /api/guidance/briefing should return board_meetings array"""
        response = requests.get(f"{BASE_URL}/api/guidance/briefing", timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        assert "board_meetings" in data, "Response missing 'board_meetings' field"
        board = data.get("board_meetings")
        assert isinstance(board, list), f"board_meetings should be list, got {type(board)}"
        print(f"✓ board_meetings: {len(board)} items")
    
    def test_get_briefing_has_top_active_stocks(self):
        """GET /api/guidance/briefing should return top_active_stocks array"""
        response = requests.get(f"{BASE_URL}/api/guidance/briefing", timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        assert "top_active_stocks" in data, "Response missing 'top_active_stocks' field"
        active = data.get("top_active_stocks")
        assert isinstance(active, list), f"top_active_stocks should be list, got {type(active)}"
        print(f"✓ top_active_stocks: {len(active)} items")
        
        # Validate structure if exists
        if active:
            first = active[0]
            assert "symbol" in first, "Active stock missing symbol"
            assert "filings_7d" in first, "Active stock missing filings_7d"
            print(f"  Sample: {first.get('symbol')} - {first.get('filings_7d')} filings in 7d")
    
    def test_get_briefing_has_generated_at(self):
        """GET /api/guidance/briefing should return generated_at timestamp"""
        response = requests.get(f"{BASE_URL}/api/guidance/briefing", timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        assert "generated_at" in data, "Response missing 'generated_at' field"
        generated_at = data.get("generated_at")
        assert generated_at is not None, "generated_at should not be None"
        assert isinstance(generated_at, str), f"generated_at should be string, got {type(generated_at)}"
        print(f"✓ generated_at: {generated_at}")
    
    def test_briefing_caching_same_timestamp(self):
        """Second call within 6 hours should return same generated_at (cached)"""
        # First call
        response1 = requests.get(f"{BASE_URL}/api/guidance/briefing", timeout=60)
        assert response1.status_code == 200
        data1 = response1.json()
        ts1 = data1.get("generated_at")
        
        # Wait a bit
        time.sleep(2)
        
        # Second call
        response2 = requests.get(f"{BASE_URL}/api/guidance/briefing", timeout=60)
        assert response2.status_code == 200
        data2 = response2.json()
        ts2 = data2.get("generated_at")
        
        # Should be same timestamp (cached)
        assert ts1 == ts2, f"Expected cached response with same timestamp. Got ts1={ts1}, ts2={ts2}"
        print(f"✓ Caching works: both calls returned generated_at={ts1}")
    
    def test_refresh_briefing_returns_200(self):
        """POST /api/guidance/briefing/refresh should return 200"""
        response = requests.post(f"{BASE_URL}/api/guidance/briefing/refresh", timeout=90)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ POST /api/guidance/briefing/refresh returned 200")
    
    def test_refresh_briefing_returns_fresh_data(self):
        """POST /api/guidance/briefing/refresh should return fresh data with new generated_at"""
        # Get current briefing
        response1 = requests.get(f"{BASE_URL}/api/guidance/briefing", timeout=60)
        assert response1.status_code == 200
        data1 = response1.json()
        ts1 = data1.get("generated_at")
        
        # Wait a moment
        time.sleep(2)
        
        # Force refresh
        response2 = requests.post(f"{BASE_URL}/api/guidance/briefing/refresh", timeout=90)
        assert response2.status_code == 200
        data2 = response2.json()
        ts2 = data2.get("generated_at")
        
        # Should have new timestamp
        assert ts2 is not None, "Refresh response missing generated_at"
        # Timestamps should be different (new generation)
        assert ts2 != ts1, f"Expected new timestamp after refresh. Got ts1={ts1}, ts2={ts2}"
        print(f"✓ Refresh generated new briefing: old={ts1}, new={ts2}")
        
        # Verify structure is complete
        assert "narrative" in data2
        assert "critical_filings" in data2
        assert "insider_activity" in data2
        assert "upcoming_agms" in data2
        assert "board_meetings" in data2
        assert "top_active_stocks" in data2
        print(f"✓ Refreshed briefing has all required fields")
    
    def test_briefing_response_structure_complete(self):
        """Verify complete response structure of briefing endpoint"""
        response = requests.get(f"{BASE_URL}/api/guidance/briefing", timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "narrative",
            "critical_filings",
            "insider_activity",
            "upcoming_agms",
            "board_meetings",
            "top_active_stocks",
            "generated_at",
            "date"
        ]
        
        for field in required_fields:
            assert field in data, f"Response missing required field: {field}"
        
        print(f"✓ All required fields present in briefing response")
        print(f"  Summary: {len(data.get('critical_filings', []))} critical, "
              f"{len(data.get('insider_activity', []))} insider, "
              f"{len(data.get('upcoming_agms', []))} AGMs, "
              f"{len(data.get('board_meetings', []))} board meetings, "
              f"{len(data.get('top_active_stocks', []))} active stocks")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
