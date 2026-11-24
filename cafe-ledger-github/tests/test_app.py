import base64
import csv
import io
import tempfile
import unittest
import uuid
from datetime import date, timedelta
from pathlib import Path

from cafe import create_app
from cafe.config import money, public_origin
from cafe.database import connect


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = {'TESTING': True, 'DATA_DIR': Path(self.temp.name), 'DEMO': False,
                       'PUBLIC_ORIGIN': '', 'ADMIN_PASSWORD': '', 'CURRENCY': 'INR',
                       'TIMEZONE': 'Asia/Kolkata', 'TAX_BPS': 500}
        self.app = create_app(self.config)
        self.client = self.app.test_client()
        self.headers = {'Origin': 'http://localhost', 'X-Cafe-Request': '1'}
        self.menu = self.client.get('/api/menu').json['items']

    def payload(self, **changes):
        result = {'request_id': str(uuid.uuid4()), 'items': [{'id': self.menu[0]['id'], 'quantity': 2}],
                  'discount': '0.01', 'payment_method': 'UPI', 'order_type': 'Dine-in'}
        result.update(changes)
        return result

    def post(self, payload):
        return self.client.post('/api/bills', json=payload, headers=self.headers)

    def db(self):
        db = connect(self.app.config['DATABASE'])
        self.addCleanup(db.close)
        return db

    def test_billing_uses_server_prices_and_rounds_tax(self):
        payload = self.payload()
        payload['items'][0]['price_minor'] = 1
        payload['total_minor'] = 0
        response = self.post(payload)
        self.assertEqual(response.status_code, 201)
        bill = response.json['bill']
        subtotal = self.menu[0]['price_minor'] * 2
        self.assertEqual(bill['subtotal_minor'], subtotal)
        self.assertEqual(bill['tax_minor'], ((subtotal - 1) * 500 + 5000) // 10000)
        self.assertEqual(bill['total_minor'], subtotal - 1 + bill['tax_minor'])

    def test_half_paise_rounds_up(self):
        db = self.db()
        with db:
            db.execute('UPDATE menu SET price_minor=10 WHERE id=?', (self.menu[0]['id'],))
        bill = self.post(self.payload(items=[{'id': self.menu[0]['id'], 'quantity': 1}], discount='0')).json['bill']
        self.assertEqual(bill['tax_minor'], 1)
        self.assertEqual(bill['total_minor'], 11)

    def test_retry_does_not_duplicate_bill(self):
        payload = self.payload()
        first = self.post(payload)
        second = self.post(payload)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json['bill'], second.json['bill'])
        self.assertEqual(self.db().execute('SELECT COUNT(*) FROM bills').fetchone()[0], 1)

    def test_reused_id_cannot_change_bill(self):
        payload = self.payload()
        self.post(payload)
        payload['discount'] = '10'
        self.assertEqual(self.post(payload).status_code, 409)
        self.assertEqual(self.db().execute('SELECT COUNT(*) FROM bills').fetchone()[0], 1)

    def test_invalid_cart_is_atomic(self):
        for items in [[], [{'id': self.menu[0]['id'], 'quantity': 1}, {'id': 999999, 'quantity': 1}],
                      [{'id': self.menu[0]['id'], 'quantity': -1}], [{'id': True, 'quantity': 1}],
                      [{'id': self.menu[0]['id'], 'quantity': 1}] * 2,
                      [{'id': self.menu[0]['id'], 'quantity': 100}]]:
            with self.subTest(items=items):
                self.assertEqual(self.post(self.payload(items=items)).status_code, 400)
        db = self.db()
        self.assertEqual(db.execute('SELECT COUNT(*) FROM bills').fetchone()[0], 0)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM bill_items').fetchone()[0], 0)

    def test_discount_cannot_exceed_subtotal(self):
        self.assertEqual(self.post(self.payload(discount='999999')).status_code, 400)

    def test_bad_payment_and_request_id_rejected(self):
        for change in [{'payment_method': 'Bitcoin'}, {'request_id': 'oops'}, {'discount': 'NaN'}, {'discount': True}]:
            self.assertEqual(self.post(self.payload(**change)).status_code, 400)

    def test_receipt_keeps_original_price_and_name(self):
        payload = self.payload()
        original = self.post(payload).json['bill']
        item = self.menu[0]
        result = self.client.patch('/api/menu/' + str(item['id']), headers=self.headers,
            json={'name': 'Renamed item', 'category': 'Coffee', 'price': '999', 'active': False})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.client.get('/api/bills/' + str(original['id'])).json['bill'], original)
        self.assertEqual(self.post(payload).json['bill'], original)
        self.assertEqual(self.post(self.payload()).status_code, 400)

    def test_report_reconciles_discount_tax_and_items(self):
        first = self.post(self.payload(discount='10')).json['bill']
        second = self.post(self.payload(discount='0')).json['bill']
        report = self.client.get('/api/analytics').json
        self.assertEqual(report['totals']['bills'], 2)
        self.assertEqual(report['totals']['gross_minor'], first['total_minor'] + second['total_minor'])
        self.assertEqual(report['totals']['net_minor'], first['subtotal_minor'] + second['subtotal_minor'] - 1000)
        self.assertEqual(report['best_sellers'][0]['quantity'], 4)
        self.assertEqual(len(report['daily']), 30)
        self.assertEqual(sum(row['bills'] == 0 for row in report['daily']), 29)

    def test_export_is_explicit_about_currency_and_mode(self):
        self.post(self.payload())
        response = self.client.get('/api/export.csv')
        rows = list(csv.DictReader(io.StringIO(response.text)))
        self.assertEqual(rows[-1]['currency'], 'INR')
        self.assertEqual(rows[-1]['data_mode'], 'real')
        self.assertEqual(rows[-1]['bills'], '1')
        self.assertIn('attachment;', response.headers['Content-Disposition'])

    def test_period_validation(self):
        for query in ['start=oops', 'start=2026-02-02&end=2026-01-01', 'start=2020-01-01&end=2022-01-01', 'end=2999-01-01']:
            self.assertEqual(self.client.get('/api/analytics?' + query).status_code, 400)

    def test_mutations_need_same_origin_and_custom_header(self):
        self.assertEqual(self.client.post('/api/bills', json=self.payload()).status_code, 403)
        self.assertEqual(self.client.post('/api/bills', json=self.payload(), headers={**self.headers, 'Origin': 'https://evil.example'}).status_code, 403)
        self.assertEqual(self.client.post('/api/bills', data='x', headers=self.headers).status_code, 415)
        self.assertEqual(self.client.get('/api/menu', base_url='http://untrusted.example').status_code, 403)

    def test_public_mode_requires_password_and_authenticates(self):
        with self.assertRaises(ValueError):
            create_app({**self.config, 'PUBLIC_ORIGIN': 'https://cafe.example'})
        password = 'a-long-test-password-123'
        hosted = create_app({**self.config, 'PUBLIC_ORIGIN': 'https://cafe.example', 'ADMIN_PASSWORD': password})
        client = hosted.test_client()
        self.assertEqual(client.get('/healthz', base_url='https://cafe.example').status_code, 200)
        self.assertEqual(client.get('/api/menu', base_url='https://cafe.example').status_code, 401)
        auth = 'Basic ' + base64.b64encode(('admin:' + password).encode()).decode()
        self.assertEqual(client.get('/api/menu', base_url='https://cafe.example', headers={'Authorization': auth}).status_code, 200)
        self.assertEqual(client.get('/api/menu', base_url='https://wrong.example', headers={'Authorization': auth}).status_code, 403)

    def test_real_register_starts_without_sales(self):
        self.assertEqual(self.client.get('/api/analytics').json['totals']['bills'], 0)
        self.assertFalse(self.client.get('/api/forecast').json['ready'])

    def test_demo_is_separate_and_seed_is_not_repeated(self):
        demo = create_app({**self.config, 'DEMO': True})
        db = connect(demo.config['DATABASE'])
        self.addCleanup(db.close)
        count = db.execute('SELECT COUNT(*) FROM bills').fetchone()[0]
        self.assertGreater(count, 1000)
        self.assertEqual(db.execute('SELECT COUNT(DISTINCT business_date) FROM bills').fetchone()[0], 90)
        create_app({**self.config, 'DEMO': True})
        self.assertEqual(db.execute('SELECT COUNT(*) FROM bills').fetchone()[0], count)
        self.assertEqual(self.db().execute('SELECT COUNT(*) FROM bills').fetchone()[0], 0)

    def test_database_currency_cannot_be_relabeled(self):
        with self.assertRaises(ValueError):
            create_app({**self.config, 'CURRENCY': 'USD'})

    def test_private_files_not_served(self):
        for path in ['/instance/cafe.sqlite3', '/.env', '/cafe/config.py']:
            self.assertEqual(self.client.get(path).status_code, 404)


class MoneyTests(unittest.TestCase):
    def test_decimal_amounts(self):
        self.assertEqual(money('120.50'), 12050)
        self.assertEqual(money(0), 0)
        for invalid in ['1.001', '-1', 'NaN', 'Infinity', True, None, '1000001']:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                money(invalid)

    def test_public_url_is_https_origin(self):
        self.assertEqual(public_origin('https://Cafe.Example/'), 'https://cafe.example')
        for value in ['http://cafe.example', 'https://cafe.example/path', 'https://user:pass@cafe.example', 'https://cafe.example?x=1']:
            with self.assertRaises(ValueError):
                public_origin(value)


if __name__ == '__main__':
    unittest.main()
