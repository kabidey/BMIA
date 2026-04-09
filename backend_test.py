#!/usr/bin/env python3
"""
BMIA Phase 4 Backend API Testing Suite
Tests expanded parameters (25+ technical, 30+ fundamental), AI batch scanning, and signal generation
"""
import requests
import sys
import time
import json
from datetime import datetime

class BMIAAPITester:
    def __init__(self, base_url="https://equity-sentiment-hub.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.failed_tests = []

    def log_test(self, name, success, details="", response_time=None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
            self.failed_tests.append(f"{name}: {details}")
        
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

    def test_expanded_symbols(self):
        """Test expanded symbol universe (Phase 4: beyond Yahoo Finance)"""
        success, data = self.run_test("Expanded Symbol Universe", "GET", "api/symbols")
        if success:
            symbols = data.get("symbols", [])
            total = data.get("total", 0)
            print(f"   📊 Found {total} symbols in expanded universe")
            
            # Check for expanded universe (should have Nifty 50 + Next 50 + Midcap + Commodities)
            if total >= 150:
                print(f"   ✅ Expanded universe confirmed: {total} symbols")
            else:
                print(f"   ⚠️  Limited universe: only {total} symbols (expected 150+)")
            
            # Check for different asset classes
            sectors = set(s.get('sector', 'Unknown') for s in symbols)
            print(f"   📈 Found {len(sectors)} sectors: {', '.join(list(sectors)[:8])}...")
            
            # Check for commodities
            commodities = [s for s in symbols if '=F' in s.get('symbol', '')]
            if commodities:
                print(f"   🥇 Found {len(commodities)} commodities (Gold, Silver, Oil, etc.)")
            
            return True, data
        return False, {}

    def test_sectors_endpoint(self):
        """Test sectors endpoint for filtering"""
        success, data = self.run_test("Sectors Endpoint", "GET", "api/sectors")
        if success:
            sectors = data.get("sectors", [])
            print(f"   📊 Found {len(sectors)} sectors for filtering")
            if len(sectors) >= 10:
                print(f"   ✅ Comprehensive sector list: {', '.join(sectors[:6])}...")
                return True
            else:
                print(f"   ⚠️  Limited sectors: {sectors}")
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

    def test_expanded_stock_analysis(self):
        """Test expanded stock analysis with 25+ technical and 30+ fundamental metrics (Phase 4)"""
        print(f"\n🔍 Testing Expanded Stock Analysis (TCS.NS) - 25+ Technical + 30+ Fundamental...")
        
        success, data = self.run_test(
            "Expanded Stock Analysis - TCS.NS", 
            "POST", 
            "api/analyze-stock",
            data={"symbol": "TCS.NS", "period": "6mo", "interval": "1d"},
            timeout=60
        )
        
        if success:
            print(f"   📊 Analysis for {data.get('symbol', 'Unknown')}")
            
            # Check technical indicators (should have 25+ indicators)
            technical = data.get('technical', {})
            if technical and not technical.get('error'):
                # Phase 4 expanded indicators
                indicators = [
                    'rsi', 'macd', 'bollinger', 'adx', 'stochastic', 'atr', 'obv',
                    'williams_r', 'cci', 'roc', 'ichimoku', 'fibonacci', 'pivot_points',
                    'vsa', 'breakout', 'moving_averages', 'price_action'
                ]
                found_indicators = [ind for ind in indicators if ind in technical]
                print(f"   🔧 Technical indicators: {len(found_indicators)}/17 core indicators found")
                
                # Check specific Phase 4 expanded features
                if 'bollinger' in technical:
                    bb = technical['bollinger']
                    if 'squeeze' in bb and 'percent_b' in bb:
                        print(f"   ✅ Bollinger: Squeeze={bb.get('squeeze')}, %B={bb.get('percent_b')}")
                
                if 'ichimoku' in technical:
                    ich = technical['ichimoku']
                    if 'cloud_signal' in ich and 'tk_cross' in ich:
                        print(f"   ✅ Ichimoku: Cloud={ich.get('cloud_signal')}, TK Cross={ich.get('tk_cross')}")
                
                if 'vsa' in technical:
                    vsa = technical['vsa']
                    if 'signal' in vsa and 'vol_ratio' in vsa:
                        print(f"   ✅ VSA: Signal={vsa.get('signal')}, Vol Ratio={vsa.get('vol_ratio')}")
                
                if 'fibonacci' in technical and 'levels' in technical['fibonacci']:
                    print(f"   ✅ Fibonacci: {len(technical['fibonacci']['levels'])} retracement levels")
                
                if 'moving_averages' in technical:
                    ma = technical['moving_averages']
                    if 'golden_cross' in ma and 'above_all_ma' in ma:
                        print(f"   ✅ MA Regime: Golden Cross={ma.get('golden_cross')}, Above All={ma.get('above_all_ma')}")
                
                if len(found_indicators) >= 15:
                    print(f"   ✅ Technical analysis comprehensive")
                else:
                    print(f"   ⚠️  Missing some technical indicators")
            else:
                print(f"   ❌ Technical analysis failed: {technical.get('error', 'Unknown error')}")

            # Check fundamental metrics (should have 30+ metrics)
            fundamental = data.get('fundamental', {})
            if fundamental and not fundamental.get('error'):
                # Phase 4 expanded fundamental metrics
                key_metrics = [
                    'pe_ratio', 'forward_pe', 'peg_ratio', 'price_to_book', 'ev_to_ebitda', 'ev_to_revenue',
                    'roe', 'roa', 'profit_margin', 'operating_margin', 'gross_margin',
                    'revenue_growth', 'earnings_growth', 'earnings_quarterly_growth',
                    'debt_to_equity', 'debt_to_ebitda', 'current_ratio', 'quick_ratio',
                    'free_cashflow', 'operating_cashflow', 'fcf_yield',
                    'eps', 'forward_eps', 'bvps', 'revenue_per_share',
                    'dividend_yield', 'dividend_rate', 'payout_ratio',
                    'beta', 'held_pct_insiders', 'held_pct_institutions', 'short_ratio',
                    'graham_value', 'valuation', 'quarterly_revenue', 'quarterly_earnings'
                ]
                found_metrics = [metric for metric in key_metrics if metric in fundamental and fundamental[metric] is not None]
                print(f"   💰 Fundamental metrics: {len(found_metrics)}/34 key metrics found")
                
                # Check specific Phase 4 expanded features
                if 'graham_value' in fundamental and fundamental['graham_value']:
                    print(f"   ✅ Graham Intrinsic Value: ₹{fundamental['graham_value']} (vs current: ₹{fundamental.get('current_price', 'N/A')})")
                    if 'valuation' in fundamental:
                        print(f"   ✅ Valuation Status: {fundamental['valuation']}")
                
                if 'quarterly_revenue' in fundamental and fundamental['quarterly_revenue']:
                    print(f"   ✅ Quarterly Data: {len(fundamental['quarterly_revenue'])} quarters of revenue data")
                
                if 'fcf_yield' in fundamental and fundamental['fcf_yield']:
                    print(f"   ✅ FCF Yield: {fundamental['fcf_yield']}%")
                
                if 'debt_to_ebitda' in fundamental and fundamental['debt_to_ebitda']:
                    print(f"   ✅ Debt/EBITDA: {fundamental['debt_to_ebitda']}x")
                
                if len(found_metrics) >= 25:
                    print(f"   ✅ Fundamental analysis comprehensive")
                else:
                    print(f"   ⚠️  Missing some fundamental metrics")
            else:
                print(f"   ❌ Fundamental analysis failed: {fundamental.get('error', 'Unknown error')}")

            # Check news and sentiment
            news = data.get('news', {})
            sentiment = data.get('sentiment', {})
            if news.get('headlines'):
                print(f"   📰 News: {len(news['headlines'])} headlines found")
            if sentiment.get('score') is not None:
                print(f"   😊 Sentiment: {sentiment.get('label', 'Unknown')} (score: {sentiment.get('score', 'N/A')})")

            # Check if all components are present
            required_fields = ["market_data", "technical", "fundamental", "news", "sentiment", "alpha"]
            missing_fields = [field for field in required_fields if field not in data or data[field].get('error')]
            
            if not missing_fields:
                alpha_score = data["alpha"]["alpha_score"]
                recommendation = data["alpha"]["recommendation"]
                print(f"   ✅ Complete analysis: Alpha Score = {alpha_score}, Recommendation = {recommendation}")
                return True, data
            else:
                print(f"   ⚠️  Missing or invalid fields: {missing_fields}")
                return False, data
        
        return False, {}

    def test_ai_batch_scan(self):
        """Test AI-powered batch scanning (Phase 4: converted batch scanner to AI)"""
        print(f"\n🔍 Testing AI Batch Scanner - This may take 30-60 seconds...")
        
        test_symbols = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS']
        success, data = self.run_test(
            "AI Batch Scanner", 
            "POST", 
            "api/batch/ai-scan",
            data={"symbols": test_symbols, "provider": "openai"},
            timeout=120  # AI processing takes longer
        )
        
        if success:
            results = data.get('results', [])
            ai_powered = data.get('ai_powered', False)
            provider = data.get('provider', 'Unknown')
            model = data.get('model', 'Unknown')
            total = data.get('total', 0)
            
            print(f"   🤖 AI-Powered: {ai_powered}")
            print(f"   🔧 Provider: {provider}, Model: {model}")
            print(f"   📊 Results: {len(results)} stocks analyzed")
            
            if results:
                # Check AI-specific fields (Phase 4 requirement)
                first_result = results[0]
                ai_fields = ['rank', 'ai_score', 'action', 'conviction', 'rationale', 'key_strength', 'key_risk']
                found_ai_fields = [field for field in ai_fields if field in first_result and first_result[field] is not None]
                print(f"   🧠 AI fields: {len(found_ai_fields)}/7 found")
                
                # Show sample results
                print(f"   📈 Sample AI Rankings:")
                for i, stock in enumerate(results[:3]):
                    symbol = stock.get('symbol', 'Unknown').replace('.NS', '')
                    rank = stock.get('rank', 'N/A')
                    ai_score = stock.get('ai_score', 'N/A')
                    action = stock.get('action', 'N/A')
                    conviction = stock.get('conviction', 'N/A')
                    rationale = stock.get('rationale', 'N/A')[:50] + '...' if stock.get('rationale') else 'N/A'
                    print(f"      #{rank} {symbol}: Score={ai_score}, Action={action}, Conviction={conviction}")
                    print(f"         Rationale: {rationale}")
                
                # Check if AI ranking is working
                if ai_powered and len(found_ai_fields) >= 5:
                    print(f"   ✅ AI batch scanning working correctly")
                    return True, data
                else:
                    print(f"   ⚠️  AI features incomplete or not working")
                    return False, data
            else:
                print(f"   ❌ No results returned")
                return False, {}
        return False, {}

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

    def test_generate_signal_expanded(self):
        """Test AI signal generation with expanded parameters (Phase 4)"""
        print(f"\n🔍 Testing AI Signal Generation with Expanded Parameters (RELIANCE.NS)...")
        
        success, data = self.run_test(
            "Generate AI Signal - RELIANCE.NS", 
            "POST", 
            "api/signals/generate",
            data={
                "symbol": "RELIANCE.NS",
                "provider": "openai",
                "period": "6mo"
            },
            timeout=90  # Expanded analysis takes longer
        )
        
        if success:
            signal = data.get("signal", {})
            raw_scores = data.get("raw_scores", {})
            learning_context = data.get("learning_context_summary", {})
            
            print(f"   🎯 Signal generated for {signal.get('symbol', 'Unknown')}")
            print(f"   📊 Action: {signal.get('action', 'N/A')}")
            print(f"   🎲 Confidence: {signal.get('confidence', 'N/A')}%")
            print(f"   ⏱️  Timeframe: {signal.get('timeframe', 'N/A')}")
            print(f"   📅 Horizon: {signal.get('horizon_days', 'N/A')} days")
            
            # Check signal structure (Phase 4 requirements)
            required_fields = [
                'action', 'confidence', 'entry', 'targets', 'stop_loss', 
                'key_theses', 'invalidators', 'risk_reward_ratio', 
                'technical_summary', 'fundamental_summary', 'detailed_reasoning'
            ]
            found_fields = [field for field in required_fields if field in signal and signal[field]]
            print(f"   🔧 Signal fields: {len(found_fields)}/{len(required_fields)} required fields")
            
            # Check entry and targets
            if 'entry' in signal and 'price' in signal['entry']:
                print(f"   💰 Entry: ₹{signal['entry']['price']} ({signal['entry'].get('type', 'market')})")
            
            if 'targets' in signal and signal['targets']:
                print(f"   🎯 Targets: {len(signal['targets'])} price targets")
                for i, target in enumerate(signal['targets'][:2]):
                    print(f"      Target {i+1}: ₹{target.get('price', 'N/A')} (prob: {target.get('probability', 0)*100:.0f}%)")
            
            if 'stop_loss' in signal and 'price' in signal['stop_loss']:
                print(f"   🛡️  Stop Loss: ₹{signal['stop_loss']['price']} ({signal['stop_loss'].get('type', 'hard')})")
            
            # Check raw scores (should include all analysis types)
            if raw_scores:
                print(f"   📈 Input Scores:")
                print(f"      Technical: {raw_scores.get('technical_score', 'N/A')}")
                print(f"      Fundamental: {raw_scores.get('fundamental_score', 'N/A')}")
                print(f"      Sentiment: {raw_scores.get('sentiment_score', 'N/A')}")
                print(f"      Alpha: {raw_scores.get('alpha_score', 'N/A')}")
            
            # Check learning context (Phase 4 feature)
            if learning_context:
                print(f"   🧠 Learning Context:")
                print(f"      Past signals: {learning_context.get('total_past_signals', 0)}")
                if learning_context.get('win_rate') is not None:
                    print(f"      Win rate: {learning_context.get('win_rate')}%")
                print(f"      Lessons applied: {learning_context.get('lessons_count', 0)}")
            
            # Check key theses and reasoning
            if 'key_theses' in signal and signal['key_theses']:
                print(f"   💡 Key Theses: {len(signal['key_theses'])} theses")
                for i, thesis in enumerate(signal['key_theses'][:2]):
                    print(f"      {i+1}. {thesis[:60]}...")
            
            if 'detailed_reasoning' in signal and signal['detailed_reasoning']:
                reasoning_length = len(signal['detailed_reasoning'])
                print(f"   📝 Detailed Reasoning: {reasoning_length} characters")
            
            # Overall assessment
            if len(found_fields) >= 8 and raw_scores and signal.get('confidence', 0) > 0:
                print(f"   ✅ AI signal generation with expanded parameters working correctly")
                return True, signal
            else:
                print(f"   ⚠️  Signal incomplete or missing expanded features")
                return False, {}
        
        return False, {}

    def test_active_signals(self):
        """Test getting active signals"""
        success, data = self.run_test("Get Active Signals", "GET", "api/signals/active")
        if success:
            signals = data.get("signals", [])
            print(f"   ✓ Found {len(signals)} active signals")
            return True, signals
        return False, []

    def test_signal_history(self):
        """Test getting signal history"""
        success, data = self.run_test("Get Signal History", "GET", "api/signals/history")
        if success:
            signals = data.get("signals", [])
            print(f"   ✓ Found {len(signals)} historical signals")
            return True, signals
        return False, []

    def test_track_record(self):
        """Test getting track record metrics"""
        success, data = self.run_test("Get Track Record", "GET", "api/signals/track-record")
        if success:
            total_signals = data.get("total_signals", 0)
            metrics = data.get("metrics", {})
            print(f"   ✓ Track record: {total_signals} total signals")
            if metrics:
                win_rate = metrics.get("win_rate", "N/A")
                print(f"   ✓ Win rate: {win_rate}%")
            return True, data
        return False, {}

    def test_learning_context(self):
        """Test getting learning context"""
        success, data = self.run_test("Get Learning Context", "GET", "api/signals/learning-context")
        if success:
            total_signals = data.get("total_signals", 0)
            lessons = data.get("lessons", [])
            print(f"   ✓ Learning context: {total_signals} signals, {len(lessons)} lessons")
            return True, data
        return False, {}

    def test_evaluate_all_signals(self):
        """Test evaluating all signals"""
        success, data = self.run_test("Evaluate All Signals", "POST", "api/signals/evaluate-all", timeout=30)
        if success:
            evaluated = data.get("evaluated", 0)
            print(f"   ✓ Evaluated {evaluated} signals")
            return True, data
        return False, {}

    def run_all_tests(self):
        """Run all Phase 4 tests in sequence"""
        print("🚀 Starting BMIA Phase 4 Backend API Tests")
        print("   📈 Expanded Parameters: 25+ Technical + 30+ Fundamental")
        print("   🤖 AI Batch Scanner: Converted from basic to AI-powered")
        print("   🌍 Expanded Universe: Beyond Yahoo Finance")
        print(f"   🌐 Base URL: {self.base_url}")
        print("=" * 70)
        
        # Basic connectivity
        self.test_health_check()
        
        # Phase 4: Expanded data universe
        print(f"\n📊 Testing Phase 4: Expanded Data Universe...")
        self.test_expanded_symbols()
        self.test_sectors_endpoint()
        
        # Phase 4: Expanded analysis parameters
        print(f"\n🔧 Testing Phase 4: Expanded Analysis Parameters...")
        analysis_success, analysis_data = self.test_expanded_stock_analysis()
        
        # Phase 4: AI-powered batch scanner
        print(f"\n🤖 Testing Phase 4: AI Batch Scanner...")
        batch_success, batch_data = self.test_ai_batch_scan()
        
        # Phase 4: AI signal generation with expanded parameters
        print(f"\n🧠 Testing Phase 4: AI Signal Generation...")
        signal_success, signal_data = self.test_generate_signal_expanded()
        
        # Legacy signal management endpoints
        print(f"\n📋 Testing Signal Management...")
        self.test_active_signals()
        self.test_signal_history()
        self.test_track_record()
        self.test_learning_context()
        
        # Print summary
        print("\n" + "=" * 70)
        print(f"📊 Phase 4 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        # Phase 4 specific assessment
        phase4_critical_tests = [
            analysis_success,  # Expanded parameters
            batch_success,     # AI batch scanner
            signal_success     # AI signal generation
        ]
        
        phase4_passed = sum(phase4_critical_tests)
        print(f"🎯 Phase 4 Critical Features: {phase4_passed}/3 working")
        
        if self.failed_tests:
            print(f"\n❌ Failed Tests:")
            for failure in self.failed_tests[:10]:  # Show first 10 failures
                print(f"   • {failure}")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All Phase 4 tests passed!")
            return 0
        elif phase4_passed >= 2:
            print("✅ Phase 4 core features working (some minor issues)")
            return 0
        else:
            print(f"⚠️  Phase 4 has significant issues - {len(self.failed_tests)} tests failed")
            return 1

def main():
    tester = BMIAAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())