"""
Iteration 15 Tests — Hardening of Batch Scanner, AI Signals, and Track Record

Tests:
1. Signal validation: _validate_signal_bounds correctly fixes BUY/SELL targets/stops
2. Signal validation: confidence clamped to 10-95, horizon_days clamped to 1-90
3. Signal validation: risk_reward_ratio computed from validated targets/stops
4. Track record: data_quality field with status, closed_count, stale_open_signals
5. Track record: metrics fields are sanitized (no NaN/Inf)
6. Active signals: sanitized with live_return_pct (no NaN/Inf)
7. Learning context: returns properly
8. Batch scanner: ThreadPoolExecutor and asyncio.wait_for timeout in code
9. Batch scanner: validate_fundamentals and validate_technical imports
10. Portfolio hardening: validate_fundamentals and validate_technical work correctly
"""
import pytest
import requests
import os
import sys
import math

# Add backend to path for direct imports
sys.path.insert(0, '/app/backend')

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://compliance-rag-agent.preview.emergentagent.com').rstrip('/')


class TestSignalValidation:
    """Test _validate_signal_bounds function directly"""

    def test_validate_signal_bounds_buy_target_below_entry(self):
        """BUY signal with target below entry should be adjusted upward"""
        from services.signal_service import _validate_signal_bounds, _safe_float

        signal = {
            "action": "BUY",
            "entry": {"price": 100.0},
            "targets": [{"price": 90.0, "label": "T1"}],  # Target BELOW entry - invalid for BUY
            "stop_loss": {"price": 95.0, "type": "hard"},  # Stop ABOVE entry - invalid for BUY
            "confidence": 200,  # Out of range (should be 10-95)
            "horizon_days": 500,  # Out of range (should be 1-90)
        }

        validated = _validate_signal_bounds(signal)

        # Target should be adjusted to at least entry * 1.02 = 102
        assert validated["targets"][0]["price"] >= 100.0, f"BUY target should be >= entry, got {validated['targets'][0]['price']}"
        
        # Stop loss should be adjusted to below entry (entry * 0.95 = 95)
        assert validated["stop_loss"]["price"] < 100.0, f"BUY stop should be < entry, got {validated['stop_loss']['price']}"
        
        # Confidence should be clamped to 95 (max)
        assert validated["confidence"] == 95, f"Confidence should be clamped to 95, got {validated['confidence']}"
        
        # Horizon should be clamped to 90 (max)
        assert validated["horizon_days"] == 90, f"Horizon should be clamped to 90, got {validated['horizon_days']}"

        print("✅ BUY signal validation: target adjusted upward, stop adjusted downward, confidence/horizon clamped")

    def test_validate_signal_bounds_sell_target_above_entry(self):
        """SELL signal with target above entry should be adjusted downward"""
        from services.signal_service import _validate_signal_bounds

        signal = {
            "action": "SELL",
            "entry": {"price": 100.0},
            "targets": [{"price": 110.0, "label": "T1"}],  # Target ABOVE entry - invalid for SELL
            "stop_loss": {"price": 95.0, "type": "hard"},  # Stop BELOW entry - invalid for SELL
            "confidence": 5,  # Below min (should be 10)
            "horizon_days": 0,  # Below min (should be 1)
        }

        validated = _validate_signal_bounds(signal)

        # Target should be adjusted to at most entry * 0.98 = 98
        assert validated["targets"][0]["price"] <= 100.0, f"SELL target should be <= entry, got {validated['targets'][0]['price']}"
        
        # Stop loss should be adjusted to above entry (entry * 1.05 = 105)
        assert validated["stop_loss"]["price"] > 100.0, f"SELL stop should be > entry, got {validated['stop_loss']['price']}"
        
        # Confidence should be clamped to 10 (min)
        assert validated["confidence"] == 10, f"Confidence should be clamped to 10, got {validated['confidence']}"
        
        # Horizon should be clamped to 1 (min)
        assert validated["horizon_days"] == 1, f"Horizon should be clamped to 1, got {validated['horizon_days']}"

        print("✅ SELL signal validation: target adjusted downward, stop adjusted upward, confidence/horizon clamped")

    def test_validate_signal_bounds_risk_reward_computed(self):
        """Risk/reward ratio should be computed from validated targets/stops"""
        from services.signal_service import _validate_signal_bounds

        signal = {
            "action": "BUY",
            "entry": {"price": 100.0},
            "targets": [{"price": 110.0, "label": "T1"}],  # Valid: 10% upside
            "stop_loss": {"price": 95.0, "type": "hard"},  # Valid: 5% downside
            "confidence": 70,
            "horizon_days": 30,
        }

        validated = _validate_signal_bounds(signal)

        # Risk/reward should be computed: reward=10, risk=5, ratio=1:2.0
        assert "risk_reward_ratio" in validated, "risk_reward_ratio should be computed"
        assert validated["risk_reward_ratio"].startswith("1:"), f"RR should be in format 1:X, got {validated['risk_reward_ratio']}"
        
        print(f"✅ Risk/reward ratio computed: {validated['risk_reward_ratio']}")

    def test_safe_float_handles_nan_inf(self):
        """_safe_float should replace NaN/Inf with default"""
        from services.signal_service import _safe_float

        assert _safe_float(float('nan'), 0.0) == 0.0, "NaN should return default"
        assert _safe_float(float('inf'), 0.0) == 0.0, "Inf should return default"
        assert _safe_float(float('-inf'), 0.0) == 0.0, "-Inf should return default"
        assert _safe_float(None, 5.0) == 5.0, "None should return default"
        assert _safe_float("invalid", 3.0) == 3.0, "Invalid string should return default"
        assert _safe_float(42.5, 0.0) == 42.5, "Valid float should be returned"

        print("✅ _safe_float correctly handles NaN/Inf/None/invalid values")


class TestTrackRecordHardening:
    """Test track record data quality and sanitization"""

    def test_track_record_has_data_quality_field(self):
        """GET /api/signals/track-record should return data_quality field"""
        response = requests.get(f"{BASE_URL}/api/signals/track-record")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "data_quality" in data, "Response should have data_quality field"
        
        dq = data["data_quality"]
        assert "status" in dq, "data_quality should have status field"
        assert dq["status"] in ["good", "insufficient", "no_data"], f"Invalid status: {dq['status']}"
        
        # Check for expected fields
        if dq["status"] != "no_data":
            assert "closed_count" in dq, "data_quality should have closed_count"
            assert "stale_open_signals" in dq, "data_quality should have stale_open_signals"
            assert "zero_return_closed" in dq, "data_quality should have zero_return_closed"

        print(f"✅ Track record data_quality: {dq}")

    def test_track_record_metrics_sanitized(self):
        """Track record metrics should not contain NaN/Inf"""
        response = requests.get(f"{BASE_URL}/api/signals/track-record")
        assert response.status_code == 200
        
        data = response.json()
        metrics = data.get("metrics", {})
        
        def check_no_nan_inf(obj, path=""):
            """Recursively check for NaN/Inf in nested structure"""
            if isinstance(obj, dict):
                for k, v in obj.items():
                    check_no_nan_inf(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    check_no_nan_inf(v, f"{path}[{i}]")
            elif isinstance(obj, float):
                assert not math.isnan(obj), f"NaN found at {path}"
                assert not math.isinf(obj), f"Inf found at {path}"

        check_no_nan_inf(metrics, "metrics")
        check_no_nan_inf(data.get("equity_curve", []), "equity_curve")
        check_no_nan_inf(data.get("by_action", {}), "by_action")
        check_no_nan_inf(data.get("by_sector", {}), "by_sector")
        check_no_nan_inf(data.get("by_confidence", {}), "by_confidence")
        check_no_nan_inf(data.get("streaks", {}), "streaks")

        print("✅ Track record metrics are sanitized (no NaN/Inf)")


class TestActiveSignalsHardening:
    """Test active signals sanitization"""

    def test_active_signals_sanitized(self):
        """GET /api/signals/active should return sanitized signals"""
        response = requests.get(f"{BASE_URL}/api/signals/active")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "signals" in data, "Response should have signals field"
        assert "total" in data, "Response should have total field"
        
        # Check each signal for NaN/Inf
        for sig in data["signals"]:
            for key in ["live_return_pct", "return_pct", "entry_price", "current_price"]:
                val = sig.get(key)
                if val is not None and isinstance(val, float):
                    assert not math.isnan(val), f"NaN found in signal {sig.get('symbol')} field {key}"
                    assert not math.isinf(val), f"Inf found in signal {sig.get('symbol')} field {key}"

        print(f"✅ Active signals sanitized: {data['total']} signals")


class TestLearningContext:
    """Test learning context endpoint"""

    def test_learning_context_returns_properly(self):
        """GET /api/signals/learning-context should return properly"""
        response = requests.get(f"{BASE_URL}/api/signals/learning-context")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Learning context should have these fields (may be empty if no signals)
        expected_fields = ["total_signals"]
        for field in expected_fields:
            assert field in data, f"Learning context should have {field}"

        print(f"✅ Learning context returned: total_signals={data.get('total_signals', 0)}")


class TestBatchScannerHardening:
    """Test batch scanner hardening (code structure, not actual scan)"""

    def test_scanner_uses_thread_pool_executor(self):
        """build_shortlist should use ThreadPoolExecutor with per-stock timeout"""
        import inspect
        from services.full_market_scanner import build_shortlist

        source = inspect.getsource(build_shortlist)
        
        assert "ThreadPoolExecutor" in source, "build_shortlist should use ThreadPoolExecutor"
        assert "concurrent.futures" in source or "from concurrent" in source or "import concurrent" in source, \
            "Should import concurrent.futures"
        assert "timeout" in source.lower(), "Should have timeout handling"

        print("✅ build_shortlist uses ThreadPoolExecutor with timeout")

    def test_god_mode_scan_has_asyncio_timeout(self):
        """god_mode_scan should have asyncio.wait_for timeout on LLM ensemble"""
        import inspect
        from services.full_market_scanner import god_mode_scan

        source = inspect.getsource(god_mode_scan)
        
        assert "asyncio.wait_for" in source, "god_mode_scan should use asyncio.wait_for"
        assert "timeout=120" in source or "timeout = 120" in source, "Should have 120s timeout"

        print("✅ god_mode_scan has asyncio.wait_for with 120s timeout")

    def test_scanner_imports_validation_functions(self):
        """build_shortlist should import and use validate_fundamentals/validate_technical"""
        import inspect
        from services.full_market_scanner import build_shortlist

        source = inspect.getsource(build_shortlist)
        
        assert "validate_fundamentals" in source, "Should use validate_fundamentals"
        assert "validate_technical" in source, "Should use validate_technical"
        assert "portfolio_hardening" in source, "Should import from portfolio_hardening"

        print("✅ build_shortlist imports validate_fundamentals and validate_technical")

    def test_scanner_attaches_factor_score(self):
        """god_mode_scan should attach factor_score to shortlist results"""
        import inspect
        from services.full_market_scanner import god_mode_scan

        source = inspect.getsource(god_mode_scan)
        
        assert "factor_score" in source, "Should compute/attach factor_score"
        assert "compute_factor_score" in source, "Should use compute_factor_score function"

        print("✅ god_mode_scan attaches factor_score to results")


class TestPortfolioHardeningFunctions:
    """Test portfolio hardening validation functions"""

    def test_validate_fundamentals_sanitizes_data(self):
        """validate_fundamentals should sanitize impossible values"""
        from services.portfolio_hardening import validate_fundamentals

        # Test with garbage data
        fund = {
            "pe_ratio": float('nan'),
            "roe": float('inf'),
            "dividend_yield": 500,  # Impossible - should be capped
            "debt_to_equity": -50,  # Impossible - should be None
            "beta": 100,  # Impossible - should be None
        }

        clean = validate_fundamentals(fund)
        
        assert clean.get("pe_ratio") is None, "NaN pe_ratio should be None"
        assert clean.get("roe") is None, "Inf roe should be None"
        assert clean.get("dividend_yield") is None, "500% dividend yield should be None"
        assert clean.get("debt_to_equity") is None, "Negative D/E should be None"
        assert clean.get("beta") is None, "Beta=100 should be None"

        print("✅ validate_fundamentals sanitizes impossible values")

    def test_validate_fundamentals_preserves_valid_data(self):
        """validate_fundamentals should preserve valid values"""
        from services.portfolio_hardening import validate_fundamentals

        fund = {
            "pe_ratio": 25.5,
            "roe": 18.3,
            "dividend_yield": 2.5,
            "debt_to_equity": 45.0,
            "beta": 1.2,
        }

        clean = validate_fundamentals(fund)
        
        assert clean.get("pe_ratio") == 25.5, "Valid pe_ratio should be preserved"
        assert clean.get("roe") == 18.3, "Valid roe should be preserved"
        assert clean.get("dividend_yield") == 2.5, "Valid dividend_yield should be preserved"
        assert clean.get("debt_to_equity") == 45.0, "Valid D/E should be preserved"
        assert clean.get("beta") == 1.2, "Valid beta should be preserved"

        print("✅ validate_fundamentals preserves valid values")

    def test_validate_technical_sanitizes_rsi(self):
        """validate_technical should sanitize RSI values"""
        from services.portfolio_hardening import validate_technical

        tech = {
            "rsi": {"current": 150},  # Invalid - RSI must be 0-100
        }

        clean = validate_technical(tech)
        assert clean["rsi"]["current"] is None, "RSI > 100 should be None"

        tech2 = {
            "rsi": {"current": float('nan')},
        }
        clean2 = validate_technical(tech2)
        assert clean2["rsi"]["current"] is None, "NaN RSI should be None"

        tech3 = {
            "rsi": {"current": 65.5},  # Valid
        }
        clean3 = validate_technical(tech3)
        assert clean3["rsi"]["current"] == 65.5, "Valid RSI should be preserved"

        print("✅ validate_technical sanitizes RSI values")


class TestPerformanceServiceSanitizer:
    """Test performance service _sf sanitizer"""

    def test_sf_sanitizer_handles_nan_inf(self):
        """_sf should replace NaN/Inf with default"""
        from services.performance_service import _sf

        assert _sf(float('nan'), 0.0) == 0.0, "NaN should return default"
        assert _sf(float('inf'), 0.0) == 0.0, "Inf should return default"
        assert _sf(float('-inf'), 0.0) == 0.0, "-Inf should return default"
        assert _sf(None, 5.0) == 5.0, "None should return default"
        assert _sf("invalid", 3.0) == 3.0, "Invalid string should return default"
        assert _sf(42.567, 0.0) == 42.57, "Valid float should be rounded to 2 decimals"

        print("✅ _sf sanitizer correctly handles NaN/Inf/None/invalid values")


class TestSignalsRoutesSanitization:
    """Test signals routes have sanitization"""

    def test_signals_routes_import_sanitization(self):
        """signals.py should have _sanitize_dict for JSON safety"""
        import inspect
        from routes import signals

        source = inspect.getsource(signals)
        
        assert "_sanitize_dict" in source or "_sanitize_float" in source, \
            "signals.py should have sanitization functions"
        assert "math.isnan" in source or "isnan" in source, \
            "Should check for NaN"
        assert "math.isinf" in source or "isinf" in source, \
            "Should check for Inf"

        print("✅ signals.py has sanitization functions for JSON safety")

    def test_gather_raw_data_uses_validation(self):
        """_gather_raw_data should use validate_fundamentals/validate_technical"""
        import inspect
        from routes.signals import _gather_raw_data

        source = inspect.getsource(_gather_raw_data)
        
        assert "validate_fundamentals" in source, "Should use validate_fundamentals"
        assert "validate_technical" in source, "Should use validate_technical"
        assert "portfolio_hardening" in source, "Should import from portfolio_hardening"

        print("✅ _gather_raw_data uses validation functions from portfolio_hardening")


class TestAPIEndpoints:
    """Test API endpoints return correct structure"""

    def test_health_endpoint(self):
        """GET /api/health should return ok"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print("✅ Health endpoint working")

    def test_track_record_endpoint_structure(self):
        """GET /api/signals/track-record should return complete structure"""
        response = requests.get(f"{BASE_URL}/api/signals/track-record")
        assert response.status_code == 200
        
        data = response.json()
        
        # Required top-level fields
        required_fields = ["total_signals", "open_signals", "closed_signals", "metrics", "data_quality"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Metrics structure
        metrics = data.get("metrics", {})
        metric_fields = ["win_rate", "avg_return", "expectancy", "profit_factor"]
        for field in metric_fields:
            assert field in metrics or metrics == {}, f"Missing metric field: {field}"

        print(f"✅ Track record structure complete: {data['total_signals']} total signals")

    def test_active_signals_endpoint_structure(self):
        """GET /api/signals/active should return correct structure"""
        response = requests.get(f"{BASE_URL}/api/signals/active")
        assert response.status_code == 200
        
        data = response.json()
        assert "signals" in data
        assert "total" in data
        assert isinstance(data["signals"], list)
        assert isinstance(data["total"], int)

        print(f"✅ Active signals structure correct: {data['total']} active")

    def test_learning_context_endpoint_structure(self):
        """GET /api/signals/learning-context should return correct structure"""
        response = requests.get(f"{BASE_URL}/api/signals/learning-context")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_signals" in data

        print(f"✅ Learning context structure correct: {data.get('total_signals', 0)} signals")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
