"""Public launch requires HTTPS origin and a staff password."""
import os
from waitress import serve
from cafe import create_app

if __name__ == '__main__':
    app = create_app()
    if not app.config['PUBLIC_ORIGIN']:
        raise SystemExit('Set APP_PUBLIC_URL to the assigned HTTPS origin (Render supplies RENDER_EXTERNAL_URL).')
    if len(app.config['ADMIN_PASSWORD']) < 16:
        raise SystemExit('Set CAFE_ADMIN_PASSWORD to at least 16 characters.')
    serve(app,host='0.0.0.0',port=int(os.environ.get('PORT','8080')),threads=8,
          max_request_body_size=65536,clear_untrusted_proxy_headers=True)
