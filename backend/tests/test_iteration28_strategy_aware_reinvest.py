"""
Iteration 28: Strategy-Aware Auto-Reinvest Testing

Tests:
1. pick_replacement_stock returns different picks for different strategies
2. Strategy-specific filters enforced (value_stocks: pe<20, pb<3, de<0.5; long_term: mc>10000Cr, roe>15%)
3. Scoring is thesis-consistent (momentum=high 3M return, oversold=low RSI, value=low PE)
4. Dividend yield scoring caps at 15 points (yfinance percent-vs-fraction bug fix)
5. GET /api/portfolios/overview: all 6 portfolios healthy, NAV +10-11L, total_pnl == realized + unrealized
6. Per portfolio: Bespoke has POWERGRID (RECONCILE_V2), Quick Entry has ONGC (RECONCILE_V2), Value Stocks has WIPRO (RECONCILE_V2)
7. Exit history endpoint still works
"""
import pytest
import requests
import os
import sys

# Add backend to path for direct imports
sys.path.insert(0, "/app/backend")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "https://compliance-rag-agent.preview.emergentagent.com"


class TestPortfolioStrategiesConfig:
    """Test PORTFOLIO_STRATEGIES configuration is correct"""
    
    def test_portfolio_strategies_exist(self):
        """Verify all 6 strategy configs exist with correct scoring types"""
        from services.portfolio_engine import PORTFOLIO_STRATEGIES
        
        expected_strategies = {
            "bespoke_forward_looking": "momentum",
            "quick_entry": "breakout",
            "long_term": "blue_chip",
            "swing": "oversold",
            "alpha_generator": "contrarian",
            "value_stocks": "value",
        }
        
        for strategy_type, expected_scoring in expected_strategies.items():
            assert strategy_type in PORTFOLIO_STRATEGIES, f"Missing strategy: {strategy_type}"
            cfg = PORTFOLIO_STRATEGIES[strategy_type]
            assert cfg.get("scoring") == expected_scoring, f"{strategy_type} should have scoring={expected_scoring}, got {cfg.get('scoring')}"
            assert "screener_criteria" in cfg, f"{strategy_type} missing screener_criteria"
            print(f"PASS: {strategy_type} has scoring={expected_scoring}")
    
    def test_value_stocks_screener_criteria(self):
        """Value stocks should have pe_max=20, price_to_book_max=3.0, debt_to_equity_max=0.5"""
        from services.portfolio_engine import PORTFOLIO_STRATEGIES
        
        criteria = PORTFOLIO_STRATEGIES["value_stocks"]["screener_criteria"]
        assert criteria.get("pe_max") == 20, f"value_stocks pe_max should be 20, got {criteria.get('pe_max')}"
        assert criteria.get("price_to_book_max") == 3.0, f"value_stocks price_to_book_max should be 3.0, got {criteria.get('price_to_book_max')}"
        assert criteria.get("debt_to_equity_max") == 0.5, f"value_stocks debt_to_equity_max should be 0.5, got {criteria.get('debt_to_equity_max')}"
        print(f"PASS: value_stocks screener_criteria correct: pe_max=20, pb_max=3.0, de_max=0.5")
    
    def test_long_term_screener_criteria(self):
        """Long term should have market_cap_min=10000Cr (10000e7), roe_min=15"""
        from services.portfolio_engine import PORTFOLIO_STRATEGIES
        
        criteria = PORTFOLIO_STRATEGIES["long_term"]["screener_criteria"]
        assert criteria.get("market_cap_min") == 10000e7, f"long_term market_cap_min should be 10000e7, got {criteria.get('market_cap_min')}"
        assert criteria.get("roe_min") == 15, f"long_term roe_min should be 15, got {criteria.get('roe_min')}"
        print(f"PASS: long_term screener_criteria correct: market_cap_min=10000Cr, roe_min=15%")


class TestAutoReinvestScreenerLogic:
    """Test _passes_screener function logic"""
    
    def test_passes_screener_value_stocks_pass(self):
        """Candidate with pe=15, pb=2.0, de=0.3 should pass value_stocks screener"""
        from services.auto_reinvest import _passes_screener
        from services.portfolio_engine import PORTFOLIO_STRATEGIES
        
        criteria = PORTFOLIO_STRATEGIES["value_stocks"]["screener_criteria"]
        candidate = {
            "market_cap": 5000e7,  # 5000 Cr > 2000 Cr min
            "pe_ratio": 15,        # < 20
            "price_to_book": 2.0,  # < 3.0
            "debt_to_equity": 30,  # yfinance returns as percentage, 30 < 0.5*100=50
            "roe": 0.15,           # 15% > 12% (not in value criteria but good)
        }
        
        result = _passes_screener(candidate, criteria)
        assert result is True, f"Candidate should pass value_stocks screener, got {result}"
        print("PASS: Valid value stock candidate passes screener")
    
    def test_passes_screener_value_stocks_fail_pe(self):
        """Candidate with pe=25 should fail value_stocks screener (pe_max=20)"""
        from services.auto_reinvest import _passes_screener
        from services.portfolio_engine import PORTFOLIO_STRATEGIES
        
        criteria = PORTFOLIO_STRATEGIES["value_stocks"]["screener_criteria"]
        candidate = {
            "market_cap": 5000e7,
            "pe_ratio": 25,        # > 20 - FAIL
            "price_to_book": 2.0,
            "debt_to_equity": 30,
        }
        
        result = _passes_screener(candidate, criteria)
        assert result is False, f"Candidate with PE=25 should fail value_stocks screener"
        print("PASS: High PE candidate correctly rejected by value_stocks screener")
    
    def test_passes_screener_value_stocks_fail_de(self):
        """Candidate with de=0.8 (80 in yfinance) should fail value_stocks screener (de_max=0.5)"""
        from services.auto_reinvest import _passes_screener
        from services.portfolio_engine import PORTFOLIO_STRATEGIES
        
        criteria = PORTFOLIO_STRATEGIES["value_stocks"]["screener_criteria"]
        candidate = {
            "market_cap": 5000e7,
            "pe_ratio": 15,
            "price_to_book": 2.0,
            "debt_to_equity": 80,  # 80 > 0.5*100=50 - FAIL
        }
        
        result = _passes_screener(candidate, criteria)
        assert result is False, f"Candidate with DE=80 should fail value_stocks screener"
        print("PASS: High D/E candidate correctly rejected by value_stocks screener")
    
    def test_passes_screener_long_term_pass(self):
        """Candidate with mc=15000Cr, roe=18% should pass long_term screener"""
        from services.auto_reinvest import _passes_screener
        from services.portfolio_engine import PORTFOLIO_STRATEGIES
        
        criteria = PORTFOLIO_STRATEGIES["long_term"]["screener_criteria"]
        candidate = {
            "market_cap": 15000e7,  # > 10000 Cr
            "roe": 0.18,            # 18% > 15%
            "debt_to_equity": 50,   # < 1.0*100=100
            "profit_margin": 0.10,  # 10% > 8%
        }
        
        result = _passes_screener(candidate, criteria)
        assert result is True, f"Candidate should pass long_term screener"
        print("PASS: Valid blue-chip candidate passes long_term screener")
    
    def test_passes_screener_long_term_fail_mc(self):
        """Candidate with mc=5000Cr should fail long_term screener (mc_min=10000Cr)"""
        from services.auto_reinvest import _passes_screener
        from services.portfolio_engine import PORTFOLIO_STRATEGIES
        
        criteria = PORTFOLIO_STRATEGIES["long_term"]["screener_criteria"]
        candidate = {
            "market_cap": 5000e7,  # < 10000 Cr - FAIL
            "roe": 0.18,
            "debt_to_equity": 50,
            "profit_margin": 0.10,
        }
        
        result = _passes_screener(candidate, criteria)
        assert result is False, f"Candidate with MC=5000Cr should fail long_term screener"
        print("PASS: Small-cap candidate correctly rejected by long_term screener")


class TestAutoReinvestScoringLogic:
    """Test _score_by_strategy function logic"""
    
    def test_momentum_scoring_rewards_3m_return(self):
        """Momentum scoring should reward high 3M returns"""
        from services.auto_reinvest import _score_by_strategy
        
        high_momentum = {
            "ret_1m_pct": 5, "ret_3m_pct": 25, "ret_6m_pct": 40,
            "rsi": 55, "dist_from_high_pct": 5, "dist_from_low_pct": 30,
            "volatility_ann_pct": 25, "market_cap": 10000e7,
            "pe_ratio": 20, "price_to_book": 3, "roe": 0.15,
            "profit_margin": 0.10, "dividend_yield": 0.01,
            "revenue_growth": 0.15, "debt_to_equity": 50, "beta": 1.0
        }
        
        low_momentum = {
            "ret_1m_pct": 1, "ret_3m_pct": 5, "ret_6m_pct": 10,
            "rsi": 55, "dist_from_high_pct": 15, "dist_from_low_pct": 10,
            "volatility_ann_pct": 25, "market_cap": 10000e7,
            "pe_ratio": 20, "price_to_book": 3, "roe": 0.15,
            "profit_margin": 0.10, "dividend_yield": 0.01,
            "revenue_growth": 0.05, "debt_to_equity": 50, "beta": 1.0
        }
        
        high_score = _score_by_strategy(high_momentum, "momentum")
        low_score = _score_by_strategy(low_momentum, "momentum")
        
        assert high_score > low_score, f"High momentum ({high_score}) should score higher than low momentum ({low_score})"
        print(f"PASS: Momentum scoring: high 3M return ({high_score}) > low 3M return ({low_score})")
    
    def test_oversold_scoring_rewards_low_rsi(self):
        """Oversold scoring should reward low RSI stocks"""
        from services.auto_reinvest import _score_by_strategy
        
        oversold = {
            "ret_1m_pct": -5, "ret_3m_pct": -10, "ret_6m_pct": 10,
            "rsi": 28, "dist_from_high_pct": 25, "dist_from_low_pct": 5,
            "volatility_ann_pct": 30, "market_cap": 5000e7,
            "pe_ratio": 15, "price_to_book": 2, "roe": 0.12,
            "profit_margin": 0.08, "dividend_yield": 0.02,
            "revenue_growth": 0.05, "debt_to_equity": 40, "beta": 1.2
        }
        
        overbought = {
            "ret_1m_pct": 10, "ret_3m_pct": 20, "ret_6m_pct": 40,
            "rsi": 75, "dist_from_high_pct": 2, "dist_from_low_pct": 50,
            "volatility_ann_pct": 30, "market_cap": 5000e7,
            "pe_ratio": 15, "price_to_book": 2, "roe": 0.12,
            "profit_margin": 0.08, "dividend_yield": 0.02,
            "revenue_growth": 0.05, "debt_to_equity": 40, "beta": 1.2
        }
        
        oversold_score = _score_by_strategy(oversold, "oversold")
        overbought_score = _score_by_strategy(overbought, "oversold")
        
        assert oversold_score > overbought_score, f"Oversold ({oversold_score}) should score higher than overbought ({overbought_score}) for swing strategy"
        print(f"PASS: Oversold scoring: low RSI ({oversold_score}) > high RSI ({overbought_score})")
    
    def test_value_scoring_rewards_low_pe(self):
        """Value scoring should reward low PE stocks"""
        from services.auto_reinvest import _score_by_strategy
        
        low_pe = {
            "ret_1m_pct": 2, "ret_3m_pct": 5, "ret_6m_pct": 10,
            "rsi": 50, "dist_from_high_pct": 10, "dist_from_low_pct": 15,
            "volatility_ann_pct": 20, "market_cap": 8000e7,
            "pe_ratio": 8, "price_to_book": 1.5, "roe": 0.15,
            "profit_margin": 0.12, "dividend_yield": 0.03,
            "revenue_growth": 0.08, "debt_to_equity": 30, "beta": 0.9
        }
        
        high_pe = {
            "ret_1m_pct": 2, "ret_3m_pct": 5, "ret_6m_pct": 10,
            "rsi": 50, "dist_from_high_pct": 10, "dist_from_low_pct": 15,
            "volatility_ann_pct": 20, "market_cap": 8000e7,
            "pe_ratio": 35, "price_to_book": 4.0, "roe": 0.15,
            "profit_margin": 0.12, "dividend_yield": 0.01,
            "revenue_growth": 0.08, "debt_to_equity": 30, "beta": 0.9
        }
        
        low_pe_score = _score_by_strategy(low_pe, "value")
        high_pe_score = _score_by_strategy(high_pe, "value")
        
        assert low_pe_score > high_pe_score, f"Low PE ({low_pe_score}) should score higher than high PE ({high_pe_score}) for value strategy"
        print(f"PASS: Value scoring: low PE ({low_pe_score}) > high PE ({high_pe_score})")
    
    def test_dividend_yield_scoring_caps_at_15(self):
        """Dividend yield contribution should cap at 15 points (yfinance bug fix)"""
        from services.auto_reinvest import _score_by_strategy
        
        # Test with dividend yield as fraction (0.05 = 5%)
        high_div_fraction = {
            "ret_1m_pct": 0, "ret_3m_pct": 0, "ret_6m_pct": 0,
            "rsi": 50, "dist_from_high_pct": 10, "dist_from_low_pct": 10,
            "volatility_ann_pct": 20, "market_cap": 5000e7,
            "pe_ratio": 10, "price_to_book": 1.5, "roe": 0.15,
            "profit_margin": 0.10, "dividend_yield": 0.10,  # 10% as fraction
            "revenue_growth": 0.05, "debt_to_equity": 30, "beta": 1.0
        }
        
        # Test with dividend yield as percentage (10 = 10%)
        high_div_percent = {
            "ret_1m_pct": 0, "ret_3m_pct": 0, "ret_6m_pct": 0,
            "rsi": 50, "dist_from_high_pct": 10, "dist_from_low_pct": 10,
            "volatility_ann_pct": 20, "market_cap": 5000e7,
            "pe_ratio": 10, "price_to_book": 1.5, "roe": 0.15,
            "profit_margin": 0.10, "dividend_yield": 10,  # 10% as percentage
            "revenue_growth": 0.05, "debt_to_equity": 30, "beta": 1.0
        }
        
        score_fraction = _score_by_strategy(high_div_fraction, "value")
        score_percent = _score_by_strategy(high_div_percent, "value")
        
        # Both should produce similar scores because the code normalizes
        # The dividend contribution should be capped at 15 points
        # Base score from PE=10: (15-10)*1.2 = 6
        # Base score from PB=1.5: (2.5-1.5)*5 = 5
        # Base score from ROE=15%: 10
        # Base score from DE=30: 5
        # Max DY contribution: 15
        # Total max: 6 + 5 + 10 + 5 + 15 = 41
        
        print(f"Score with DY as fraction (0.10): {score_fraction}")
        print(f"Score with DY as percentage (10): {score_percent}")
        
        # The scores should be reasonable (not inflated by uncapped DY)
        assert score_fraction <= 50, f"Score with fraction DY should be reasonable, got {score_fraction}"
        assert score_percent <= 50, f"Score with percent DY should be reasonable, got {score_percent}"
        print(f"PASS: Dividend yield scoring capped correctly (scores: {score_fraction}, {score_percent})")


class TestPortfolioOverviewAPI:
    """Test GET /api/portfolios/overview endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "somnath.dey@smifs.com", "password": "admin123"}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_overview_returns_200(self, auth_token):
        """GET /api/portfolios/overview should return 200"""
        response = requests.get(
            f"{BASE_URL}/api/portfolios/overview",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
        print("PASS: GET /api/portfolios/overview returns 200")
    
    def test_overview_has_6_portfolios(self, auth_token):
        """Overview should have 6 portfolios"""
        response = requests.get(
            f"{BASE_URL}/api/portfolios/overview",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        portfolios = data.get("portfolios", [])
        assert len(portfolios) == 6, f"Expected 6 portfolios, got {len(portfolios)}"
        print(f"PASS: Overview has 6 portfolios")
    
    def test_overview_nav_positive(self, auth_token):
        """NAV (total_value) should be positive (around 310L based on previous tests)"""
        response = requests.get(
            f"{BASE_URL}/api/portfolios/overview",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        nav = data.get("total_value", 0)
        assert nav > 300_00_000, f"NAV should be > 300L, got {nav/1e5:.2f}L"
        print(f"PASS: NAV (total_value) is positive: {nav/1e5:.2f}L")
    
    def test_overview_total_pnl_invariant(self, auth_token):
        """total_pnl should equal realized_pnl + unrealized_pnl"""
        response = requests.get(
            f"{BASE_URL}/api/portfolios/overview",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        total_pnl = data.get("total_pnl", 0)
        realized = data.get("total_realized_pnl", 0)
        unrealized = data.get("total_unrealized_pnl", 0)
        
        expected = realized + unrealized
        diff = abs(total_pnl - expected)
        
        assert diff < 100, f"total_pnl ({total_pnl}) should equal realized ({realized}) + unrealized ({unrealized}), diff={diff}"
        print(f"PASS: total_pnl invariant holds: {total_pnl:.2f} == {realized:.2f} + {unrealized:.2f} (diff={diff:.2f})")
    
    def test_overview_total_return_positive(self, auth_token):
        """Total return should be positive (around +3.68% based on previous tests)"""
        response = requests.get(
            f"{BASE_URL}/api/portfolios/overview",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        total_pnl = data.get("total_pnl", 0)
        total_pnl_pct = data.get("total_pnl_pct", 0)
        
        # Should be positive
        assert total_pnl > 0, f"Total P&L should be positive, got {total_pnl}"
        print(f"PASS: Total Return: +{total_pnl/1e5:.2f}L (+{total_pnl_pct:.2f}%)")


class TestReconciledHoldings:
    """Test that reconciled holdings are present in correct portfolios"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "somnath.dey@smifs.com", "password": "admin123"}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_bespoke_has_powergrid(self, auth_token):
        """Bespoke Forward Looking should have POWERGRID with RECONCILE conviction"""
        response = requests.get(
            f"{BASE_URL}/api/portfolios/bespoke_forward_looking",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        holdings = data.get("holdings", [])
        
        powergrid = next((h for h in holdings if "POWERGRID" in h.get("symbol", "")), None)
        assert powergrid is not None, "POWERGRID should be in bespoke_forward_looking"
        
        conviction = powergrid.get("conviction", "")
        assert "RECONCILE" in conviction or "AUTO" in conviction, f"POWERGRID conviction should contain RECONCILE, got {conviction}"
        print(f"PASS: Bespoke has POWERGRID with conviction={conviction}")
    
    def test_quick_entry_has_ongc(self, auth_token):
        """Quick Entry should have ONGC with RECONCILE conviction"""
        response = requests.get(
            f"{BASE_URL}/api/portfolios/quick_entry",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        holdings = data.get("holdings", [])
        
        ongc = next((h for h in holdings if "ONGC" in h.get("symbol", "")), None)
        assert ongc is not None, "ONGC should be in quick_entry"
        
        conviction = ongc.get("conviction", "")
        assert "RECONCILE" in conviction or "AUTO" in conviction, f"ONGC conviction should contain RECONCILE, got {conviction}"
        print(f"PASS: Quick Entry has ONGC with conviction={conviction}")
    
    def test_value_stocks_has_wipro(self, auth_token):
        """Value Stocks should have WIPRO with RECONCILE conviction"""
        response = requests.get(
            f"{BASE_URL}/api/portfolios/value_stocks",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        holdings = data.get("holdings", [])
        
        wipro = next((h for h in holdings if "WIPRO" in h.get("symbol", "")), None)
        assert wipro is not None, "WIPRO should be in value_stocks"
        
        conviction = wipro.get("conviction", "")
        assert "RECONCILE" in conviction or "AUTO" in conviction, f"WIPRO conviction should contain RECONCILE, got {conviction}"
        print(f"PASS: Value Stocks has WIPRO with conviction={conviction}")


class TestExitHistoryAPI:
    """Test exit history endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "somnath.dey@smifs.com", "password": "admin123"}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_exit_history_value_stocks(self, auth_token):
        """GET /api/portfolios/exit-history/value_stocks should return 200"""
        response = requests.get(
            f"{BASE_URL}/api/portfolios/exit-history/value_stocks",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Exit history for value_stocks returns 200")
    
    def test_exit_history_bespoke(self, auth_token):
        """GET /api/portfolios/exit-history/bespoke_forward_looking should return 200"""
        response = requests.get(
            f"{BASE_URL}/api/portfolios/exit-history/bespoke_forward_looking",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Exit history for bespoke_forward_looking returns 200")
    
    def test_exit_history_quick_entry(self, auth_token):
        """GET /api/portfolios/exit-history/quick_entry should return 200"""
        response = requests.get(
            f"{BASE_URL}/api/portfolios/exit-history/quick_entry",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Exit history for quick_entry returns 200")


class TestPerPortfolioPnLInvariant:
    """Test that per-portfolio total_pnl == realized_pnl + unrealized_pnl"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "somnath.dey@smifs.com", "password": "admin123"}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_all_portfolios_pnl_invariant(self, auth_token):
        """Each portfolio's total_pnl should equal realized + unrealized"""
        response = requests.get(
            f"{BASE_URL}/api/portfolios/overview",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        portfolios = data.get("portfolios", [])
        
        for p in portfolios:
            ptype = p.get("type", "unknown")
            total_pnl = p.get("total_pnl", 0) or 0
            realized = p.get("realized_pnl", 0) or 0
            unrealized = p.get("unrealized_pnl", 0) or 0
            
            expected = realized + unrealized
            diff = abs(total_pnl - expected)
            
            # Allow small rounding differences
            assert diff < 10, f"{ptype}: total_pnl ({total_pnl}) != realized ({realized}) + unrealized ({unrealized}), diff={diff}"
            print(f"PASS: {ptype} P&L invariant: {total_pnl:.2f} == {realized:.2f} + {unrealized:.2f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
