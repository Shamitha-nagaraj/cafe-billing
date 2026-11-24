from datetime import date, timedelta


def daily_series(db, start, end):
    rows = db.execute('''SELECT business_date AS date, SUM(subtotal_minor-discount_minor) AS net_minor,
        SUM(tax_minor) AS tax_minor, SUM(total_minor) AS gross_minor, COUNT(*) AS bills
        FROM bills WHERE business_date BETWEEN ? AND ? GROUP BY business_date''', (start.isoformat(),end.isoformat()))
    lookup = {row['date']:dict(row) for row in rows}
    result = []
    while start <= end:
        result.append(lookup.get(start.isoformat(), {'date':start.isoformat(),'net_minor':0,'tax_minor':0,'gross_minor':0,'bills':0}))
        start += timedelta(days=1)
    return result


def report(db, start, end):
    daily = daily_series(db, start, end)
    totals = {key:sum(row[key] for row in daily) for key in ('net_minor','tax_minor','gross_minor','bills')}
    totals['average_bill_minor'] = round(totals['gross_minor']/totals['bills']) if totals['bills'] else 0
    best = [dict(x) for x in db.execute('''SELECT i.menu_id, m.name, SUM(i.quantity) AS quantity,
        SUM(i.line_total_minor) AS subtotal_minor FROM bill_items i JOIN bills b ON b.id=i.bill_id
        JOIN menu m ON m.id=i.menu_id
        WHERE b.business_date BETWEEN ? AND ? GROUP BY i.menu_id ORDER BY quantity DESC,i.menu_id LIMIT 6''', (start.isoformat(),end.isoformat()))]
    recent = [dict(x) for x in db.execute('''SELECT id,created_at,total_minor,payment_method,order_type FROM bills
        WHERE business_date BETWEEN ? AND ? ORDER BY id DESC LIMIT 20''', (start.isoformat(),end.isoformat()))]
    for row in recent:
        row['number'] = f"CL-{row['id']:06d}"
    return {'daily':daily,'totals':totals,'best_sellers':best,'recent':recent,
            'start':start.isoformat(),'end':end.isoformat()}


def training_history(db, today):
    first = db.execute('SELECT MIN(business_date) FROM bills').fetchone()[0]
    if not first or first >= today.isoformat():
        return []
    start = max(date.fromisoformat(first), today-timedelta(days=730))
    return daily_series(db, start, today-timedelta(days=1))
