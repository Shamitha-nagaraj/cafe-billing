"""Configuration shared by the local and hosted launchers."""
import os
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent


def money(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError('Enter a valid amount with at most two decimal places.')
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0 or amount > 1000000 or amount * 100 != (amount * 100).to_integral_value():
            raise ValueError('Amount must be 0–1,000,000 with at most two decimal places.')
        return int(amount * 100)
    except InvalidOperation:
        raise ValueError('Enter a valid amount.') from None


def public_origin(value):
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment
            or any(c.isspace() for c in value) or '\\' in value):
        raise ValueError('APP_PUBLIC_URL must be the exact public HTTPS origin, without a path.')
    _ = parsed.port
    return 'https://' + parsed.netloc.lower()


def settings(overrides=None):
    local = {}
    path = ROOT / '.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                key, sep, value = line.partition('=')
                if not sep:
                    raise ValueError('Use NAME=value entries in .env.')
                local[key.strip()] = value.strip().strip('\"\'')
    def env(key, default=''):
        return os.environ.get(key, local.get(key, default))
    demo = env('CAFE_DEMO', '0') == '1'
    origin = env('APP_PUBLIC_URL') or env('RENDER_EXTERNAL_URL')
    cfg = {
        'CAFE_NAME': env('CAFE_NAME', 'Café Ledger'),
        'CURRENCY': env('CAFE_CURRENCY', 'INR'),
        'TIMEZONE': env('CAFE_TIMEZONE', 'Asia/Kolkata'),
        'TAX_BPS': money(env('CAFE_TAX_PERCENT', '0')),
        'DATA_DIR': Path(env('CAFE_DATA_DIR', str(ROOT / 'instance'))),
        'DEMO': demo,
        'PUBLIC_ORIGIN': public_origin(origin) if origin else '',
        'ADMIN_USER': env('CAFE_ADMIN_USER', 'admin'),
        'ADMIN_PASSWORD': env('CAFE_ADMIN_PASSWORD'),
        'MAX_CONTENT_LENGTH': 64 * 1024,
        'TESTING': False,
    }
    cfg.update(overrides or {})
    if cfg['CURRENCY'] not in {'INR', 'USD', 'EUR', 'GBP', 'AUD', 'CAD'}:
        raise ValueError('Supported two-decimal currencies: INR, USD, EUR, GBP, AUD, CAD.')
    if not 0 <= cfg['TAX_BPS'] <= 10000:
        raise ValueError('Tax must be between 0 and 100 percent.')
    if not cfg['CAFE_NAME'].strip() or len(cfg['CAFE_NAME']) > 80:
        raise ValueError('Café name must contain 1–80 characters.')
    ZoneInfo(cfg['TIMEZONE'])
    if cfg['PUBLIC_ORIGIN'] and len(cfg['ADMIN_PASSWORD']) < 16:
        raise ValueError('Public hosting requires CAFE_ADMIN_PASSWORD of at least 16 characters.')
    cfg['DATA_DIR'] = Path(cfg['DATA_DIR'])
    cfg['DATABASE'] = cfg['DATA_DIR'] / ('demo.sqlite3' if cfg['DEMO'] else 'cafe.sqlite3')
    return cfg
