from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import json
from datetime import datetime

app = Flask(__name__)

# CRITICAL: Enable CORS with specific settings for Claude.ai
CORS(app, resources={
    r"/api/*": {
        "origins": "*",  # Allow all origins (Claude.ai, localhost, etc.)
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# NSE headers to mimic browser
NSE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9',
}

def get_nse_session():
    """Create session with cookies"""
    session = requests.Session()
    session.headers.update(NSE_HEADERS)
    try:
        # Get cookies first
        session.get('https://www.nseindia.com', timeout=10)
    except Exception as e:
        print(f"Warning: Could not get NSE cookies: {e}")
    return session

def fetch_nifty_data():
    """Fetch Nifty 50 current price and option chain"""
    try:
        session = get_nse_session()
        
        # Get Nifty spot price and option chain
        url = 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY'
        print(f"Fetching from NSE: {url}")
        
        response = session.get(url, timeout=15)
        print(f"NSE Response Status: {response.status_code}")
        
        if response.status_code != 200:
            raise Exception(f"NSE returned status code: {response.status_code}")
        
        data = response.json()
        
        # Extract relevant data
        records = data.get('records', {})
        underlying_value = records.get('underlyingValue', 0)
        option_data = records.get('data', [])
        
        print(f"Nifty Price: {underlying_value}")
        print(f"Options found: {len(option_data)}")
        
        # Parse options
        options = []
        for item in option_data:
            # Call option
            if 'CE' in item:
                ce = item['CE']
                options.append({
                    'strike': ce.get('strikePrice'),
                    'type': 'CE',
                    'expiry': ce.get('expiryDate'),
                    'ltp': ce.get('lastPrice', 0),
                    'iv': ce.get('impliedVolatility', 0),
                    'delta': ce.get('delta', 0.5),  # NSE doesn't provide, using default
                    'gamma': ce.get('gamma', 0.001),
                    'theta': ce.get('theta', -2),
                    'vega': ce.get('vega', 10),
                    'volume': ce.get('totalTradedVolume', 0),
                    'oi': ce.get('openInterest', 0),
                    'oi_change': ce.get('changeinOpenInterest', 0),
                    'bid': ce.get('bidprice', 0),
                    'ask': ce.get('askprice', 0)
                })
            
            # Put option
            if 'PE' in item:
                pe = item['PE']
                options.append({
                    'strike': pe.get('strikePrice'),
                    'type': 'PE',
                    'expiry': pe.get('expiryDate'),
                    'ltp': pe.get('lastPrice', 0),
                    'iv': pe.get('impliedVolatility', 0),
                    'delta': pe.get('delta', -0.5),
                    'gamma': pe.get('gamma', 0.001),
                    'theta': pe.get('theta', -2),
                    'vega': pe.get('vega', 10),
                    'volume': pe.get('totalTradedVolume', 0),
                    'oi': pe.get('openInterest', 0),
                    'oi_change': pe.get('changeinOpenInterest', 0),
                    'bid': pe.get('bidprice', 0),
                    'ask': pe.get('askprice', 0)
                })
        
        result = {
            'nifty_price': underlying_value,
            'nifty_change': 0,
            'options': options,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"Returning {len(options)} options")
        return result
        
    except Exception as e:
        print(f"ERROR fetching NSE data: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

@app.route('/api/nifty-data', methods=['GET', 'OPTIONS'])
def get_nifty_options():
    """API endpoint to get Nifty data"""
    
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return '', 204
    
    print("\n=== API Request Received ===")
    data = fetch_nifty_data()
    
    if data:
        print("=== Sending successful response ===")
        return jsonify(data)
    else:
        print("=== Sending error response ===")
        return jsonify({'error': 'Failed to fetch NSE data'}), 500

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    """Health check endpoint"""
    if request.method == 'OPTIONS':
        return '', 204
    
    print("Health check requested")
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'message': 'NSE Data Server is running'
    })

@app.route('/', methods=['GET'])
def home():
    """Home endpoint"""
    return jsonify({
        'status': 'running',
        'endpoints': {
            'health': '/api/health',
            'nifty_data': '/api/nifty-data'
        }
    })

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  NSE DATA SERVER STARTING")
    print("="*60)
    print(f"  Server URL: http://localhost:5000")
    print(f"  Health Check: http://localhost:5000/api/health")
    print(f"  Nifty Data: http://localhost:5000/api/nifty-data")
    print("="*60 + "\n")
    
    # Run with specific settings
    app.run(
        host='0.0.0.0',  # Allow external connections
        port=5000,
        debug=True,
        threaded=True
    )