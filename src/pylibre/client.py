import os
import json
import subprocess
from dotenv import load_dotenv
import requests
import sys

def extract_error_message(error_json):
    """Extract the relevant error message from a JSON error response"""
    try:
        # Handle blockchain error responses
        if isinstance(error_json, dict):
            # Check for processed transaction errors
            processed = error_json.get('processed', {})
            except_data = processed.get('except', {})
            stack = except_data.get('stack', [])
            
            if stack and isinstance(stack, list):
                for item in stack:
                    if item.get('context', {}).get('level') == 'error':
                        return item.get('data', {}).get('s')
            
            # Check for action trace errors
            traces = processed.get('action_traces', [])
            if traces:
                for trace in traces:
                    if 'except' in trace:
                        if 'stack' in trace['except']:
                            for stack_item in trace['except']['stack']:
                                if 'data' in stack_item and 's' in stack_item['data']:
                                    return stack_item['data']['s']
                        if 'message' in trace['except']:
                            return trace['except']['message']
            
            # Check for simple error message
            if 'message' in error_json:
                return error_json['message']
            
        return str(error_json)
    except:
        return str(error_json)

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

    def format_response(self, success, data=None, error=None):
        """Standardize response format across all methods"""
        response = {"success": success}
        if success and data is not None:
            response["data"] = data
        if not success and error is not None:
            if isinstance(error, str):
                try:
                    error_obj = json.loads(error)
                    response["error"] = extract_error_message(error_obj)
                except:
                    response["error"] = error
            else:
                response["error"] = str(error)
        return response

    def get_currency_balance(self, contract, account, symbol):
        """
        Fetch token balance for an account.
        
        Automatically handles common tokens if contract is None:
        - "BTC": contract="btc.libre"
        - "USDT": contract="usdt.libre"
        - "LIBRE": contract="eosio.token"
        """
        try:
            # Define token specifications
            TOKEN_SPECS = {
                "BTC": {"contract": "btc.libre"},
                "USDT": {"contract": "usdt.libre"},
                "LIBRE": {"contract": "eosio.token"}
            }
            
            # If no contract specified, try to determine from symbol
            if contract is None and symbol in TOKEN_SPECS:
                contract = TOKEN_SPECS[symbol]["contract"]
            elif contract is None:
                raise Exception(f"No contract specified for token {symbol} and no default contract known.")

            response = requests.post(
                f"{self.api_url}/v1/chain/get_currency_balance",
                json={"code": contract, "account": account, "symbol": symbol}
            )
            response.raise_for_status()
            balances = response.json()
            
            # API returns a list of balances
            if not isinstance(balances, list):
                return self.format_response(False, error="Unexpected response format from API")
            
            # If no balance found, return 0
            if len(balances) == 0:
                return f"0.00000000 {symbol}"
            
            # Return the first matching balance directly
            return balances[0]
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get balance: {str(e)}")

    def get_table_rows(self, code, table, scope, limit=10, lower_bound="", upper_bound="", 
                      index_position="", key_type="", reverse=False):
        """Fetch rows from a smart contract table."""
        payload = {
            "code": code,
            "table": table,
            "scope": scope,
            "limit": limit,
            "json": True,
            "reverse": reverse,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound
        }
        
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
            result = response.json()
            return result.get("rows", [])  # Return rows directly
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get table rows: {str(e)}")

    def execute_action(self, contract, action_name, data, actor, permission="active"):
        """Execute a contract action."""
        try:
            cmd = [
                "cleos", "-u", self.api_url,
                "push", "action", contract, action_name,
                json.dumps(data),
                "-p", f"{actor}@{permission}",
                "--json",
                "-x", "60"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            try:
                response = json.loads(result.stdout)
                return self.format_response(True, data={
                    "transaction_id": response.get("transaction_id")
                })
            except:
                return self.format_response(True)
            
        except subprocess.CalledProcessError as e:
            return self.format_response(False, error=e.stdout or e.stderr)

    def unlock_wallet(self, wallet_name, wallet_password_file):
        """Unlock a wallet using its password file."""
        try:
            # Open wallet first
            subprocess.run(["cleos", "wallet", "open", "-n", wallet_name], 
                          capture_output=True, check=True)
            
            # Unlock wallet
            with open(wallet_password_file, "r") as f:
                password = f.read().strip()
            
            unlock_cmd = ["cleos", "wallet", "unlock", "-n", wallet_name, "--password", password]
            result = subprocess.run(unlock_cmd, capture_output=True, text=True, check=True)
            
            return self.format_response(True)
        except FileNotFoundError:
            return self.format_response(False, error=f"Wallet password file not found: {wallet_password_file}")
        except subprocess.CalledProcessError as e:
            return self.format_response(False, error=e.stderr.strip())

    def get_table(self, code, table, scope, index_position="", key_type=""):
        """Fetch all rows from a smart contract table by paginating through it."""
        all_rows = []
        more = True
        next_lower_bound = ""
        total_rows = 0
        
        try:
            while more:
                try:
                    print(f"\rFetching rows... (found {total_rows} so far)", 
                          end="", flush=True, file=sys.stderr)
                    
                    response = requests.post(
                        f"{self.api_url}/v1/chain/get_table_rows",
                        json={
                            "code": code,
                            "table": table,
                            "scope": scope,
                            "limit": 1000,
                            "lower_bound": next_lower_bound,
                            "upper_bound": "",
                            "json": True,
                            **({"index_position": index_position} if index_position else {}),
                            **({"key_type": key_type} if key_type else {})
                        },
                        timeout=10
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    rows = result.get("rows", [])
                    all_rows.extend(rows)
                    total_rows += len(rows)
                    
                    more = result.get("more", False)
                    if more:
                        next_lower_bound = result.get("next_key")
                        if not next_lower_bound:
                            break
                        
                except requests.exceptions.RequestException as e:
                    print(f"\nError fetching rows: {str(e)}", file=sys.stderr)
                    raise Exception(f"Failed to get table: {str(e)}")
                
            print(f"\nFetched {total_rows} rows total", file=sys.stderr)
            return all_rows  # Return rows directly
            
        except KeyboardInterrupt:
            print(f"\nFetch interrupted. Returning {total_rows} rows that were collected", 
                  file=sys.stderr)
            return all_rows

    def transfer(self, from_account, to_account, quantity, memo="", contract=None):
        """
        Execute a transfer action on the blockchain.
        
        Automatically handles common tokens:
        - "BTC": 8 decimals, contract="btc.libre"
        - "USDT": 8 decimals, contract="usdt.libre"
        - "LIBRE": 4 decimals, contract="eosio.token"
        
        Args:
            from_account (str): Sender account
            to_account (str): Recipient account
            quantity (str): Amount with symbol (e.g., "1.00000000 USDT")
            memo (str): Transfer memo
            contract (str, optional): Override the default contract for the token
        
        Returns:
            dict: {
                "success": bool,
                "transaction_id": str | None,
                "error": str | None
            }
        """
        try:
            # Parse quantity to get amount and symbol
            parts = quantity.strip().split(' ')
            if len(parts) != 2:
                return self.format_response(False, 
                    error=f"Invalid quantity format. Expected 'amount SYMBOL' but got: {quantity}")
            
            amount, symbol = parts
            
            # Define token specifications
            TOKEN_SPECS = {
                "BTC": {"contract": "btc.libre", "precision": 8},
                "USDT": {"contract": "usdt.libre", "precision": 8},
                "LIBRE": {"contract": "eosio.token", "precision": 4}
            }
            
            # If no contract specified, try to determine from symbol
            if contract is None and symbol in TOKEN_SPECS:
                contract = TOKEN_SPECS[symbol]["contract"]
                # Format amount to correct precision
                amount = f"{float(amount):.{TOKEN_SPECS[symbol]['precision']}f}"
                quantity = f"{amount} {symbol}"
            elif contract is None:
                return self.format_response(False, 
                    error=f"No contract specified for token {symbol} and no default contract known.")
            
            # Execute the transfer
            return self.execute_action(
                contract=contract,
                action_name="transfer",
                data={
                    "from": from_account,
                    "to": to_account,
                    "quantity": quantity,
                    "memo": memo
                },
                actor=from_account
            )
            
        except Exception as e:
            return self.format_response(False, error=str(e))
