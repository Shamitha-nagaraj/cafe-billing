"""Flask application factory; no model API or external account required."""
import csv
import hmac
import io
import sqlite3
from datetime import date, datetime, timedelta
from ipaddress import ip_address
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
from flask import Flask, Response, g, jsonify, render_template, request
from werkzeug.exceptions import HTTPException
from . import analytics, billing, database
from .config import ROOT, money, settings


def create_app(overrides=None):
    app = Flask(__name__, template_folder=str(ROOT/'templates'), static_folder=str(ROOT/'static'))
    app.config.update(settings(overrides))
    database.initialize(app.config)

    def db():
        if 'db' not in g:
            g.db = database.connect(app.config['DATABASE'])
        return g.db

    def today():
        return datetime.now(ZoneInfo(app.config['TIMEZONE'])).date()

    @app.teardown_appcontext
    def close_db(error=None):
        connection = g.pop('db', None)
        if connection is not None:
            connection.close()

    @app.before_request
    def guard():
        if request.path == '/healthz' and request.method in ('GET','HEAD'):
            return None
        origin = app.config['PUBLIC_ORIGIN']
        if origin:
            if request.host.lower() != urlsplit(origin).netloc:
                return jsonify(error='Open the configured website address.'), 403
        else:
            hostname = urlsplit('http://'+request.host).hostname
            try:
                loopback = hostname == 'localhost' or ip_address(hostname or '').is_loopback
            except ValueError:
                loopback = False
            if not loopback:
                return jsonify(error='Local mode accepts localhost only. Configure HTTPS and staff authentication for public hosting.'),403
            origin = request.host_url.rstrip('/')
        password = app.config['ADMIN_PASSWORD']
        if password:
            auth = request.authorization
            if not (auth and auth.type == 'basic'
                    and hmac.compare_digest((auth.username or '').encode(), app.config['ADMIN_USER'].encode())
                    and hmac.compare_digest((auth.password or '').encode(), password.encode())):
                return Response('Staff sign-in required.',401,{'WWW-Authenticate':'Basic realm="Cafe staff", charset="UTF-8"'})
        if request.method not in ('GET','HEAD','OPTIONS'):
            if request.headers.get('Origin') != origin or request.headers.get('X-Cafe-Request') != '1':
                return jsonify(error='Submit changes from this café application.'),403
            if not request.is_json:
                return jsonify(error='Send JSON data.'),415

    @app.after_request
    def security_headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        return response

    @app.errorhandler(billing.Conflict)
    def conflict(error):
        return jsonify(error=str(error)),409

    @app.errorhandler(ValueError)
    def bad_input(error):
        return jsonify(error=str(error)),400

    @app.errorhandler(sqlite3.Error)
    def storage_error(error):
        app.logger.error('Database operation failed (%s)',type(error).__name__)
        return jsonify(error='The database is unavailable or busy. Retry the same bill; do not create a second payment.'),503

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description),error.code

    @app.errorhandler(Exception)
    def unexpected(error):
        app.logger.error('Request failed (%s)',type(error).__name__)
        return jsonify(error='The request could not be completed. Check the server log and retry.'),500

    @app.get('/healthz')
    def health():
        db().execute('SELECT 1')
        return jsonify(status='ok')

    @app.get('/')
    def index():
        return render_template('index.html')

    @app.get('/api/config')
    def config():
        return jsonify(name=app.config['CAFE_NAME'], currency=app.config['CURRENCY'],
                       timezone=app.config['TIMEZONE'], tax_bps=app.config['TAX_BPS'],
                       demo=app.config['DEMO'], today=today().isoformat())

    @app.get('/api/menu')
    def menu():
        return jsonify(items=[dict(row) for row in db().execute('SELECT * FROM menu ORDER BY category,id')])

    @app.post('/api/menu')
    @app.patch('/api/menu/<int:item_id>')
    def save_menu(item_id=None):
        payload = request.get_json()
        if not isinstance(payload,dict):
            raise ValueError('Submit a menu item.')
        name, category = payload.get('name'), payload.get('category')
        if not isinstance(name,str) or not 1 <= len(name.strip()) <= 80:
            raise ValueError('Item name must be 1–80 characters.')
        if not isinstance(category,str) or not 1 <= len(category.strip()) <= 40:
            raise ValueError('Category must be 1–40 characters.')
        price = money(payload.get('price'))
        if not 1 <= price <= 10000000:
            raise ValueError('Item price must be between 0.01 and 100,000.')
        active = payload.get('active',True)
        if type(active) is not bool:
            raise ValueError('Active must be true or false.')
        with db():
            if item_id is None:
                cursor = db().execute('INSERT INTO menu(name,category,price_minor,code,active) VALUES (?,?,?,?,?)',
                                     (name.strip(),category.strip(),price,name.strip()[:2].upper(),int(active)))
                item_id = cursor.lastrowid
            else:
                cursor = db().execute('UPDATE menu SET name=?,category=?,price_minor=?,active=? WHERE id=?',
                                     (name.strip(),category.strip(),price,int(active),item_id))
                if cursor.rowcount != 1:
                    return jsonify(error='Menu item not found.'),404
        return jsonify(item=dict(db().execute('SELECT * FROM menu WHERE id=?',(item_id,)).fetchone()))

    @app.post('/api/bills')
    def create_bill():
        bill, created = billing.checkout(db(),request.get_json(),app.config)
        return jsonify(bill=bill),201 if created else 200

    @app.get('/api/bills/<int:bill_id>')
    def get_bill(bill_id):
        bill = billing.receipt(db(),bill_id)
        return (jsonify(bill=bill) if bill else (jsonify(error='Bill not found.'),404))

    def period():
        end = date.fromisoformat(request.args.get('end',today().isoformat()))
        start = date.fromisoformat(request.args.get('start',(end-timedelta(days=29)).isoformat()))
        if start > end or end > today() or (end-start).days > 365:
            raise ValueError('Choose up to 366 days, ending no later than today.')
        return start,end

    @app.get('/api/analytics')
    def sales():
        start,end = period()
        return jsonify(analytics.report(db(),start,end))

    @app.get('/api/forecast')
    def forecast():
        from .forecast import predict
        return jsonify(predict(analytics.training_history(db(),today()),today()))

    @app.get('/api/export.csv')
    def export():
        start,end = period()
        output = io.StringIO(newline='')
        writer = csv.writer(output)
        writer.writerow(['date','bills','net_sales','tax','collected_total','currency','data_mode'])
        for row in analytics.daily_series(db(),start,end):
            writer.writerow([row['date'],row['bills'],f"{row['net_minor']/100:.2f}",f"{row['tax_minor']/100:.2f}",
                             f"{row['gross_minor']/100:.2f}",app.config['CURRENCY'],'synthetic_demo' if app.config['DEMO'] else 'real'])
        return Response(output.getvalue(),mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename="cafe-sales-{start}-{end}.csv"'})

    return app
