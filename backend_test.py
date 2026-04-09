#!/usr/bin/env python3
"""
BMIA Backend API Testing Suite
Tests all endpoints with real market data from yfinance
"""
import requests
import sys
import time
import json
from datetime import datetime

class BMIAAPITester:
    def __init__(self, base_url="https://nse-bse-analyzer-4.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details="", response_time=None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat()
        })

    def run_test(self, name, method, endpoint, expected_status=200, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        start_time = time.time()
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            
            response_time = round(time.time() - start_time, 2)
            
            success = response.status_code == expected_status
            
            if success:
                try:
                    response_data = response.json()
                    self.log_test(name, True, f"Status: {response.status_code}, Response time: {response_time}s", response_time)
                    return True, response_data
                except json.JSONDecodeError:
                    self.log_test(name, False, f"Invalid JSON response. Status: {response.status_code}", response_time)
                    return False, {}
            else:
                self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}. Response: {response.text[:200]}", response_time)
                return False, {}

        except requests.exceptions.Timeout:
            self.log_test(name, False, f"Request timeout after {timeout}s")
            return False, {}
        except Exception as e:
            self.log_test(name, False, f"Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test health endpoint"""
        success, data = self.run_test("Health Check", "GET", "api/health")
        if success:
            if data.get("status") == "ok" and data.get("service") == "BMIA":
                return True
            else:
                print(f"   ⚠️  Health check response missing expected fields: {data}")
        return False

    def test_symbol_search(self):
        """Test symbol search functionality"""
        # Test search with query
        success, data = self.run_test("Symbol Search - RELIANCE", "GET", "api/symbols?q=RELIANCE")
        if success:
            symbols = data.get("symbols", [])
            if any("RELIANCE" in s.get("symbol", "") for s in symbols):
                print(f"   ✓ Found RELIANCE in search results")
                return True
            else:
                print(f"   ⚠️  RELIANCE not found in search results: {symbols}")
        return False

    def test_nifty50_symbols(self):
        """Test Nifty 50 symbols endpoint"""
        success, data = self.run_test("Nifty 50 Symbols", "GET", "api/symbols/nifty50")
        if success:
            symbols = data.get("symbols", [])
            if len(symbols) >= 40:  # Should have most Nifty 50 stocks
                print(f"   ✓ Found {len(symbols)} Nifty 50 symbols")
                return True
            else:
                print(f"   ⚠️  Expected more Nifty 50 symbols, got {len(symbols)}")
        return False

    def test_market_overview(self):
        """Test market overview endpoint"""
        success, data = self.run_test("Market Overview", "GET", "api/market/overview", timeout=45)
        if success:
            gainers = data.get("gainers", [])
            losers = data.get("losers", [])
            if len(gainers) > 0 and len(losers) > 0:
                print(f"   ✓ Found {len(gainers)} gainers and {len(losers)} losers")
                return True
            else:
                print(f"   ⚠️  Missing gainers or losers data")
        return False

    def test_market_heatmap(self):
        """Test market heatmap endpoint"""
        success, data = self.run_test("Market Heatmap", "GET", "api/market/heatmap", timeout=45)
        if success:
            heatmap = data.get("heatmap", {})
            if len(heatmap) > 0:
                sectors = list(heatmap.keys())
                print(f"   ✓ Found heatmap data for sectors: {sectors}")
                return True
            else:
                print(f"   ⚠️  No heatmap data found")
        return False

    def test_stock_analysis(self):
        """Test full stock analysis - this is the main feature"""
        print(f"\n🔍 Testing Stock Analysis (RELIANCE.NS) - This may take 15-20 seconds...")
        
        success, data = self.run_test(
            "Stock Analysis - RELIANCE.NS", 
            "POST", 
            "api/analyze-stock",
            data={"symbol": "RELIANCE.NS", "period": "6mo", "interval": "1d"},
            timeout=60
        )
        
        if success:
            # Check all required components
            required_fields = ["market_data", "technical", "fundamental", "news", "sentiment", "alpha"]
            missing_fields = []
            
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)
                elif field == "market_data" and "error" in data[field]:
                    missing_fields.append(f"{field} (has error)")
                elif field == "alpha" and "alpha_score" not in data[field]:
                    missing_fields.append(f"{field} (missing alpha_score)")
            
            if not missing_fields:
                alpha_score = data["alpha"]["alpha_score"]
                recommendation = data["alpha"]["recommendation"]
                print(f"   ✓ Complete analysis: Alpha Score = {alpha_score}, Recommendation = {recommendation}")
                return True, data
            else:
                print(f"   ⚠️  Missing or invalid fields: {missing_fields}")
                return False, data
        
        return False, {}

    def test_batch_scanner(self):
        """Test batch scanner - this takes the longest"""
        print(f"\n🔍 Testing Batch Scanner - This may take 30-45 seconds...")
        
        success, data = self.run_test(
            "Batch Scanner", 
            "POST", 
            "api/batch/analyze",
            data={},  # Will use default Nifty 50 subset
            timeout=90
        )
        
        if success:
            results = data.get("results", [])
            if len(results) > 0:
                # Check if results have alpha scores
                scored_results = [r for r in results if "alpha_score" in r]
                print(f"   ✓ Batch scan completed: {len(scored_results)} stocks with alpha scores")
                return True
            else:
                print(f"   ⚠️  No results from batch scanner")
        return False

    def test_ai_chat(self):
        """Test AI chat functionality"""
        success, data = self.run_test(
            "AI Chat", 
            "POST", 
            "api/ai/chat",
            data={
                "symbol": "RELIANCE.NS",
                "query": "What are the key risks for this stock?",
                "provider": "openai"
            },
            timeout=30
        )
        
        if success:
            if "response" in data and len(data["response"]) > 50:
                print(f"   ✓ AI response received (length: {len(data['response'])} chars)")
                return True
            else:
                print(f"   ⚠️  AI response too short or missing")
        return False

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting BMIA Backend API Tests")
        print(f"   Base URL: {self.base_url}")
        print("=" * 60)
        
        # Basic tests first
        self.test_health_check()
        self.test_symbol_search()
        self.test_nifty50_symbols()
        
        # Market data tests
        self.test_market_overview()
        self.test_market_heatmap()
        
        # Core analysis tests (these take longer)
        analysis_success, analysis_data = self.test_stock_analysis()
        
        # Batch scanner (longest test)
        self.test_batch_scanner()
        
        # AI features
        self.test_ai_chat()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            failed_tests = [r for r in self.test_results if not r["success"]]
            print(f"❌ {len(failed_tests)} tests failed:")
            for test in failed_tests:
                print(f"   - {test['test']}: {test['details']}")
            return 1

def main():
    tester = BMIAAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())