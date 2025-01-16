import requests
import json
from pathlib import Path
import yaml
import time
from datetime import datetime, timedelta

BINANCE_BASE_URL = "https://api.binance.com"
CREDENTIALS_PATH = Path("config/config.yaml")

# Add these at the top with other global variables
_ip_cache = {"result": None, "timestamp": None}
IP_CACHE_DURATION = timedelta(minutes=5)

def is_us_ip():
    """Check if the current IP address is from the United States.
    Returns:
        bool or None: True if US IP, False if non-US IP, None if unable to determine
    """
    global _ip_cache
    
    # Check cache first
    if _ip_cache["timestamp"]:
        if datetime.now() - _ip_cache["timestamp"] < IP_CACHE_DURATION:
            return _ip_cache["result"]
    
    ipinfo_token = get_ipinfo_token()
    if not ipinfo_token:
        print("Error: No IPInfo token found. Cannot verify IP location.")
        return None
        
    try:
        headers = {"Authorization": f"Bearer {ipinfo_token}"}
        response = requests.get("https://ipinfo.io/country", headers=headers)
        
        if response.status_code != 200:
            # Fallback to basic auth if header method fails
            response = requests.get("https://ipinfo.io/country", auth=(ipinfo_token, ""))
            
        if response.status_code == 429:
            print("Error: Rate limit exceeded for IP verification")
            return None
        elif response.status_code != 200:
            print(f"Error: Could not verify IP location (Status: {response.status_code})")
            return None
        
        country_code = response.text.strip()
        result = country_code == "US"
        
        # Cache the result
        _ip_cache["result"] = result
        _ip_cache["timestamp"] = datetime.now()
        
        return result
    except Exception as e:
        print(f"Error: Failed to check IP location: {e}")
        return None

def load_binance_credentials():
    """Load Binance API credentials from config.yaml"""
    try:
        if not CREDENTIALS_PATH.exists():
            print("Warning: config.yaml not found. Using public API endpoints only.")
            return None, None
            
        with open(CREDENTIALS_PATH) as f:
            config = yaml.safe_load(f)
            
        binance_config = config.get("binance", {})
        return binance_config.get("api_key"), binance_config.get("api_secret")
    except Exception as e:
        print(f"Error loading Binance credentials: {e}")
        return None, None

def get_ipinfo_token():
    """Load IPInfo token from config.yaml"""
    try:
        if not CREDENTIALS_PATH.exists():
            print(f"Error: Config file not found at {CREDENTIALS_PATH}")
            return None
            
        with open(CREDENTIALS_PATH) as f:
            config = yaml.safe_load(f)
            
        token = config.get("credentials", {}).get("ipinfo", {}).get("token")
        if not token:
            print("Error: IPInfo token not found in config.yaml")
            print("Expected path: credentials.ipinfo.token")
        else:
            print(f"Debug: Found IPInfo token: {token[:4]}...")
            
        return token
    except Exception as e:
        print(f"Error loading IPInfo token: {e}")
        return None

def fetch_btc_usdt_price():
    """Fetch the latest BTC/USDT price from Binance."""
    ip_check = is_us_ip()
    if ip_check is None:
        print("Error: Cannot proceed - IP location verification failed")
        return None
    if ip_check is True:
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
