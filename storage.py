# import sqlite3
# from pathlib import Path
# from datetime import datetime

# DB_PATH = Path("data") / "terminal.db"

# def init_db():
#     DB_PATH.parent.mkdir(parents=True, exist_ok=True)
#     con=sqlite3.connect(DB_PATH)
#     con.execute("""
#     CREATE TABLE IF NOT EXISTS signals(
#         signal_id TEXT PRIMARY KEY,
#         created_at TEXT,
#         symbol TEXT,
#         action TEXT,
#         price REAL,
#         entry_low REAL,
#         entry_high REAL,
#         sl REAL,
#         tp1 REAL,
#         tp2 REAL,
#         rr REAL,
#         confidence REAL,
#         bull_score REAL,
#         bear_score REAL,
#         regime TEXT,
#         sector TEXT,
#         smart_money REAL,
#         rel_volume REAL,
#         status TEXT DEFAULT 'ACTIVE',
#         outcome TEXT DEFAULT ''
#     )""")
#     con.commit(); con.close()

# def save_signal(row):
#     init_db()
#     sid=row.get("signal_id") or f"SIG-{datetime.now():%Y%m%d-%H%M%S-%f}"
#     con=sqlite3.connect(DB_PATH)
#     con.execute("""INSERT OR REPLACE INTO signals
#     (signal_id,created_at,symbol,action,price,entry_low,entry_high,sl,tp1,tp2,rr,confidence,bull_score,bear_score,regime,sector,smart_money,rel_volume,status,outcome)
#     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
#     (sid,datetime.now().isoformat(timespec="seconds"),row["symbol"],row["action"],row["price"],
#      row["entry_low"],row["entry_high"],row["sl"],row["tp1"],row["tp2"],row["rr"],row["confidence"],
#      row["bull_score"],row["bear_score"],row["regime"],row.get("sector","N/A"),row["smart_money"],row["rel_volume"],
#      row.get("status","ACTIVE"),row.get("outcome","")))
#     con.commit(); con.close()
#     return sid

# def read_signals(limit=200):
#     init_db()
#     con=sqlite3.connect(DB_PATH)
#     df=__import__("pandas").read_sql_query("SELECT * FROM signals ORDER BY created_at DESC LIMIT ?",con,params=(limit,))
#     con.close()
#     return df
