"""
Expanded Fundamental Analysis Service
30+ metrics fetched from yfinance including balance sheet, income statement, cash flow.
"""
import math
import yfinance as yf
import logging

logger = logging.getLogger(__name__)


def get_fundamentals(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Core metrics
        pe_ratio = info.get("trailingPE") or info.get("forwardPE")
        forward_pe = info.get("forwardPE")
        peg_ratio = info.get("pegRatio")
        price_to_sales = info.get("priceToSalesTrailing12Months")
        price_to_book = info.get("priceToBook")
        ev_to_ebitda = info.get("enterpriseToEbitda")
        ev_to_revenue = info.get("enterpriseToRevenue")
        enterprise_value = info.get("enterpriseValue")

        # Profitability
        profit_margin = info.get("profitMargins")
        operating_margin = info.get("operatingMargins")
        gross_margin = info.get("grossMargins")
        roe = info.get("returnOnEquity")
        roa = info.get("returnOnAssets")

        # Growth
        revenue_growth = info.get("revenueGrowth")
        earnings_growth = info.get("earningsGrowth")
        earnings_quarterly_growth = info.get("earningsQuarterlyGrowth")

        # Debt & Liquidity
        debt_to_equity = info.get("debtToEquity")
        current_ratio = info.get("currentRatio")
        quick_ratio = info.get("quickRatio")
        total_debt = info.get("totalDebt")
        total_cash = info.get("totalCash")
        free_cashflow = info.get("freeCashflow")
        operating_cashflow = info.get("operatingCashflow")

        # Per share
        eps = info.get("trailingEps")
        forward_eps = info.get("forwardEps")
        bvps = info.get("bookValue")
        revenue_per_share = info.get("revenuePerShare")

        # Dividends
        dividend_yield = info.get("dividendYield")
        dividend_rate = info.get("dividendRate")
        payout_ratio = info.get("payoutRatio")

        # Risk
        beta = info.get("beta")

        # Misc
        market_cap = info.get("marketCap")
        current_price = info.get("currentPrice") or info.get("previousClose")
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        full_time_employees = info.get("fullTimeEmployees")
        fifty_two_week_high = info.get("fiftyTwoWeekHigh")
        fifty_two_week_low = info.get("fiftyTwoWeekLow")
        avg_volume = info.get("averageVolume")
        avg_volume_10d = info.get("averageDailyVolume10Day")
        shares_outstanding = info.get("sharesOutstanding")
        float_shares = info.get("floatShares")
        held_pct_insiders = info.get("heldPercentInsiders")
        held_pct_institutions = info.get("heldPercentInstitutions")
        short_ratio = info.get("shortRatio")

        # Graham's Intrinsic Value
        graham_value = None
        if eps and bvps and eps > 0 and bvps > 0:
            graham_value = round(math.sqrt(22.5 * eps * bvps), 2)

        valuation = "N/A"
        if graham_value and current_price:
            ratio = current_price / graham_value
            if ratio < 0.8: valuation = "Deeply Undervalued"
            elif ratio < 1.0: valuation = "Undervalued"
            elif ratio < 1.2: valuation = "Fair Value"
            elif ratio < 1.5: valuation = "Overvalued"
            else: valuation = "Highly Overvalued"

        # FCF Yield
        fcf_yield = None
        if free_cashflow and market_cap and market_cap > 0:
            fcf_yield = round(free_cashflow / market_cap * 100, 2)

        # Debt/EBITDA proxy
        ebitda = info.get("ebitda")
        debt_to_ebitda = None
        if total_debt and ebitda and ebitda > 0:
            debt_to_ebitda = round(total_debt / ebitda, 2)

        # Net cash position
        net_cash = None
        if total_cash is not None and total_debt is not None:
            net_cash = total_cash - total_debt

        # Try to get quarterly financials
        quarterly_revenue = []
        quarterly_earnings = []
        try:
            q_fin = ticker.quarterly_financials
            if q_fin is not None and not q_fin.empty:
                for col in q_fin.columns[:4]:
                    rev = q_fin.loc["Total Revenue"][col] if "Total Revenue" in q_fin.index else None
                    ni = q_fin.loc["Net Income"][col] if "Net Income" in q_fin.index else None
                    quarterly_revenue.append({"quarter": str(col.date()), "revenue": float(rev) if rev else None})
                    quarterly_earnings.append({"quarter": str(col.date()), "net_income": float(ni) if ni else None})
        except Exception:
            pass

        def safe_round(v, d=2):
            if v is None: return None
            try: return round(float(v), d)
            except: return None

        def pct(v):
            if v is None: return None
            try: return round(float(v) * 100, 2)
            except: return None

        return {
            # Valuation
            "pe_ratio": safe_round(pe_ratio), "forward_pe": safe_round(forward_pe),
            "peg_ratio": safe_round(peg_ratio), "price_to_sales": safe_round(price_to_sales),
            "price_to_book": safe_round(price_to_book), "ev_to_ebitda": safe_round(ev_to_ebitda),
            "ev_to_revenue": safe_round(ev_to_revenue), "enterprise_value": enterprise_value,
            # Profitability
            "profit_margin": pct(profit_margin), "operating_margin": pct(operating_margin),
            "gross_margin": pct(gross_margin), "roe": pct(roe), "roa": pct(roa),
            # Growth
            "revenue_growth": pct(revenue_growth), "earnings_growth": pct(earnings_growth),
            "earnings_quarterly_growth": pct(earnings_quarterly_growth),
            # Debt & Liquidity
            "debt_to_equity": safe_round(debt_to_equity),
            "current_ratio": safe_round(current_ratio), "quick_ratio": safe_round(quick_ratio),
            "total_debt": total_debt, "total_cash": total_cash,
            "net_cash": net_cash, "debt_to_ebitda": debt_to_ebitda,
            # Cash Flow
            "free_cashflow": free_cashflow, "operating_cashflow": operating_cashflow,
            "fcf_yield": fcf_yield,
            # Per Share
            "eps": safe_round(eps), "forward_eps": safe_round(forward_eps),
            "bvps": safe_round(bvps), "revenue_per_share": safe_round(revenue_per_share),
            # Dividends
            "dividend_yield": pct(dividend_yield), "dividend_rate": safe_round(dividend_rate),
            "payout_ratio": pct(payout_ratio),
            # Risk
            "beta": safe_round(beta),
            # Ownership
            "held_pct_insiders": pct(held_pct_insiders),
            "held_pct_institutions": pct(held_pct_institutions),
            "short_ratio": safe_round(short_ratio),
            "shares_outstanding": shares_outstanding, "float_shares": float_shares,
            # Graham
            "graham_value": graham_value, "valuation": valuation,
            "current_price": safe_round(current_price),
            # Misc
            "market_cap": market_cap, "sector": sector, "industry": industry,
            "full_time_employees": full_time_employees,
            "fifty_two_week_high": safe_round(fifty_two_week_high),
            "fifty_two_week_low": safe_round(fifty_two_week_low),
            "avg_volume": avg_volume, "avg_volume_10d": avg_volume_10d,
            # Quarterly
            "quarterly_revenue": quarterly_revenue[:4],
            "quarterly_earnings": quarterly_earnings[:4],
        }
    except Exception as e:
        logger.error(f"Fundamentals error for {symbol}: {e}")
        return {"error": str(e), "sector": "N/A", "industry": "N/A", "current_price": None}
