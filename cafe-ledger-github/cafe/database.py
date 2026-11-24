"""SQLite persistence. Demo history is isolated from real transactions."""
import random
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

MENU = [
    ('Espresso', 'Coffee', 9000, 'ES'), ('Cappuccino', 'Coffee', 15000, 'CA'),
    ('Café Latte', 'Coffee', 17000, 'LA'), ('Cold Brew', 'Coffee', 18000, 'CB'),
    ('Masala Chai', 'Tea & more', 7000, 'CH'), ('Hot Chocolate', 'Tea & more', 16000, 'HC'),
    ('Butter Croissant', 'Bakery', 14000, 'CR'), ('Chocolate Muffin', 'Bakery', 12000, 'MU'),
    ('Grilled Sandwich', 'Kitchen', 22000, 'GS'), ('Pesto Toast', 'Kitchen', 19000, 'PT'),
    ('Blueberry Cheesecake', 'Bakery', 24000, 'CC'), ('Fresh Lime Soda', 'Tea & more', 11000, 'LS'),
]
SCHEMA = '''
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS menu (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
 price_minor INTEGER NOT NULL CHECK(price_minor>0), code TEXT NOT NULL,
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)));
CREATE TABLE IF NOT EXISTS bills (
 id INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT NOT NULL UNIQUE,
 payload_hash TEXT NOT NULL, created_at TEXT NOT NULL, business_date TEXT NOT NULL,
 subtotal_minor INTEGER NOT NULL CHECK(subtotal_minor>=0),
 discount_minor INTEGER NOT NULL CHECK(discount_minor>=0),
 tax_minor INTEGER NOT NULL CHECK(tax_minor>=0), tax_bps INTEGER NOT NULL,
 total_minor INTEGER NOT NULL CHECK(total_minor>=0), payment_method TEXT NOT NULL,
 order_type TEXT NOT NULL, currency TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS bill_items (
 id INTEGER PRIMARY KEY, bill_id INTEGER NOT NULL REFERENCES bills(id),
 menu_id INTEGER NOT NULL REFERENCES menu(id), name TEXT NOT NULL,
 quantity INTEGER NOT NULL CHECK(quantity>0), unit_price_minor INTEGER NOT NULL,
 line_total_minor INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS bills_date ON bills(business_date);
CREATE INDEX IF NOT EXISTS items_bill ON bill_items(bill_id);
'''


def connect(path):
    db = sqlite3.connect(str(path), timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=10000')
    return db


def initialize(cfg):
    cfg['DATA_DIR'].mkdir(parents=True, exist_ok=True)
    db = connect(cfg['DATABASE'])
    try:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript(SCHEMA)
        with db:
            for key, value in [('currency', cfg['CURRENCY']), ('timezone', cfg['TIMEZONE']),
                               ('mode', 'demo' if cfg['DEMO'] else 'real')]:
                previous = db.execute('SELECT value FROM metadata WHERE key=?', (key,)).fetchone()
                if previous and previous['value'] != value:
                    raise ValueError(f'Database {key} differs from configuration. Use a separate data directory.')
                db.execute('INSERT OR IGNORE INTO metadata VALUES (?,?)', (key, value))
            if not db.execute('SELECT 1 FROM menu LIMIT 1').fetchone():
                db.executemany('INSERT INTO menu(name,category,price_minor,code) VALUES (?,?,?,?)', MENU)
            if cfg['DEMO'] and not db.execute("SELECT 1 FROM metadata WHERE key='demo_seeded'").fetchone():
                seed_demo(db, cfg)
                db.execute("INSERT INTO metadata VALUES ('demo_seeded','1')")
    finally:
        db.close()


def seed_demo(db, cfg):
    rng = random.Random(2026)
    today = datetime.now(ZoneInfo(cfg['TIMEZONE'])).date()
    menu = db.execute('SELECT * FROM menu').fetchall()
    for day_index in range(90):
        day = today - timedelta(days=90-day_index)
        count = 12 + day_index // 15 + (10 if day.weekday() >= 5 else 0) + rng.randrange(5)
        for number in range(count):
            picks = rng.sample(list(menu), rng.randint(1, 3))
            rows = [(item, rng.randint(1, 2)) for item in picks]
            subtotal = sum(item['price_minor'] * qty for item, qty in rows)
            discount = 2000 if number % 7 == 0 else 0
            tax = ((subtotal-discount) * cfg['TAX_BPS'] + 5000) // 10000
            created = datetime(day.year, day.month, day.day, 8+number%12, number%60,
                               tzinfo=ZoneInfo(cfg['TIMEZONE'])).isoformat()
            cursor = db.execute('''INSERT INTO bills(request_id,payload_hash,created_at,business_date,
                subtotal_minor,discount_minor,tax_minor,tax_bps,total_minor,payment_method,order_type,currency)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                (f'demo-{day}-{number}', 'synthetic', created, day.isoformat(), subtotal, discount,
                 tax, cfg['TAX_BPS'], subtotal-discount+tax, rng.choice(['Cash','Card','UPI']),
                 rng.choice(['Dine-in','Takeaway']), cfg['CURRENCY']))
            db.executemany('''INSERT INTO bill_items(bill_id,menu_id,name,quantity,unit_price_minor,line_total_minor)
                VALUES (?,?,?,?,?,?)''', [(cursor.lastrowid, item['id'], item['name'], qty,
                                          item['price_minor'], item['price_minor']*qty) for item, qty in rows])
