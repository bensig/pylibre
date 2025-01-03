import subprocess
from pyntelope import Net, Transaction, Action, Authorization, Data, types
import os
import json
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
    def __init__(self, api_url, verbose=False):
        self.api_url = api_url
        self.private_keys = {}
        self.net = Net(host=api_url)
        self.verbose = verbose

    def load_account_keys(self, env_file='.env.testnet'):
        """Load private keys from an environment file."""
        if self.verbose:
            print(f"Loading environment from: {env_file}")
        load_dotenv(env_file)
        
        # Print all environment variables starting with ACCOUNT_
        if self.verbose:
            for key in os.environ:
                if key.startswith("ACCOUNT_"):
                    print(f"Found key: {key}")
            
        self.private_keys = {
            key.replace("ACCOUNT_", "").lower(): os.getenv(key)
            for key in os.environ if key.startswith("ACCOUNT_")
        }
        
        # Print the loaded private keys (with keys masked)
        if self.verbose:
            print("Loaded private keys for accounts:", list(self.private_keys.keys()))

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

    def get_currency_balance(self, account, symbol, contract=None):
        """Get currency balance for an account.
        
        Args:
            account (str): Account name
            symbol (str): Token symbol (e.g., "USDT", "BTC", "LIBRE")
            contract (str, optional): Token contract. If not specified, will be auto-detected:
                - USDT: usdt.libre
                - BTC: btc.libre
                - LIBRE: eosio.token
        """
        try:
            # Auto-detect contract if not specified
            if contract is None:
                contract_map = {
                    "USDT": "usdt.libre",
                    "BTC": "btc.libre",
                    "LIBRE": "eosio.token"
                }
                contract = contract_map.get(symbol)
                if not contract:
                    raise ValueError(f"Cannot auto-detect contract for symbol: {symbol}. Please specify contract.")
            
            if self.verbose:
                print(f"Using contract: {contract} for symbol: {symbol}")

            response = requests.post(
                f"{self.api_url}/v1/chain/get_currency_balance",
                json={
                    "code": contract,
                    "account": account,
                    "symbol": symbol
                }
            )
            response.raise_for_status()
            balances = response.json()
            
            # Return first balance or zero balance if none found
            if balances:
                return balances[0]
            else:
                decimals = 4 if symbol == "LIBRE" else 8
                return f"0.{'0' * decimals} {symbol}"

        except Exception as e:
            if self.verbose:
                print(f"Error getting balance: {str(e)}")
            raise

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
        """Execute a contract action using pyntelope."""
        try:
            # Convert data to pyntelope format
            action_data = [
                Data(name=key, value=self._convert_to_pyntelope_type(value))
                for key, value in data.items()
            ]

            # Create authorization
            auth = Authorization(actor=actor, permission=permission)

            # Create action
            action = Action(
                account=contract,
                name=action_name,
                data=action_data,
                authorization=[auth]
            )

            # Create and link transaction
            transaction = Transaction(actions=[action])
            linked_transaction = transaction.link(net=self.net)

            # Get private key for actor
            private_key = self.private_keys.get(actor)
            if not private_key:
                raise Exception(f"No private key found for account {actor}")

            # Sign and send transaction
            signed_transaction = linked_transaction.sign(key=private_key)
            response = signed_transaction.send()

            return self.format_response(True, data={
                "transaction_id": response.get("transaction_id")
            })

        except Exception as e:
            return self.format_response(False, error=str(e))

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
        """Execute a transfer action using pyntelope."""
        try:
            # Parse quantity to get amount and symbol
            parts = quantity.strip().split(' ')
            if len_parts := len(parts) != 2:
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

            # Create transfer data
            action_data = [
                Data(name="from", value=types.Name(from_account)),
                Data(name="to", value=types.Name(to_account)),
                Data(name="quantity", value=types.Asset(quantity)),
                Data(name="memo", value=types.String(memo))
            ]

            # Create authorization
            auth = Authorization(actor=from_account, permission="active")

            # Create action
            action = Action(
                account=contract,
                name="transfer",
                data=action_data,
                authorization=[auth]
            )

            # Create and link transaction
            transaction = Transaction(actions=[action])
            linked_transaction = transaction.link(net=self.net)

            # Get private key for from_account
            private_key = self.private_keys.get(from_account)
            if not private_key:
                raise Exception(f"No private key found for account {from_account}")

            # Sign and send transaction
            signed_transaction = linked_transaction.sign(key=private_key)
            response = signed_transaction.send()

            return self.format_response(True, data={
                "transaction_id": response.get("transaction_id")
            })

        except Exception as e:
            return self.format_response(False, error=str(e))

    def _convert_to_pyntelope_type(self, value):
        """Helper method to convert Python values to pyntelope types."""
        if isinstance(value, str):
            if value.replace(".", "").isdigit():  # Looks like a number
                if "." in value:
                    return types.Float64(float(value))
                return types.Int64(int(value))
            if " " in value and value.split()[1] in ["USDT", "BTC", "LIBRE"]:  # Looks like an asset
                return types.Asset(value)
            return types.String(value)
        if isinstance(value, int):
            return types.Int64(value)
        if isinstance(value, float):
            return types.Float64(value)
        if isinstance(value, bool):
            return types.Bool(value)
        if isinstance(value, dict):
            return types.Object({k: self._convert_to_pyntelope_type(v) for k, v in value.items()})
        if isinstance(value, list):
            return types.Array([self._convert_to_pyntelope_type(v) for v in value])
        return value

    def get_currency_stats(self, contract, symbol):
        """Get currency statistics for a token.
        
        Args:
            contract (str): Token contract (e.g., "eosio.token", "usdt.libre")
            symbol (str): Token symbol (e.g., "LIBRE", "USDT")
        
        Returns:
            dict: Token statistics including supply, max supply, and issuer
        """
        try:
            response = requests.post(
                f"{self.api_url}/v1/chain/get_currency_stats",
                json={
                    "code": contract,
                    "symbol": symbol
                }
            )
            response.raise_for_status()
            stats = response.json()
            
            # Return the stats for the symbol or empty dict if not found
            return stats.get(symbol, {})

        except Exception as e:
            if self.verbose:
                print(f"Error getting currency stats: {str(e)}")
            return self.format_response(False, error=str(e))

    def push_action(self, contract: str, action: str, data: dict, account: str, permission: str = "active"):
        """Execute any contract action using pyntelope.
        
        Args:
            contract (str): Contract account name
            action (str): Action name
            data (dict): Action data
            account (str): Account executing the action
            permission (str): Permission to use (default: "active")
        """
        return self.execute_action(
            contract=contract,
            action_name=action,
            data=data,
            actor=account,
            permission=permission
        )
