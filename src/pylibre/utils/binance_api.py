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

def fetch_btc_usdt_price(bypass_ip_check=True, max_retries=3, retry_delay=2):
    """Fetch the latest BTC/USDT price from Binance.
    
    Args:
        bypass_ip_check (bool): If True, skip the IP location check (useful when using VPN)
        max_retries (int): Maximum number of retry attempts per endpoint
        retry_delay (int): Delay in seconds between retries
        
    Returns:
        float or None: Current BTC/USDT price or None if unavailable
    """
    # Only perform IP check if not bypassed (e.g., when not using VPN)
    if not bypass_ip_check:
        ip_check = is_us_ip()
        if ip_check is None:
            print("Warning: IP location verification failed, but proceeding anyway")
        elif ip_check is True:
            print("Warning: US IP detected, but proceeding anyway since bypass is enabled")
    
    # Try multiple endpoints in case one fails
    endpoints = [
        # Standard Binance API
        f"{BINANCE_BASE_URL}/api/v3/ticker/price?symbol=BTCUSDT",
        # Binance API v3 alternative endpoint
        f"{BINANCE_BASE_URL}/api/v3/avgPrice?symbol=BTCUSDT",
        # Fallback to Binance US if needed
        "https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT",
        # CoinGecko API as fallback
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
        # CoinAPI as a final fallback
        "https://rest.coinapi.io/v1/exchangerate/BTC/USD"
    ]
    
    # Record all attempts for diagnostic purposes
    attempts_log = []
    
    # Try each endpoint
    for endpoint in endpoints:
        endpoint_name = endpoint.split("/")[2]  # Extract domain name
        
        # Special case for CoinAPI which requires an API key
        if "coinapi.io" in endpoint:
            api_key = get_coinapi_key()
            if not api_key:
                attempts_log.append(f"{endpoint_name}: Skipped (No API key)")
                continue
            headers = {"X-CoinAPI-Key": api_key}
        else:
            headers = {}
        
        # Try multiple times for each endpoint
        for attempt in range(1, max_retries + 1):
            try:
                print(f"Fetching BTC/USDT price from {endpoint_name} (attempt {attempt}/{max_retries})")
                
                # Set a reasonable timeout
                response = requests.get(endpoint, headers=headers, timeout=5)
                response.raise_for_status()
                data = response.json()
                
                # Parse response based on the API format
                price = None
                if "binance.com" in endpoint or "binance.us" in endpoint:
                    if "price" in data:
                        price = float(data["price"])
                    elif "avgPrice" in data:
                        price = float(data["avgPrice"])
                elif "coingecko.com" in endpoint:
                    if "bitcoin" in data and "usd" in data["bitcoin"]:
                        price = float(data["bitcoin"]["usd"])
                elif "coinapi.io" in endpoint:
                    if "rate" in data:
                        price = float(data["rate"])
                
                if price is not None and price > 0:
                    print(f"Successfully fetched BTC/USDT price from {endpoint_name}: ${price:,.2f}")
                    return price
                else:
                    attempts_log.append(f"{endpoint_name} attempt {attempt}: Invalid price format: {data}")
                    break  # Try next endpoint if format is wrong
                
            except requests.exceptions.Timeout:
                attempts_log.append(f"{endpoint_name} attempt {attempt}: Timeout")
                # Retry this endpoint after delay
                time.sleep(retry_delay)
                continue
                
            except requests.exceptions.ConnectionError:
                attempts_log.append(f"{endpoint_name} attempt {attempt}: Connection Error")
                # Possible network issue, wait a bit longer
                time.sleep(retry_delay * 2)
                continue
                
            except Exception as e:
                attempts_log.append(f"{endpoint_name} attempt {attempt}: {str(e)}")
                # Wait before trying next attempt
                time.sleep(retry_delay)
                continue
    
    # If we get here, all endpoints and retries failed
    print("ERROR: All price fetching attempts failed:")
    for attempt in attempts_log:
        print(f"  - {attempt}")
    print("Unable to fetch current BTC price - please check your internet connection")
    
    # Try to load cached price from disk
    cached_price = load_cached_price()
    if cached_price:
        print(f"Using cached price from disk: ${cached_price:,.2f}")
        return cached_price
        
    # Don't return a fallback price by default - returning None indicates a failure
    # that should be handled by calling code
    return None

def get_coinapi_key():
    """Load CoinAPI key from config.yaml"""
    try:
        if not CREDENTIALS_PATH.exists():
            return None
            
        with open(CREDENTIALS_PATH) as f:
            config = yaml.safe_load(f)
            
        return config.get("credentials", {}).get("coinapi", {}).get("api_key")
    except Exception:
        return None
        
def load_cached_price():
    """Load the most recent BTC price from disk cache"""
    try:
        cache_file = Path("shared_data/btcusdt_price.json")
        if not cache_file.exists():
            return None
            
        # Check if the cache is too old (more than 24 hours)
        if time.time() - cache_file.stat().st_mtime > 86400:
            print("Cached price is more than 24 hours old, not using")
            return None
            
        with open(cache_file, "r") as f:
            data = json.load(f)
            
        if isinstance(data, dict) and "price" in data:
            return float(data["price"])
        return None
    except Exception as e:
        print(f"Error loading cached price: {e}")
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
