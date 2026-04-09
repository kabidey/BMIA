"""
Expanded Symbol Universe
Nifty 50 + Nifty Next 50 + Midcap Select + BSE Sensex additions + MCX + Sectoral
With NSE direct data fetching capability.
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

NIFTY_50 = [
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries", "sector": "Energy"},
    {"symbol": "TCS.NS", "name": "Tata Consultancy Services", "sector": "IT"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank", "sector": "Banking"},
    {"symbol": "INFY.NS", "name": "Infosys", "sector": "IT"},
    {"symbol": "ICICIBANK.NS", "name": "ICICI Bank", "sector": "Banking"},
    {"symbol": "HINDUNILVR.NS", "name": "Hindustan Unilever", "sector": "FMCG"},
    {"symbol": "ITC.NS", "name": "ITC Limited", "sector": "FMCG"},
    {"symbol": "SBIN.NS", "name": "State Bank of India", "sector": "Banking"},
    {"symbol": "BHARTIARTL.NS", "name": "Bharti Airtel", "sector": "Telecom"},
    {"symbol": "KOTAKBANK.NS", "name": "Kotak Mahindra Bank", "sector": "Banking"},
    {"symbol": "LT.NS", "name": "Larsen & Toubro", "sector": "Infrastructure"},
    {"symbol": "AXISBANK.NS", "name": "Axis Bank", "sector": "Banking"},
    {"symbol": "ASIANPAINT.NS", "name": "Asian Paints", "sector": "Consumer"},
    {"symbol": "MARUTI.NS", "name": "Maruti Suzuki", "sector": "Automobile"},
    {"symbol": "SUNPHARMA.NS", "name": "Sun Pharma", "sector": "Pharma"},
    {"symbol": "BAJFINANCE.NS", "name": "Bajaj Finance", "sector": "Finance"},
    {"symbol": "WIPRO.NS", "name": "Wipro", "sector": "IT"},
    {"symbol": "HCLTECH.NS", "name": "HCL Technologies", "sector": "IT"},
    {"symbol": "TITAN.NS", "name": "Titan Company", "sector": "Consumer"},
    {"symbol": "ULTRACEMCO.NS", "name": "UltraTech Cement", "sector": "Cement"},
    {"symbol": "NESTLEIND.NS", "name": "Nestle India", "sector": "FMCG"},
    {"symbol": "POWERGRID.NS", "name": "Power Grid Corp", "sector": "Power"},
    {"symbol": "NTPC.NS", "name": "NTPC Limited", "sector": "Power"},
    {"symbol": "TATASTEEL.NS", "name": "Tata Steel", "sector": "Metals"},
    {"symbol": "M&M.NS", "name": "Mahindra & Mahindra", "sector": "Automobile"},
    {"symbol": "JSWSTEEL.NS", "name": "JSW Steel", "sector": "Metals"},
    {"symbol": "ADANIENT.NS", "name": "Adani Enterprises", "sector": "Conglomerate"},
    {"symbol": "ADANIPORTS.NS", "name": "Adani Ports", "sector": "Infrastructure"},
    {"symbol": "TECHM.NS", "name": "Tech Mahindra", "sector": "IT"},
    {"symbol": "ONGC.NS", "name": "ONGC", "sector": "Energy"},
    {"symbol": "COALINDIA.NS", "name": "Coal India", "sector": "Mining"},
    {"symbol": "BPCL.NS", "name": "BPCL", "sector": "Energy"},
    {"symbol": "GRASIM.NS", "name": "Grasim Industries", "sector": "Cement"},
    {"symbol": "DRREDDY.NS", "name": "Dr. Reddy's Labs", "sector": "Pharma"},
    {"symbol": "CIPLA.NS", "name": "Cipla", "sector": "Pharma"},
    {"symbol": "BAJAJFINSV.NS", "name": "Bajaj Finserv", "sector": "Finance"},
    {"symbol": "DIVISLAB.NS", "name": "Divi's Labs", "sector": "Pharma"},
    {"symbol": "BRITANNIA.NS", "name": "Britannia Industries", "sector": "FMCG"},
    {"symbol": "EICHERMOT.NS", "name": "Eicher Motors", "sector": "Automobile"},
    {"symbol": "HEROMOTOCO.NS", "name": "Hero MotoCorp", "sector": "Automobile"},
    {"symbol": "APOLLOHOSP.NS", "name": "Apollo Hospitals", "sector": "Healthcare"},
    {"symbol": "INDUSINDBK.NS", "name": "IndusInd Bank", "sector": "Banking"},
    {"symbol": "SBILIFE.NS", "name": "SBI Life Insurance", "sector": "Insurance"},
    {"symbol": "HDFCLIFE.NS", "name": "HDFC Life Insurance", "sector": "Insurance"},
    {"symbol": "TATACONSUM.NS", "name": "Tata Consumer", "sector": "FMCG"},
    {"symbol": "HINDALCO.NS", "name": "Hindalco", "sector": "Metals"},
    {"symbol": "BAJAJ-AUTO.NS", "name": "Bajaj Auto", "sector": "Automobile"},
    {"symbol": "SHRIRAMFIN.NS", "name": "Shriram Finance", "sector": "Finance"},
    {"symbol": "BEL.NS", "name": "Bharat Electronics", "sector": "Defence"},
    {"symbol": "TRENT.NS", "name": "Trent Limited", "sector": "Retail"},
]

NIFTY_NEXT_50 = [
    {"symbol": "ADANIGREEN.NS", "name": "Adani Green Energy", "sector": "Renewable Energy"},
    {"symbol": "ADANIPOWER.NS", "name": "Adani Power", "sector": "Power"},
    {"symbol": "AMBUJACEM.NS", "name": "Ambuja Cements", "sector": "Cement"},
    {"symbol": "BANKBARODA.NS", "name": "Bank of Baroda", "sector": "Banking"},
    {"symbol": "BERGEPAINT.NS", "name": "Berger Paints", "sector": "Consumer"},
    {"symbol": "BOSCHLTD.NS", "name": "Bosch Limited", "sector": "Auto Components"},
    {"symbol": "CANBK.NS", "name": "Canara Bank", "sector": "Banking"},
    {"symbol": "CHOLAFIN.NS", "name": "Cholamandalam Finance", "sector": "Finance"},
    {"symbol": "COLPAL.NS", "name": "Colgate-Palmolive", "sector": "FMCG"},
    {"symbol": "DLF.NS", "name": "DLF Limited", "sector": "Real Estate"},
    {"symbol": "DABUR.NS", "name": "Dabur India", "sector": "FMCG"},
    {"symbol": "GAIL.NS", "name": "GAIL India", "sector": "Energy"},
    {"symbol": "GODREJCP.NS", "name": "Godrej Consumer", "sector": "FMCG"},
    {"symbol": "HAL.NS", "name": "Hindustan Aeronautics", "sector": "Defence"},
    {"symbol": "HAVELLS.NS", "name": "Havells India", "sector": "Consumer Durables"},
    {"symbol": "ICICIGI.NS", "name": "ICICI Lombard", "sector": "Insurance"},
    {"symbol": "IOC.NS", "name": "Indian Oil Corp", "sector": "Energy"},
    {"symbol": "IRCTC.NS", "name": "IRCTC", "sector": "Travel"},
    {"symbol": "JINDALSTEL.NS", "name": "Jindal Steel", "sector": "Metals"},
    {"symbol": "LICI.NS", "name": "LIC of India", "sector": "Insurance"},
    {"symbol": "MARICO.NS", "name": "Marico", "sector": "FMCG"},
    {"symbol": "NAUKRI.NS", "name": "Info Edge (Naukri)", "sector": "IT Services"},
    {"symbol": "PFC.NS", "name": "Power Finance Corp", "sector": "Finance"},
    {"symbol": "PIDILITIND.NS", "name": "Pidilite Industries", "sector": "Chemicals"},
    {"symbol": "PNB.NS", "name": "Punjab National Bank", "sector": "Banking"},
    {"symbol": "RECLTD.NS", "name": "REC Limited", "sector": "Finance"},
    {"symbol": "SIEMENS.NS", "name": "Siemens India", "sector": "Industrial"},
    {"symbol": "SRF.NS", "name": "SRF Limited", "sector": "Chemicals"},
    {"symbol": "TORNTPHARM.NS", "name": "Torrent Pharma", "sector": "Pharma"},
    {"symbol": "TVSMOTOR.NS", "name": "TVS Motor", "sector": "Automobile"},
    {"symbol": "VEDL.NS", "name": "Vedanta Limited", "sector": "Metals"},
    {"symbol": "ZOMATO.NS", "name": "Zomato", "sector": "Internet"},
    {"symbol": "PAYTM.NS", "name": "One97 Communications", "sector": "Fintech"},
    {"symbol": "DMART.NS", "name": "Avenue Supermarts", "sector": "Retail"},
    {"symbol": "INDIGO.NS", "name": "InterGlobe Aviation", "sector": "Aviation"},
]

MIDCAP_SELECT = [
    {"symbol": "MPHASIS.NS", "name": "Mphasis", "sector": "IT"},
    {"symbol": "PERSISTENT.NS", "name": "Persistent Systems", "sector": "IT"},
    {"symbol": "COFORGE.NS", "name": "Coforge", "sector": "IT"},
    {"symbol": "LTIM.NS", "name": "LTIMindtree", "sector": "IT"},
    {"symbol": "DIXON.NS", "name": "Dixon Technologies", "sector": "Electronics"},
    {"symbol": "POLYCAB.NS", "name": "Polycab India", "sector": "Cables"},
    {"symbol": "ASTRAL.NS", "name": "Astral Limited", "sector": "Pipes"},
    {"symbol": "MUTHOOTFIN.NS", "name": "Muthoot Finance", "sector": "Finance"},
    {"symbol": "JUBLFOOD.NS", "name": "Jubilant FoodWorks", "sector": "QSR"},
    {"symbol": "PAGEIND.NS", "name": "Page Industries", "sector": "Textile"},
    {"symbol": "TATAPOWER.NS", "name": "Tata Power", "sector": "Power"},
    {"symbol": "TATACOMM.NS", "name": "Tata Communications", "sector": "Telecom"},
    {"symbol": "MAXHEALTH.NS", "name": "Max Healthcare", "sector": "Healthcare"},
    {"symbol": "FEDERALBNK.NS", "name": "Federal Bank", "sector": "Banking"},
    {"symbol": "IDFCFIRSTB.NS", "name": "IDFC First Bank", "sector": "Banking"},
    {"symbol": "SAIL.NS", "name": "Steel Authority", "sector": "Metals"},
    {"symbol": "NMDC.NS", "name": "NMDC Limited", "sector": "Mining"},
    {"symbol": "IRFC.NS", "name": "IRFC", "sector": "Finance"},
    {"symbol": "SOLARINDS.NS", "name": "Solar Industries", "sector": "Defence"},
    {"symbol": "CUMMINSIND.NS", "name": "Cummins India", "sector": "Industrial"},
]

MCX_COMMODITIES = [
    {"symbol": "GC=F", "name": "Gold", "sector": "Precious Metals"},
    {"symbol": "SI=F", "name": "Silver", "sector": "Precious Metals"},
    {"symbol": "CL=F", "name": "Crude Oil", "sector": "Energy Commodities"},
    {"symbol": "NG=F", "name": "Natural Gas", "sector": "Energy Commodities"},
    {"symbol": "HG=F", "name": "Copper", "sector": "Base Metals"},
    {"symbol": "ZC=F", "name": "Corn", "sector": "Agri Commodities"},
    {"symbol": "ZS=F", "name": "Soybeans", "sector": "Agri Commodities"},
    {"symbol": "CT=F", "name": "Cotton", "sector": "Agri Commodities"},
    {"symbol": "ALI=F", "name": "Aluminum", "sector": "Base Metals"},
    {"symbol": "PL=F", "name": "Platinum", "sector": "Precious Metals"},
]

ALL_SYMBOLS = NIFTY_50 + NIFTY_NEXT_50 + MIDCAP_SELECT + MCX_COMMODITIES

SECTORS = sorted(list(set(s["sector"] for s in ALL_SYMBOLS)))

# Symbol lookup cache
_SYMBOL_MAP = {s["symbol"]: s for s in ALL_SYMBOLS}


def get_symbol_info(symbol: str):
    if symbol in _SYMBOL_MAP:
        return _SYMBOL_MAP[symbol]
    return {"symbol": symbol, "name": symbol.replace(".NS", "").replace("=F", ""), "sector": "Unknown"}


def search_symbols(query: str):
    query = query.upper()
    results = []
    for s in ALL_SYMBOLS:
        if query in s["symbol"].upper() or query in s["name"].upper():
            results.append(s)
    return results[:30]


def get_symbols_by_category(category: str):
    cat_map = {
        "nifty50": NIFTY_50,
        "next50": NIFTY_NEXT_50,
        "midcap": MIDCAP_SELECT,
        "commodities": MCX_COMMODITIES,
    }
    return cat_map.get(category, NIFTY_50)


def fetch_nse_stock_list():
    """Fetch live stock list from NSE India using nselib."""
    try:
        from nselib import capital_market
        data = capital_market.market_watch_all_indices()
        if data is not None and not data.empty:
            stocks = []
            for _, row in data.iterrows():
                sym = row.get("symbol", "")
                if sym:
                    stocks.append({
                        "symbol": f"{sym}.NS",
                        "name": row.get("companyName", sym),
                        "sector": "NSE",
                        "lastPrice": row.get("lastPrice"),
                        "change": row.get("change"),
                        "pChange": row.get("pChange"),
                    })
            return stocks
    except Exception as e:
        logger.warning(f"NSE direct fetch error: {e}")
    return []


def fetch_nse_index_stocks(index_name: str = "NIFTY 50"):
    """Fetch stocks in a specific NSE index."""
    try:
        from nselib import capital_market
        data = capital_market.index_data(index_name)
        if data is not None and not data.empty:
            stocks = []
            for _, row in data.iterrows():
                sym = row.get("symbol", "")
                if sym:
                    stocks.append({
                        "symbol": f"{sym}.NS",
                        "name": str(row.get("companyName", sym)),
                        "lastPrice": row.get("lastPrice"),
                        "change": row.get("change"),
                        "pChange": row.get("pChange"),
                    })
            return stocks
    except Exception as e:
        logger.warning(f"NSE index fetch error for {index_name}: {e}")
    return []
