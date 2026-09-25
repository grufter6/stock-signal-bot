# Curated universe: a mix of historically higher-beta/growth names and
# historically lower-beta/blue-chip names, so the daily scan has real
# material to split into "volatile" vs "steady" buckets by *measured*
# volatility (not by this a-priori guess).
UNIVERSE = [
    # higher-beta / growth-leaning
    "TSLA", "NVDA", "AMD", "COIN", "MARA", "PLTR", "SOFI", "RIVN",
    "SMCI", "ARM", "MSTR", "SNAP", "ROKU", "DKNG", "CVNA", "UPST",
    "AFRM", "SQ", "SHOP", "NET",
    # blue-chip / lower-beta-leaning
    "JNJ", "PG", "KO", "PEP", "WMT", "MCD", "VZ", "T",
    "DUK", "SO", "XOM", "CVX", "JPM", "V", "MA", "MSFT",
    "AAPL", "GOOGL", "BRK-B", "UNH",
]

# how many symbols to keep, per bucket, for the frequent signal-check
TOP_N_PER_BUCKET = 5
