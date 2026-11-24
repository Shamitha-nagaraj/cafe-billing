"""Server-authoritative money calculations and atomic, idempotent checkout."""
import hashlib
import json
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from .config import money


class Conflict(ValueError):
    pass


def receipt(db, bill_id):
    row = db.execute('SELECT * FROM bills WHERE id=?', (bill_id,)).fetchone()
    if not row:
        return None
    result = dict(row)
    result.pop('payload_hash')
    result.pop('request_id')
    result['number'] = f"CL-{row['id']:06d}"
    result['items'] = [dict(x) for x in db.execute('SELECT name,quantity,unit_price_minor,line_total_minor FROM bill_items WHERE bill_id=? ORDER BY id', (bill_id,))]
    return result


def checkout(db, payload, cfg):
    if not isinstance(payload, dict):
        raise ValueError('Submit an order object.')
    token = payload.get('request_id', '')
    try:
        uuid.UUID(token)
    except (ValueError, AttributeError, TypeError):
        raise ValueError('A valid request ID is required.') from None
    items = payload.get('items')
    if not isinstance(items, list) or not 1 <= len(items) <= 50:
        raise ValueError('Choose between 1 and 50 menu items.')
    normalized, seen = [], set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('Invalid cart item.')
        mid, qty = item.get('id'), item.get('quantity')
        if type(mid) is not int or mid <= 0 or type(qty) is not int or not 1 <= qty <= 99 or mid in seen:
            raise ValueError('Each item must be unique and have a quantity from 1 to 99.')
        seen.add(mid)
        normalized.append({'id': mid, 'quantity': qty})
    discount = money(payload.get('discount', '0'))
    payment, order_type = payload.get('payment_method'), payload.get('order_type')
    if payment not in ('Cash', 'Card', 'UPI') or order_type not in ('Dine-in', 'Takeaway'):
        raise ValueError('Choose a payment method and order type.')
    canonical = {'items': sorted(normalized, key=lambda x:x['id']), 'discount': discount,
                 'payment_method': payment, 'order_type': order_type}
    fingerprint = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
    try:
        db.execute('BEGIN IMMEDIATE')
        existing = db.execute('SELECT id,payload_hash FROM bills WHERE request_id=?', (token,)).fetchone()
        if existing:
            if existing['payload_hash'] != fingerprint:
                raise Conflict('This request ID was already used for a different bill. Start a new bill.')
            result = receipt(db, existing['id'])
            db.rollback()
            return result, False
        lines = []
        for item in normalized:
            row = db.execute('SELECT * FROM menu WHERE id=? AND active=1', (item['id'],)).fetchone()
            if not row:
                raise ValueError('A selected menu item is no longer available. Refresh the menu.')
            lines.append((row, item['quantity']))
        subtotal = sum(row['price_minor'] * qty for row, qty in lines)
        if discount > subtotal:
            raise ValueError('Discount cannot exceed the subtotal.')
        tax = ((subtotal-discount) * cfg['TAX_BPS'] + 5000) // 10000
        now = datetime.now(ZoneInfo(cfg['TIMEZONE']))
        cursor = db.execute('''INSERT INTO bills(request_id,payload_hash,created_at,business_date,
            subtotal_minor,discount_minor,tax_minor,tax_bps,total_minor,payment_method,order_type,currency)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', (token, fingerprint, now.isoformat(), now.date().isoformat(),
            subtotal, discount, tax, cfg['TAX_BPS'], subtotal-discount+tax, payment, order_type, cfg['CURRENCY']))
        bill_id = cursor.lastrowid
        db.executemany('''INSERT INTO bill_items(bill_id,menu_id,name,quantity,unit_price_minor,line_total_minor)
            VALUES (?,?,?,?,?,?)''', [(bill_id,row['id'],row['name'],qty,row['price_minor'],row['price_minor']*qty) for row,qty in lines])
        db.commit()
        return receipt(db, bill_id), True
    except Exception:
        db.rollback()
        raise
