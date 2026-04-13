"""
Iteration 14: LSTM + Monte Carlo Simulation Engine Tests
Tests the new forward simulation feature with:
- LSTM neural network return forecasting
- 10,000 Monte Carlo GBM paths
- Fan charts, distribution histograms, risk metrics
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# All 6 strategy types to test
STRATEGY_TYPES = [
    'value_stocks',
    'long_term',
    'bespoke_forward_looking',
    'quick_entry',
    'swing',
    'alpha_generator'
]


class TestSimulationEndpoints:
    """Test GET /api/portfolios/simulation/{strategy_type} for all strategies"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def test_health_check(self):
        """Verify API is accessible"""
        response = self.session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print("✅ Health check passed")

    @pytest.mark.parametrize("strategy_type", STRATEGY_TYPES)
    def test_simulation_endpoint_returns_complete(self, strategy_type):
        """Test simulation endpoint returns status='complete' for cached data"""
        response = self.session.get(f"{BASE_URL}/api/portfolios/simulation/{strategy_type}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Should be complete (cached) or computing
        status = data.get("status")
        assert status in ["complete", "computing"], f"Unexpected status: {status}"
        
        if status == "complete":
            print(f"✅ {strategy_type}: Simulation complete")
        else:
            print(f"⏳ {strategy_type}: Simulation computing (not cached yet)")

    @pytest.mark.parametrize("strategy_type", STRATEGY_TYPES)
    def test_simulation_has_lstm_forecast(self, strategy_type):
        """Test simulation response contains lstm_forecast with expected fields"""
        response = self.session.get(f"{BASE_URL}/api/portfolios/simulation/{strategy_type}")
        assert response.status_code == 200
        data = response.json()
        
        if data.get("status") == "computing":
            pytest.skip(f"{strategy_type} simulation still computing")
        
        lstm = data.get("lstm_forecast")
        assert lstm is not None, "Missing lstm_forecast"
        
        # Check method is 'lstm' or 'historical_fallback'
        method = lstm.get("method")
        assert method in ["lstm", "historical_fallback"], f"Unexpected method: {method}"
        
        # Check annualized expected return exists
        ann_return = lstm.get("annualized_expected_return_pct")
        assert ann_return is not None, "Missing annualized_expected_return_pct"
        assert isinstance(ann_return, (int, float)), "annualized_expected_return_pct should be numeric"
        
        # LSTM returns should be clamped to reasonable bounds (not >100% annualized)
        assert -100 <= ann_return <= 100, f"LSTM return {ann_return}% exceeds reasonable bounds"
        
        # Check volatility
        ann_vol = lstm.get("annualized_volatility_pct")
        assert ann_vol is not None, "Missing annualized_volatility_pct"
        assert ann_vol > 0, "Volatility should be positive"
        
        print(f"✅ {strategy_type}: LSTM forecast - method={method}, E[R]={ann_return}%, vol={ann_vol}%")

    @pytest.mark.parametrize("strategy_type", STRATEGY_TYPES)
    def test_simulation_has_fan_chart(self, strategy_type):
        """Test simulation response contains monte_carlo.fan_chart with weekly data points"""
        response = self.session.get(f"{BASE_URL}/api/portfolios/simulation/{strategy_type}")
        assert response.status_code == 200
        data = response.json()
        
        if data.get("status") == "computing":
            pytest.skip(f"{strategy_type} simulation still computing")
        
        mc = data.get("monte_carlo")
        assert mc is not None, "Missing monte_carlo"
        
        fan_chart = mc.get("fan_chart")
        assert fan_chart is not None, "Missing fan_chart"
        assert isinstance(fan_chart, list), "fan_chart should be a list"
        
        # Should have ~52 weekly data points (252 days / 5 days per week)
        assert len(fan_chart) >= 40, f"Expected ~52 weekly points, got {len(fan_chart)}"
        
        # Check first data point has required percentile fields
        first_point = fan_chart[0]
        required_fields = ["day", "week", "p5", "p25", "p50", "p75", "p95", "mean"]
        for field in required_fields:
            assert field in first_point, f"Missing field '{field}' in fan_chart point"
        
        # Verify percentiles are in correct order (p5 < p25 < p50 < p75 < p95)
        assert first_point["p5"] <= first_point["p25"] <= first_point["p50"] <= first_point["p75"] <= first_point["p95"], \
            "Percentiles not in correct order"
        
        print(f"✅ {strategy_type}: Fan chart has {len(fan_chart)} weekly points with p5/p25/p50/p75/p95/mean")

    @pytest.mark.parametrize("strategy_type", STRATEGY_TYPES)
    def test_simulation_has_distribution_chart(self, strategy_type):
        """Test simulation response contains monte_carlo.distribution_chart (histogram)"""
        response = self.session.get(f"{BASE_URL}/api/portfolios/simulation/{strategy_type}")
        assert response.status_code == 200
        data = response.json()
        
        if data.get("status") == "computing":
            pytest.skip(f"{strategy_type} simulation still computing")
        
        mc = data.get("monte_carlo")
        assert mc is not None, "Missing monte_carlo"
        
        dist_chart = mc.get("distribution_chart")
        assert dist_chart is not None, "Missing distribution_chart"
        assert isinstance(dist_chart, list), "distribution_chart should be a list"
        assert len(dist_chart) > 10, f"Expected histogram bins, got {len(dist_chart)}"
        
        # Check histogram bin structure
        first_bin = dist_chart[0]
        assert "return_pct" in first_bin, "Missing return_pct in distribution bin"
        assert "frequency" in first_bin, "Missing frequency in distribution bin"
        assert isinstance(first_bin["frequency"], int), "frequency should be integer"
        
        print(f"✅ {strategy_type}: Distribution chart has {len(dist_chart)} histogram bins")

    @pytest.mark.parametrize("strategy_type", STRATEGY_TYPES)
    def test_simulation_has_risk_metrics(self, strategy_type):
        """Test simulation response contains monte_carlo.risk_metrics with VaR, CVaR, etc."""
        response = self.session.get(f"{BASE_URL}/api/portfolios/simulation/{strategy_type}")
        assert response.status_code == 200
        data = response.json()
        
        if data.get("status") == "computing":
            pytest.skip(f"{strategy_type} simulation still computing")
        
        mc = data.get("monte_carlo")
        assert mc is not None, "Missing monte_carlo"
        
        risk = mc.get("risk_metrics")
        assert risk is not None, "Missing risk_metrics"
        
        # Check required risk metric fields
        required_fields = [
            "var_95_pct",
            "cvar_95_pct",
            "probability_of_profit_pct",
            "expected_return_pct",
            "max_expected_drawdown_pct",
            "median_return_pct",
            "return_range_25_75"
        ]
        for field in required_fields:
            assert field in risk, f"Missing risk metric: {field}"
        
        # Validate VaR (should be negative or small positive for 95% confidence)
        var_95 = risk["var_95_pct"]
        assert isinstance(var_95, (int, float)), "var_95_pct should be numeric"
        
        # CVaR should be <= VaR (more extreme)
        cvar_95 = risk["cvar_95_pct"]
        assert cvar_95 <= var_95, f"CVaR ({cvar_95}) should be <= VaR ({var_95})"
        
        # Probability of profit should be 0-100%
        prob_profit = risk["probability_of_profit_pct"]
        assert 0 <= prob_profit <= 100, f"Probability of profit {prob_profit}% out of range"
        
        # Max expected drawdown should be positive
        max_dd = risk["max_expected_drawdown_pct"]
        assert max_dd >= 0, f"Max drawdown should be positive, got {max_dd}"
        
        # Return range should be a list of 2 values
        return_range = risk["return_range_25_75"]
        assert isinstance(return_range, list) and len(return_range) == 2, "return_range_25_75 should be [p25, p75]"
        assert return_range[0] <= return_range[1], "Return range should be [lower, upper]"
        
        print(f"✅ {strategy_type}: Risk metrics - VaR95={var_95}%, CVaR95={cvar_95}%, P(profit)={prob_profit}%, MaxDD={max_dd}%")

    @pytest.mark.parametrize("strategy_type", STRATEGY_TYPES)
    def test_simulation_has_terminal_stats(self, strategy_type):
        """Test simulation response contains monte_carlo.terminal_stats"""
        response = self.session.get(f"{BASE_URL}/api/portfolios/simulation/{strategy_type}")
        assert response.status_code == 200
        data = response.json()
        
        if data.get("status") == "computing":
            pytest.skip(f"{strategy_type} simulation still computing")
        
        mc = data.get("monte_carlo")
        assert mc is not None, "Missing monte_carlo"
        
        term = mc.get("terminal_stats")
        assert term is not None, "Missing terminal_stats"
        
        # Check required terminal stat fields
        required_fields = ["mean_value", "median_value", "worst_case_value", "best_case_value"]
        for field in required_fields:
            assert field in term, f"Missing terminal stat: {field}"
            assert isinstance(term[field], (int, float)), f"{field} should be numeric"
        
        # Validate ordering: worst < median < mean < best (typically)
        assert term["worst_case_value"] <= term["median_value"], "Worst case should be <= median"
        assert term["median_value"] <= term["best_case_value"], "Median should be <= best case"
        
        print(f"✅ {strategy_type}: Terminal stats - Worst={term['worst_case_value']:.0f}, Median={term['median_value']:.0f}, Best={term['best_case_value']:.0f}")

    def test_swing_trader_expected_return(self):
        """Swing Trader should show negative/low expected return reflecting weak strategy"""
        response = self.session.get(f"{BASE_URL}/api/portfolios/simulation/swing")
        assert response.status_code == 200
        data = response.json()
        
        if data.get("status") == "computing":
            pytest.skip("Swing simulation still computing")
        
        lstm = data.get("lstm_forecast", {})
        exp_return = lstm.get("annualized_expected_return_pct", 0)
        
        # Swing trader historically underperforms - expected return should be lower than aggressive strategies
        # Based on iteration 13, swing had CAGR=12.4% vs bespoke=52.39%
        # We just verify it's not unreasonably high
        assert exp_return < 50, f"Swing expected return {exp_return}% seems too high for a weak strategy"
        
        print(f"✅ Swing Trader: Expected return {exp_return}% (appropriately modest)")

    def test_all_simulations_complete(self):
        """Summary test: verify all 6 simulations are cached and complete"""
        complete_count = 0
        computing_count = 0
        
        for strategy in STRATEGY_TYPES:
            response = self.session.get(f"{BASE_URL}/api/portfolios/simulation/{strategy}")
            assert response.status_code == 200
            data = response.json()
            
            if data.get("status") == "complete":
                complete_count += 1
            else:
                computing_count += 1
        
        print(f"\n📊 Simulation Status Summary:")
        print(f"   Complete: {complete_count}/6")
        print(f"   Computing: {computing_count}/6")
        
        # All should be complete since they're cached
        assert complete_count == 6, f"Expected all 6 simulations complete, got {complete_count}"
        print("✅ All 6 simulations are cached and complete")


class TestSimulationDataQuality:
    """Additional data quality tests for simulation results"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def test_simulation_metadata(self):
        """Test simulation response has proper metadata"""
        response = self.session.get(f"{BASE_URL}/api/portfolios/simulation/value_stocks")
        assert response.status_code == 200
        data = response.json()
        
        if data.get("status") == "computing":
            pytest.skip("Simulation still computing")
        
        # Check metadata fields
        assert "strategy" in data, "Missing strategy name"
        assert "stocks_simulated" in data, "Missing stocks_simulated count"
        assert "portfolio_value" in data, "Missing portfolio_value"
        assert "simulation_horizon" in data, "Missing simulation_horizon"
        assert "computation_time_sec" in data, "Missing computation_time_sec"
        
        # Verify reasonable values
        assert data["stocks_simulated"] > 0, "Should have simulated at least 1 stock"
        assert data["portfolio_value"] > 0, "Portfolio value should be positive"
        
        print(f"✅ Simulation metadata: {data['strategy']}, {data['stocks_simulated']} stocks, ₹{data['portfolio_value']:.0f}")

    def test_monte_carlo_simulation_params(self):
        """Test Monte Carlo simulation parameters are recorded"""
        response = self.session.get(f"{BASE_URL}/api/portfolios/simulation/long_term")
        assert response.status_code == 200
        data = response.json()
        
        if data.get("status") == "computing":
            pytest.skip("Simulation still computing")
        
        mc = data.get("monte_carlo", {})
        params = mc.get("simulation_params")
        assert params is not None, "Missing simulation_params"
        
        # Check simulation parameters
        assert params.get("n_paths") == 10000, f"Expected 10000 paths, got {params.get('n_paths')}"
        assert params.get("horizon_days") == 252, f"Expected 252 days, got {params.get('horizon_days')}"
        assert "daily_mu" in params, "Missing daily_mu"
        assert "daily_sigma" in params, "Missing daily_sigma"
        
        print(f"✅ Monte Carlo params: {params['n_paths']} paths, {params['horizon_days']} days")

    def test_fan_chart_progression(self):
        """Test fan chart shows proper value progression over time"""
        response = self.session.get(f"{BASE_URL}/api/portfolios/simulation/bespoke_forward_looking")
        assert response.status_code == 200
        data = response.json()
        
        if data.get("status") == "computing":
            pytest.skip("Simulation still computing")
        
        fan_chart = data.get("monte_carlo", {}).get("fan_chart", [])
        assert len(fan_chart) >= 2, "Need at least 2 points for progression test"
        
        # First point should be at day 0
        assert fan_chart[0]["day"] == 0, "First point should be at day 0"
        
        # Last point should be at or near day 252
        last_day = fan_chart[-1]["day"]
        assert last_day >= 250, f"Last point should be near day 252, got {last_day}"
        
        # Median (p50) at day 0 should equal initial portfolio value
        initial_p50 = fan_chart[0]["p50"]
        portfolio_value = data.get("portfolio_value", 0)
        assert abs(initial_p50 - portfolio_value) < 1, f"Initial p50 ({initial_p50}) should equal portfolio value ({portfolio_value})"
        
        print(f"✅ Fan chart progression: Day 0 to Day {last_day}, initial value ₹{initial_p50:.0f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
