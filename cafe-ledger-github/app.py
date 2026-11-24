"""Local-only development launcher. Use serve.py on an HTTPS host."""
import argparse
from cafe import create_app

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Café Ledger: local billing and forecasting')
    parser.add_argument('--demo',action='store_true',help='Use an isolated database with synthetic sales')
    parser.add_argument('--port',type=int,default=8080)
    args = parser.parse_args()
    app = create_app({'DEMO':True} if args.demo else None)
    print('DEMONSTRATION DATA' if app.config['DEMO'] else 'REAL REGISTER — empty until you record sales')
    app.run(host='127.0.0.1',port=args.port,debug=False)
