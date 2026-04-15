"""
Iteration 21: Test Screener.in-style Stock Documents API
Tests the GET /api/guidance/stock/{symbol}/documents endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestStockDocumentsAPI:
    """Tests for the Screener.in-style stock documents endpoint"""
    
    def test_hdfcbank_documents_returns_categorized_data(self):
        """GET /api/guidance/stock/HDFCBANK/documents returns categorized documents"""
        response = requests.get(f"{BASE_URL}/api/guidance/stock/HDFCBANK/documents")
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify required fields exist
        assert "symbol" in data, "Response missing 'symbol' field"
        assert data["symbol"] == "HDFCBANK", f"Expected symbol 'HDFCBANK', got {data['symbol']}"
        
        # Verify stock metadata
        assert "stock_name" in data, "Response missing 'stock_name' field"
        assert "scrip_code" in data, "Response missing 'scrip_code' field"
        assert "total" in data, "Response missing 'total' field"
        
        # Verify categorized document arrays exist
        required_categories = [
            "announcements", "important", "annual_reports", "credit_ratings",
            "board_meetings", "results", "insider_activity", "agm_egm", "corporate_actions"
        ]
        for cat in required_categories:
            assert cat in data, f"Response missing '{cat}' category"
            assert isinstance(data[cat], list), f"'{cat}' should be a list"
        
        # Verify total > 0 for HDFCBANK (known stock with data)
        assert data["total"] > 0, f"Expected total > 0 for HDFCBANK, got {data['total']}"
        
        # Verify BSE link is present
        assert "bse_link" in data, "Response missing 'bse_link' field"
        if data["scrip_code"]:
            assert data["bse_link"] is not None, "BSE link should be present when scrip_code exists"
    
    def test_hdfcbank_document_item_structure(self):
        """Verify document items have correct structure"""
        response = requests.get(f"{BASE_URL}/api/guidance/stock/HDFCBANK/documents")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check announcements array has items
        if data["announcements"]:
            item = data["announcements"][0]
            
            # Verify document item fields
            required_fields = ["news_id", "headline", "category", "news_date", "stock_symbol", "stock_name"]
            for field in required_fields:
                assert field in item, f"Document item missing '{field}' field"
            
            # Verify optional fields exist (can be null)
            assert "pdf_url" in item, "Document item missing 'pdf_url' field"
            assert "critical" in item, "Document item missing 'critical' field"
            assert "more_text" in item, "Document item missing 'more_text' field"
    
    def test_reliance_documents_returns_data(self):
        """GET /api/guidance/stock/RELIANCE/documents returns categorized docs"""
        response = requests.get(f"{BASE_URL}/api/guidance/stock/RELIANCE/documents")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify symbol
        assert data["symbol"] == "RELIANCE", f"Expected symbol 'RELIANCE', got {data['symbol']}"
        
        # Verify categorized arrays exist
        assert "announcements" in data
        assert "important" in data
        assert "annual_reports" in data
        assert "board_meetings" in data
        assert "insider_activity" in data
        
        # Total should be >= 0 (may or may not have data)
        assert data["total"] >= 0, f"Total should be >= 0, got {data['total']}"
    
    def test_nonexistent_stock_returns_empty_gracefully(self):
        """GET /api/guidance/stock/NONEXISTENT/documents returns total=0 gracefully"""
        response = requests.get(f"{BASE_URL}/api/guidance/stock/NONEXISTENT/documents")
        
        # Should return 200, not 404
        assert response.status_code == 200, f"Expected 200 for nonexistent stock, got {response.status_code}"
        
        data = response.json()
        
        # Verify symbol is returned
        assert data["symbol"] == "NONEXISTENT", f"Expected symbol 'NONEXISTENT', got {data['symbol']}"
        
        # Verify total is 0
        assert data["total"] == 0, f"Expected total=0 for nonexistent stock, got {data['total']}"
        
        # Verify all category arrays are empty
        assert data["announcements"] == [], "announcements should be empty"
        assert data["annual_reports"] == [], "annual_reports should be empty"
        assert data["credit_ratings"] == [], "credit_ratings should be empty"
        assert data["board_meetings"] == [], "board_meetings should be empty"
        assert data["results"] == [], "results should be empty"
        assert data["insider_activity"] == [], "insider_activity should be empty"
        assert data["agm_egm"] == [], "agm_egm should be empty"
        assert data["corporate_actions"] == [], "corporate_actions should be empty"
    
    def test_case_insensitive_symbol_lookup(self):
        """Verify symbol lookup is case-insensitive"""
        # Test lowercase
        response_lower = requests.get(f"{BASE_URL}/api/guidance/stock/hdfcbank/documents")
        assert response_lower.status_code == 200
        
        data_lower = response_lower.json()
        
        # Test uppercase
        response_upper = requests.get(f"{BASE_URL}/api/guidance/stock/HDFCBANK/documents")
        assert response_upper.status_code == 200
        
        data_upper = response_upper.json()
        
        # Both should return same total (case-insensitive)
        # Note: The symbol in response may differ based on implementation
        assert data_lower["total"] == data_upper["total"], "Case-insensitive lookup should return same results"
    
    def test_tcs_documents_endpoint(self):
        """GET /api/guidance/stock/TCS/documents returns valid response"""
        response = requests.get(f"{BASE_URL}/api/guidance/stock/TCS/documents")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["symbol"] == "TCS"
        assert "total" in data
        assert "announcements" in data
        assert isinstance(data["announcements"], list)


class TestGuidanceStocksEndpoint:
    """Test the stocks list endpoint used by the dropdown"""
    
    def test_guidance_stocks_returns_list(self):
        """GET /api/guidance/stocks returns list of stocks"""
        response = requests.get(f"{BASE_URL}/api/guidance/stocks")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        assert "stocks" in data, "Response missing 'stocks' field"
        assert "total" in data, "Response missing 'total' field"
        assert isinstance(data["stocks"], list), "'stocks' should be a list"
        
        # Should have some stocks
        if data["total"] > 0:
            stock = data["stocks"][0]
            # Verify stock item structure
            assert "symbol" in stock, "Stock item missing 'symbol'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
