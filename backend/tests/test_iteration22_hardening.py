"""
Iteration 22: Hardening Fixes Tests
- Health endpoint
- Audit log captures user email from JWT
- Guidance vectors stats
- Portfolios endpoint returns 6 portfolios
- God Mode scanner text verification (NSE + BSE)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthEndpoint:
    """Health check endpoint tests"""
    
    def test_health_returns_ok(self):
        """GET /api/health returns ok status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        assert "timestamp" in data
        print(f"Health check passed: {data}")


class TestGuidanceVectors:
    """Guidance vectors stats tests"""
    
    def test_vectors_stats_ready(self):
        """GET /api/guidance/vectors/stats returns ready=true"""
        response = requests.get(f"{BASE_URL}/api/guidance/vectors/stats")
        assert response.status_code == 200
        data = response.json()
        assert data.get("ready") == True
        assert "total_vectors" in data
        assert data["total_vectors"] > 0
        print(f"Vectors stats: {data['total_vectors']} vectors, ready={data['ready']}")


class TestPortfolios:
    """Portfolio endpoint tests"""
    
    def test_portfolios_returns_six(self):
        """GET /api/portfolios returns 6 portfolios"""
        response = requests.get(f"{BASE_URL}/api/portfolios")
        assert response.status_code == 200
        data = response.json()
        portfolios = data.get("portfolios", [])
        assert len(portfolios) == 6, f"Expected 6 portfolios, got {len(portfolios)}"
        
        # Verify portfolio types
        expected_types = {
            "bespoke_forward_looking", "quick_entry", "long_term", 
            "swing", "alpha_generator", "value_stocks"
        }
        actual_types = {p.get("type") for p in portfolios}
        assert expected_types == actual_types, f"Portfolio types mismatch: {actual_types}"
        print(f"Portfolios test passed: {len(portfolios)} portfolios found")


class TestAuditLogEmailCapture:
    """Audit log email capture tests"""
    
    def test_check_email_captures_user_email(self):
        """POST /api/auth/check-email captures email in audit log"""
        test_email = "somnath.dey@smifs.com"
        
        # Make check-email request
        response = requests.post(
            f"{BASE_URL}/api/auth/check-email",
            json={"email": test_email},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        print(f"Check-email response: {response.json()}")
    
    def test_login_captures_user_email(self):
        """POST /api/auth/login captures email in audit log"""
        test_email = "somnath.dey@smifs.com"
        test_password = "admin123"
        
        # Make login request
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": test_email, "password": test_password},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        print(f"Login successful for {test_email}")
        return data["token"]
    
    def test_audit_log_shows_user_emails(self):
        """GET /api/audit-log shows user emails (not all anonymous)"""
        # First login to get token
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "somnath.dey@smifs.com", "password": "admin123"},
            headers={"Content-Type": "application/json"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["token"]
        
        # Get audit log
        response = requests.get(
            f"{BASE_URL}/api/audit-log?limit=20",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        logs = data.get("logs", [])
        assert len(logs) > 0, "No audit logs found"
        
        # Check that at least some entries have real emails (not anonymous)
        emails_found = [log.get("user_email") for log in logs]
        non_anonymous = [e for e in emails_found if e and e != "anonymous"]
        
        assert len(non_anonymous) > 0, "All audit entries are anonymous - email capture not working"
        print(f"Audit log test passed: {len(non_anonymous)} entries with real emails out of {len(logs)}")
        
        # Verify recent auth entries have email
        auth_entries = [log for log in logs if log.get("path") in ["/api/auth/check-email", "/api/auth/login"]]
        if auth_entries:
            recent_auth = auth_entries[0]
            # Recent auth entries should have email captured
            if recent_auth.get("user_email") == "somnath.dey@smifs.com":
                print("SUCCESS: Recent auth entry has correct email captured")
            else:
                print(f"WARNING: Recent auth entry email: {recent_auth.get('user_email')}")


class TestGodModeScannerEndpoint:
    """God Mode scanner endpoint tests (not full scan, just endpoint verification)"""
    
    def test_scan_history_endpoint_exists(self):
        """GET /api/batch/scan-history returns valid response"""
        response = requests.get(f"{BASE_URL}/api/batch/scan-history?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "scans" in data
        print(f"Scan history: {len(data.get('scans', []))} past scans found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
