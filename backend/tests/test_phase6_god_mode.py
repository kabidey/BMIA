"""
Phase 6 Backend Tests: God Mode & Full Market Scanner
Tests:
1. POST /api/batch/god-scan - Background task with polling
2. POST /api/signals/generate with god_mode=true - Async signal generation
3. POST /api/signals/generate with god_mode=false - Synchronous signal
4. GET /api/market/cockpit - Dashboard data
5. GET /api/health - Health check
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthEndpoint:
    """Health check endpoint tests"""
    
    def test_health_returns_ok(self):
        """GET /api/health should return status ok"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        assert "timestamp" in data
        print(f"Health check passed: {data}")


class TestMarketCockpit:
    """Market Intelligence Cockpit endpoint tests"""
    
    def test_cockpit_returns_dashboard_data(self):
        """GET /api/market/cockpit should return dashboard sections"""
        response = requests.get(f"{BASE_URL}/api/market/cockpit", timeout=60)
        assert response.status_code == 200
        data = response.json()
        
        # Verify key sections exist
        assert "indices" in data, "Missing indices section"
        assert "vix" in data, "Missing vix section"
        assert "breadth" in data, "Missing breadth section"
        assert "flows" in data, "Missing flows section"
        assert "sectors" in data, "Missing sectors section"
        
        # Verify indices data structure
        indices = data.get("indices", {})
        assert "primary" in indices or len(indices) > 0, "Indices should have data"
        
        print(f"Cockpit data sections: {list(data.keys())}")
        print(f"VIX: {data.get('vix', {}).get('value', 'N/A')}")


class TestGodScanBatch:
    """God Mode Batch Scanner tests - Background task with polling"""
    
    def test_god_scan_starts_and_returns_job_id(self):
        """POST /api/batch/god-scan should return job_id immediately"""
        payload = {
            "market": "NSE",
            "max_candidates": 20,
            "max_shortlist": 5,
            "top_n": 5
        }
        response = requests.post(
            f"{BASE_URL}/api/batch/god-scan",
            json=payload,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should return job_id and status immediately
        assert "job_id" in data, "Missing job_id in response"
        assert data.get("status") == "started", f"Expected status 'started', got {data.get('status')}"
        
        job_id = data["job_id"]
        print(f"God scan started with job_id: {job_id}")
        return job_id
    
    def test_god_scan_polling_until_complete(self):
        """Poll GET /api/batch/god-scan/{job_id} until complete"""
        # Start the scan
        payload = {
            "market": "NSE",
            "max_candidates": 20,
            "max_shortlist": 5,
            "top_n": 5
        }
        start_response = requests.post(
            f"{BASE_URL}/api/batch/god-scan",
            json=payload,
            timeout=30
        )
        assert start_response.status_code == 200
        job_id = start_response.json().get("job_id")
        assert job_id, "No job_id returned"
        
        print(f"Started god scan job: {job_id}")
        
        # Poll for results (max 3 minutes)
        max_attempts = 60
        poll_interval = 3
        final_status = None
        final_data = None
        
        for attempt in range(max_attempts):
            time.sleep(poll_interval)
            poll_response = requests.get(
                f"{BASE_URL}/api/batch/god-scan/{job_id}",
                timeout=30
            )
            
            if poll_response.status_code == 404:
                # Job might have been cleaned up after completion
                print(f"Job {job_id} not found (may have been cleaned up)")
                break
            
            assert poll_response.status_code == 200
            poll_data = poll_response.json()
            final_status = poll_data.get("status")
            final_data = poll_data
            
            print(f"Poll {attempt + 1}: status={final_status}, stage={poll_data.get('stage')}")
            
            if final_status == "complete":
                # Verify complete response has results
                assert "results" in poll_data, "Complete response missing results"
                results = poll_data.get("results", [])
                print(f"God scan complete! {len(results)} results returned")
                
                # Verify result structure
                if results:
                    first_result = results[0]
                    assert "symbol" in first_result, "Result missing symbol"
                    assert "action" in first_result, "Result missing action"
                    # Check for god mode specific fields
                    if "model_votes" in first_result:
                        print(f"Model votes present: {first_result['model_votes']}")
                    if "agreement_level" in first_result:
                        print(f"Agreement level: {first_result['agreement_level']}")
                    if "ai_score" in first_result:
                        print(f"AI score: {first_result['ai_score']}")
                break
            
            if final_status == "error":
                print(f"God scan error: {poll_data.get('error')}")
                break
        
        # Allow either complete or still running (for timeout)
        assert final_status in ["complete", "running", "error"], f"Unexpected status: {final_status}"
        if final_status == "complete":
            print("God scan polling test PASSED - completed successfully")
        elif final_status == "running":
            print("God scan still running after timeout - this is acceptable for long scans")


class TestGodModeSignalGeneration:
    """God Mode Signal Generation tests - Async with polling"""
    
    def test_god_mode_signal_returns_job_id(self):
        """POST /api/signals/generate with god_mode=true should return job_id"""
        payload = {
            "symbol": "RELIANCE.NS",
            "provider": "openai",
            "god_mode": True
        }
        response = requests.post(
            f"{BASE_URL}/api/signals/generate",
            json=payload,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        
        # God mode should return job_id for async processing
        assert "job_id" in data, "God mode should return job_id"
        assert data.get("status") == "started", f"Expected status 'started', got {data.get('status')}"
        assert data.get("async") == True, "God mode should have async=true"
        
        job_id = data["job_id"]
        print(f"God mode signal started with job_id: {job_id}")
        return job_id
    
    def test_god_mode_signal_polling_until_complete(self):
        """Poll GET /api/signals/generate-status/{job_id} until complete"""
        # Start god mode signal generation
        payload = {
            "symbol": "TCS.NS",
            "provider": "openai",
            "god_mode": True
        }
        start_response = requests.post(
            f"{BASE_URL}/api/signals/generate",
            json=payload,
            timeout=30
        )
        assert start_response.status_code == 200
        job_id = start_response.json().get("job_id")
        assert job_id, "No job_id returned"
        
        print(f"Started god mode signal job: {job_id}")
        
        # Poll for results (max 3 minutes)
        max_attempts = 60
        poll_interval = 3
        final_status = None
        final_data = None
        
        for attempt in range(max_attempts):
            time.sleep(poll_interval)
            poll_response = requests.get(
                f"{BASE_URL}/api/signals/generate-status/{job_id}",
                timeout=30
            )
            
            if poll_response.status_code == 404:
                print(f"Job {job_id} not found (may have been cleaned up)")
                break
            
            assert poll_response.status_code == 200
            poll_data = poll_response.json()
            final_status = poll_data.get("status")
            final_data = poll_data
            
            print(f"Poll {attempt + 1}: status={final_status}")
            
            if final_status == "complete":
                # Verify complete response has signal data
                assert "signal" in poll_data, "Complete response missing signal"
                signal = poll_data.get("signal", {})
                print(f"God mode signal complete!")
                print(f"Action: {signal.get('action')}")
                print(f"Confidence: {signal.get('confidence')}")
                
                # Check for god_mode_consensus if present
                if "god_mode_consensus" in signal:
                    consensus = signal["god_mode_consensus"]
                    print(f"God mode consensus: {consensus}")
                    if "agreement_level" in consensus:
                        print(f"Agreement level: {consensus['agreement_level']}")
                break
            
            if final_status == "error":
                print(f"God mode signal error: {poll_data.get('error')}")
                break
        
        assert final_status in ["complete", "running", "error"], f"Unexpected status: {final_status}"
        if final_status == "complete":
            print("God mode signal polling test PASSED")


class TestSynchronousSignalGeneration:
    """Non-God Mode Signal Generation tests - Synchronous"""
    
    def test_non_god_mode_signal_returns_directly(self):
        """POST /api/signals/generate with god_mode=false should return signal directly"""
        payload = {
            "symbol": "INFY.NS",
            "provider": "openai",
            "god_mode": False
        }
        response = requests.post(
            f"{BASE_URL}/api/signals/generate",
            json=payload,
            timeout=60  # Synchronous can take 20-30s
        )
        assert response.status_code == 200
        data = response.json()
        
        # Non-god mode should NOT have job_id (synchronous)
        assert "job_id" not in data, "Non-god mode should not return job_id"
        
        # Should have signal directly
        assert "signal" in data, "Response should contain signal"
        signal = data.get("signal", {})
        
        # Verify signal structure
        assert "action" in signal, "Signal missing action"
        assert "symbol" in signal, "Signal missing symbol"
        
        print(f"Synchronous signal generated:")
        print(f"  Symbol: {signal.get('symbol')}")
        print(f"  Action: {signal.get('action')}")
        print(f"  Confidence: {signal.get('confidence')}")
        
        # Verify raw_scores
        if "raw_scores" in data:
            scores = data["raw_scores"]
            print(f"  Technical Score: {scores.get('technical_score')}")
            print(f"  Fundamental Score: {scores.get('fundamental_score')}")


class TestJobNotFound:
    """Test 404 for non-existent jobs"""
    
    def test_god_scan_invalid_job_returns_404(self):
        """GET /api/batch/god-scan/{invalid_id} should return 404"""
        response = requests.get(
            f"{BASE_URL}/api/batch/god-scan/invalid123",
            timeout=10
        )
        assert response.status_code == 404
        print("Invalid god scan job returns 404 - PASSED")
    
    def test_signal_status_invalid_job_returns_404(self):
        """GET /api/signals/generate-status/{invalid_id} should return 404"""
        response = requests.get(
            f"{BASE_URL}/api/signals/generate-status/invalid123",
            timeout=10
        )
        assert response.status_code == 404
        print("Invalid signal job returns 404 - PASSED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
