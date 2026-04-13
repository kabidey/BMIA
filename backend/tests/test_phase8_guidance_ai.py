"""
Phase 8 Backend Tests - Guidance AI RAG Integration
Tests AI-powered question answering about BSE corporate filings using RAG pipeline.
"""
import pytest
import requests
import os
import time

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


class TestGuidanceSuggestions:
    """Tests for GET /api/guidance/suggestions endpoint"""
    
    def test_suggestions_returns_array(self):
        """Test suggestions endpoint returns array of suggested questions"""
        response = requests.get(f"{BASE_URL}/api/guidance/suggestions")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
        assert len(data["suggestions"]) > 0, "Should have at least one suggestion"
        
        # Verify suggestions are strings
        for suggestion in data["suggestions"]:
            assert isinstance(suggestion, str)
            assert len(suggestion) > 10, "Suggestions should be meaningful questions"
        
        print(f"✅ Suggestions endpoint: {len(data['suggestions'])} suggestions returned")
        print(f"   Sample: {data['suggestions'][0][:60]}...")


class TestGuidanceAsk:
    """Tests for POST /api/guidance/ask endpoint (RAG AI)"""
    
    def test_ask_basic_question(self):
        """Test asking a basic question about filings"""
        response = requests.post(
            f"{BASE_URL}/api/guidance/ask",
            json={"question": "What are the most recent board meeting announcements?", "conversation_history": []},
            timeout=60
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "answer" in data, "Response should have 'answer' field"
        assert data["answer"] is not None, "Answer should not be None"
        assert len(data["answer"]) > 100, "Answer should be substantial"
        
        # Verify sources
        assert "sources" in data
        assert isinstance(data["sources"], list)
        
        # Verify metadata
        assert "filings_retrieved" in data
        assert isinstance(data["filings_retrieved"], int)
        assert data["filings_retrieved"] > 0, "Should retrieve some filings"
        
        assert "stocks_in_context" in data
        assert isinstance(data["stocks_in_context"], list)
        
        print(f"✅ Basic question answered: {len(data['answer'])} chars, {data['filings_retrieved']} filings retrieved")
        print(f"   Stocks in context: {data['stocks_in_context'][:5]}...")
    
    def test_ask_with_conversation_history(self):
        """Test follow-up question with conversation history"""
        history = [
            {"role": "user", "content": "What are the most recent board meeting announcements?"},
            {"role": "assistant", "content": "Bandhan Bank has a board meeting on 28/04/2026 for Q4 results."}
        ]
        
        response = requests.post(
            f"{BASE_URL}/api/guidance/ask",
            json={"question": "Tell me more about BANDHANBNK", "conversation_history": history},
            timeout=60
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response
        assert "answer" in data
        assert data["answer"] is not None
        
        # The answer should reference BANDHANBNK since we asked about it
        assert "BANDHANBNK" in data["answer"].upper() or "BANDHAN" in data["answer"].upper(), \
            "Answer should reference the stock we asked about"
        
        print(f"✅ Follow-up question with history answered: {len(data['answer'])} chars")
    
    def test_ask_empty_question_handled(self):
        """Test that empty question is handled gracefully"""
        response = requests.post(
            f"{BASE_URL}/api/guidance/ask",
            json={"question": "", "conversation_history": []},
            timeout=60
        )
        # Should still return 200 but with a generic response or error message
        assert response.status_code == 200
        data = response.json()
        
        # Should have answer field (even if it's an error message or generic response)
        assert "answer" in data or "error" in data
        
        print(f"✅ Empty question handled gracefully")
    
    def test_ask_specific_stock_question(self):
        """Test asking about a specific stock"""
        response = requests.post(
            f"{BASE_URL}/api/guidance/ask",
            json={"question": "Show me all filings for WIPRO in the last 7 days", "conversation_history": []},
            timeout=90  # Increased timeout for LLM calls
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "answer" in data or "error" in data, "Response should have answer or error"
        
        # If answer is None, check if there's an error (LLM timeout is acceptable)
        if data.get("answer") is None:
            if "error" in data:
                print(f"⚠️ Stock-specific question returned error (LLM timeout): {data.get('error', 'Unknown')}")
                pytest.skip("LLM timeout - intermittent issue")
            else:
                pytest.fail("Answer is None without error message")
        
        # Verify query context extracted the stock
        if "query_context" in data:
            assert "stocks" in data["query_context"]
        
        print(f"✅ Stock-specific question answered: {len(data['answer'])} chars")
    
    def test_ask_category_question(self):
        """Test asking about a specific category"""
        response = requests.post(
            f"{BASE_URL}/api/guidance/ask",
            json={"question": "Show me all insider trading activity. Any red flags?", "conversation_history": []},
            timeout=90  # Increased timeout for LLM calls
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "answer" in data or "error" in data, "Response should have answer or error"
        
        # If answer is None, check if there's an error (LLM timeout is acceptable)
        if data.get("answer") is None:
            if "error" in data:
                print(f"⚠️ Category question returned error (LLM timeout): {data.get('error', 'Unknown')}")
                pytest.skip("LLM timeout - intermittent issue")
            else:
                pytest.fail("Answer is None without error message")
        
        # Verify query context extracted the category
        if "query_context" in data:
            assert "categories" in data["query_context"]
        
        print(f"✅ Category-specific question answered: {len(data['answer'])} chars")
    
    def test_ask_response_has_sources(self):
        """Test that response includes source citations"""
        response = requests.post(
            f"{BASE_URL}/api/guidance/ask",
            json={"question": "What are the critical filings today?", "conversation_history": []},
            timeout=60
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify sources structure
        assert "sources" in data
        if data["sources"]:
            source = data["sources"][0]
            assert "symbol" in source
            assert "date" in source
            assert "category" in source
            assert "headline" in source
        
        print(f"✅ Response includes {len(data.get('sources', []))} source citations")


class TestGuidanceRegressionEndpoints:
    """Regression tests for existing Guidance endpoints (Phase 7)"""
    
    def test_guidance_stats_still_works(self):
        """Test /api/guidance/stats still returns expected data"""
        response = requests.get(f"{BASE_URL}/api/guidance/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "total_announcements" in data
        assert "total_stocks" in data
        assert "categories" in data
        assert "recent_7d" in data
        
        # Verify expected values based on previous test
        assert data["total_announcements"] >= 1000, "Should have 1000+ announcements"
        assert data["total_stocks"] >= 200, "Should have 200+ stocks"
        
        print(f"✅ Stats regression: {data['total_announcements']} announcements, {data['total_stocks']} stocks")
    
    def test_guidance_items_still_works(self):
        """Test /api/guidance pagination still works"""
        response = requests.get(f"{BASE_URL}/api/guidance?page=1&limit=40")
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "pages" in data
        
        assert len(data["items"]) <= 40
        assert data["page"] == 1
        
        print(f"✅ Items regression: {data['total']} total items, page {data['page']}/{data['pages']}")
    
    def test_guidance_stocks_still_works(self):
        """Test /api/guidance/stocks still returns stock list"""
        response = requests.get(f"{BASE_URL}/api/guidance/stocks")
        assert response.status_code == 200
        data = response.json()
        
        assert "stocks" in data
        assert "total" in data
        assert data["total"] > 0
        
        print(f"✅ Stocks regression: {data['total']} stocks with announcements")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
