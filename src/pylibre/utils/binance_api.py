import requests
import json
from pathlib import Path

BINANCE_BASE_URL = "https://api.binance.com"
CREDENTIALS_PATH = Path("credentials.json")

def is_us_ip():
    """Check if the current IP address is from the United States"""
    ipinfo_token = get_ipinfo_token()
    if not ipinfo_token:
        print("Warning: No IPInfo token found. Assuming non-US IP.")
        return False
        
    try:
        headers = {"Authorization": f"Bearer {ipinfo_token}"}
        response = requests.get("https://ipinfo.io/country", headers=headers)
        
        if response.status_code != 200:
            # Fallback to basic auth if header method fails
            response = requests.get("https://ipinfo.io/country", auth=(ipinfo_token, ""))
        
        country_code = response.text.strip()
        return country_code == "US"
    except Exception as e:
        print(f"Error checking IP location: {e}")
        return True  # Fail safe: assume US if can't verify

def load_binance_credentials():
    """Load Binance API credentials from credentials.json"""
    try:
        if not CREDENTIALS_PATH.exists():
            print("Warning: credentials.json not found. Using public API endpoints only.")
            return None, None
            
        with open(CREDENTIALS_PATH) as f:
            creds = json.load(f)
            
        binance_creds = creds.get("binance", {})
        return binance_creds.get("api_key"), binance_creds.get("api_secret")
    except Exception as e:
        print(f"Error loading Binance credentials: {e}")
        return None, None

def get_ipinfo_token():
    """Load IPInfo token from credentials.json"""
    try:
        if not CREDENTIALS_PATH.exists():
            return None
            
        with open(CREDENTIALS_PATH) as f:
            creds = json.load(f)
            
        return creds.get("ipinfo", {}).get("token")
    except Exception as e:
        print(f"Error loading IPInfo token: {e}")
        return None

def fetch_btc_usdt_price():
    """Fetch the latest BTC/USDT price from Binance."""
    if is_us_ip():
        print("Error: Cannot access Binance API from US IP addresses")
        return None
        
    try:
        response = requests.get(f"{BINANCE_BASE_URL}/api/v3/ticker/price", params={"symbol": "BTCUSDT"})
        response.raise_for_status()
        data = response.json()
        return float(data["price"])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching price: {e}")
        return None

if __name__ == "__main__":
    # Test the price fetching
    price = fetch_btc_usdt_price()
    if price:
        print(f"Current BTC/USDT price: ${price:,.2f}")
    else:
        print("Failed to fetch BTC price")
    
    # Test credentials loading
    api_key, api_secret = load_binance_credentials()
    if api_key and api_secret:
        print("✅ Credentials loaded successfully")
    else:
        print("❌ No credentials found or error loading credentials")
