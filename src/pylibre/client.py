import os
import json
import subprocess
from dotenv import load_dotenv
import requests

class LibreClient:
    def __init__(self, api_url):
        self.api_url = api_url
        self.private_keys = {}

    def load_account_keys(self, env_file='.env.testnet'):
        """Load private keys from an environment file."""
        load_dotenv(env_file)
        self.private_keys = {
            key.replace("ACCOUNT_", "").lower(): os.getenv(key)
            for key in os.environ if key.startswith("ACCOUNT_")
        }

    def get_currency_balance(self, contract, account, symbol):
        """Fetch token balance for an account."""
        try:
            response = requests.post(
                f"{self.api_url}/v1/chain/get_currency_balance",
                json={"code": contract, "account": account, "symbol": symbol}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}

    def get_table_rows(self, code, table, scope, limit=10, lower_bound="", upper_bound="", 
                      index_position="", key_type="", reverse=False):
        """Fetch rows from a smart contract table."""
        payload = {
            "code": code,
            "table": table,
            "scope": scope,
            "limit": limit,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "reverse": reverse,
            "json": True
        }
        
        # Only add index_position and key_type if they are provided
        if index_position:
            payload["index_position"] = index_position
        if key_type:
            payload["key_type"] = key_type

        try:
            response = requests.post(
                f"{self.api_url}/v1/chain/get_table_rows",
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            return response.json().get("rows", [])
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}

    def execute_action(self, contract, action_name, data, actor, permission="active"):
        try:
            process = subprocess.run(
                ["cleos", "-u", self.api_url, "push", "action", contract, action_name, json.dumps(data),
                "-p", f"{actor}@{permission}", "--json", "-x", "60"],
                capture_output=True, text=True, check=False
            )
            if process.returncode != 0:
                return {"success": False, "error": process.stderr.strip() or "Unknown error"}

            # Attempt to parse JSON response
            try:
                result = json.loads(process.stdout)
                return {"success": True, "transaction_id": result.get("transaction_id")}
            except json.JSONDecodeError:
                return {"success": False, "error": f"Invalid JSON response: {process.stdout}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def unlock_wallet(self, wallet_name, wallet_password_file):
        """Unlock a wallet using its password file."""
        try:
            # Open wallet first
            subprocess.run(["cleos", "wallet", "open", "-n", wallet_name], check=True)
            # Unlock wallet
            with open(wallet_password_file, "r") as f:
                password = f.read().strip()
            subprocess.run(
                ["cleos", "wallet", "unlock", "-n", wallet_name, "--password", password],
                check=True
            )
            return {"success": True}
        except FileNotFoundError:
            return {"success": False, "error": f"Wallet password file not found: {wallet_password_file}"}
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": e.stderr.strip()}

    def get_table(self, code, table, scope, index_position="", key_type=""):
        """Fetch all rows from a smart contract table by paginating through it."""
        all_rows = []
        more = True
        next_lower_bound = ""
        
        while more:
            try:
                response = requests.post(
                    f"{self.api_url}/v1/chain/get_table_rows",
                    json={
                        "code": code,
                        "table": table,
                        "scope": scope,
                        "limit": 1000,  # Maximum limit per request
                        "lower_bound": next_lower_bound,
                        "upper_bound": "",
                        "json": True,
                        **({"index_position": index_position} if index_position else {}),
                        **({"key_type": key_type} if key_type else {})
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                all_rows.extend(result.get("rows", []))
                more = result.get("more", False)
                
                if more:
                    next_lower_bound = result.get("next_key")
                    if not next_lower_bound:
                        break  # Safety check in case next_key is not provided
                        
            except requests.exceptions.RequestException as e:
                return {"success": False, "error": str(e)}
                
        return all_rows