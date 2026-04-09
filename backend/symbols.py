"""
Nifty 50 + Key MCX Commodity Proxy Symbols
"""

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
    {"symbol": "TATAMOTORS.NS", "name": "Tata Motors", "sector": "Automobile"},
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
    {"symbol": "BEL.NS", "name": "Bharat Electronics", "sector": "Defence"}
]

MCX_COMMODITIES = [
    {"symbol": "GC=F", "name": "Gold", "sector": "Precious Metals"},
    {"symbol": "SI=F", "name": "Silver", "sector": "Precious Metals"},
    {"symbol": "CL=F", "name": "Crude Oil", "sector": "Energy"},
    {"symbol": "NG=F", "name": "Natural Gas", "sector": "Energy"},
    {"symbol": "HG=F", "name": "Copper", "sector": "Base Metals"},
    {"symbol": "ZC=F", "name": "Cotton", "sector": "Agri"},
]

ALL_SYMBOLS = NIFTY_50 + MCX_COMMODITIES

SECTORS = list(set(s["sector"] for s in ALL_SYMBOLS))

def get_symbol_info(symbol: str):
    for s in ALL_SYMBOLS:
        if s["symbol"] == symbol:
            return s
    return {"symbol": symbol, "name": symbol.replace(".NS", "").replace("=F", ""), "sector": "Unknown"}

def search_symbols(query: str):
    query = query.upper()
    results = []
    for s in ALL_SYMBOLS:
        if query in s["symbol"].upper() or query in s["name"].upper():
            results.append(s)
    return results[:20]
