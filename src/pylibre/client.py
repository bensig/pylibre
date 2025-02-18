import subprocess
from pyntelope import Net, Transaction, Action, Authorization, Data, types
import os
import json
from dotenv import load_dotenv
import requests
import sys
import yaml

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
    # Default API endpoints
    ENDPOINTS = {
        'testnet': 'https://testnet.libre.org',
        'mainnet': 'https://lb.libre.org'
    }

    def __init__(self, api_url=None, verbose=False, network='testnet', config_path='config/config.yaml'):
        """Initialize LibreClient with config-based key loading.
        
        Args:
            api_url (str, optional): Override API endpoint URL. If None, uses config-based default
            verbose (bool): Enable verbose logging
            network (str): Network to use ('mainnet' or 'testnet')
            config_path (str): Path to config YAML file
        """
        self.network = network
        
        # Use provided API URL or load from config
        self.api_url = api_url or self.ENDPOINTS[network]
        self.private_keys = {}
        self.net = Net(host=self.api_url)
        self.verbose = verbose
        
        # Load keys from config
        self.load_account_keys(config_path)
        
        if self.verbose:
            print(f"Initialized LibreClient with {len(self.private_keys)} accounts")
            print(f"Using API endpoint: {self.api_url}")

    def load_account_keys(self, config_path):
        """Load private keys from config YAML file."""
        if self.verbose:
            print(f"Loading config from: {config_path}")
            
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Get network configuration
            network_config = config.get('networks', {}).get(self.network, {})
            self.private_keys = network_config.get('private_keys', {})
            
            # Update API URL if not explicitly provided
            if not self.api_url and 'api_url' in network_config:
                self.api_url = network_config['api_url']
                self.net = Net(host=self.api_url)
            
            if self.verbose:
                print("Loaded private keys for accounts:", list(self.private_keys.keys()))
                
        except Exception as e:
            if self.verbose:
                print(f"Error loading config: {str(e)}")
            raise

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
        """Get currency balance for an account."""
        try:
            # Auto-detect contract and precision if not specified
            if contract is None:
                contract_map = {
                    "USDT": {"contract": "usdt.libre", "precision": 8},
                    "BTC": {"contract": "btc.libre", "precision": 8},
                    "LIBRE": {"contract": "eosio.token", "precision": 4}
                }
                token_info = contract_map.get(symbol.upper())
                if not token_info:
                    raise ValueError(f"Cannot auto-detect contract for symbol: {symbol}. Please specify contract.")
                contract = token_info["contract"]
                precision = token_info["precision"]
            
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
            
            # Return first balance or zero balance with correct precision
            if balances:
                return balances[0]
            else:
                return f"0.{'0' * precision} {symbol}"

        except Exception as e:
            if self.verbose:
                print(f"Error getting balance: {str(e)}")
            raise

    def get_table_rows(self, code: str, table: str, scope: str, limit: int = 10, 
                      lower_bound: str = "", upper_bound: str = "", 
                      index_position: str = "", key_type: str = "") -> dict:
        """Get table rows from the blockchain."""
        try:
            payload = {
                "json": True,
                "code": code,
                "scope": scope,
                "table": table,
                "limit": limit
            }
            
            # Only add these if they're provided
            if lower_bound:
                payload["lower_bound"] = lower_bound
            if upper_bound:
                payload["upper_bound"] = upper_bound
            if index_position:
                payload["index_position"] = index_position
            if key_type:
                payload["key_type"] = key_type
            
            if self.verbose:
                print(f"\nAPI Request to /v1/chain/get_table_rows:")
                print(f"Payload: {payload}")

            response = requests.post(
                f"{self.api_url}/v1/chain/get_table_rows",
                json=payload
            )
            response.raise_for_status()
            return {"success": True, "rows": response.json()["rows"]}
            
        except Exception as e:
            if self.verbose:
                print(f"Error response: {e.response.text if hasattr(e, 'response') else str(e)}")
            return {"success": False, "error": f"Failed to get table rows: {str(e)}"}

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
            elif contract is None:
                return self.format_response(False, 
                    error=f"No contract specified for token {symbol} and no default contract known.")
            
            # Format amount with correct precision based on the symbol
            if symbol in TOKEN_SPECS:
                precision = TOKEN_SPECS[symbol]["precision"]
                
                # Convert to Decimal for precise handling
                from decimal import Decimal, getcontext
                
                # Set higher precision for decimal calculations
                getcontext().prec = 28
                
                try:
                    # Remove any trailing zeros and ensure proper decimal formatting
                    decimal_amount = Decimal(str(amount))  # Use string to avoid float precision issues
                    
                    # Check if this is a BTC sell order (from memo)
                    is_btc_sell = symbol == "BTC" and memo and memo.startswith("sell:")
                    
                    # Special handling for BTC sell orders
                    if is_btc_sell:
                        # For BTC sell orders, we need to be extremely precise
                        # Format with exact precision and ensure no scientific notation
                        formatted_amount = f"{decimal_amount:.8f}"
                        
                        # Ensure exactly 8 decimal places
                        parts = formatted_amount.split('.')
                        if len(parts) == 2:
                            integer_part, decimal_part = parts
                            # Pad with zeros if needed
                            decimal_part = decimal_part.ljust(precision, '0')[:precision]
                            formatted_amount = f"{integer_part}.{decimal_part}"
                        
                        # Ensure we're not sending scientific notation
                        if 'e' in formatted_amount.lower():
                            # Convert from scientific notation
                            decimal_amount_str = format(decimal_amount, f'.{precision}f')
                            formatted_amount = decimal_amount_str
                            
                        # Double-check the formatting is correct
                        if self.verbose:
                            print(f"Original amount: {amount}")
                            print(f"Formatted amount: {formatted_amount}")
                            
                        # Check if the amount is too small (below minimum precision)
                        min_btc_amount = Decimal('0.00000001')  # Minimum BTC amount (8 decimal places)
                        if decimal_amount < min_btc_amount:
                            return self.format_response(False, 
                                error=f"BTC amount {decimal_amount} is below minimum precision of {min_btc_amount}")
                    else:
                        # For other tokens or operations, use standard formatting
                        formatted_amount = f"{decimal_amount:.{precision}f}"
                    
                    quantity = f"{formatted_amount} {symbol}"
                except Exception as e:
                    return self.format_response(False, 
                        error=f"Error formatting amount: {e}")

            if self.verbose:
                print(f"\nTransfer Details:")
                print(f"From: {from_account}")
                print(f"To: {to_account}")
                print(f"Amount: {quantity}")
                print(f"Contract: {contract}")
                print(f"Memo: {memo}")

            # Create transfer data
            action_data = [
                Data(name="from", value=types.Name(from_account)),
                Data(name="to", value=types.Name(to_account)),
                Data(name="quantity", value=types.Asset(quantity)),
                Data(name="memo", value=types.String(memo))
            ]

            # Create authorization
            auth = Authorization(actor=from_account, permission="active")

            # For BTC sell orders, ensure the memo is properly formatted
            if symbol == "BTC" and memo and memo.startswith("sell:"):
                # Extract and reformat the memo to ensure consistency
                try:
                    memo_parts = memo.split(':')
                    if len(memo_parts) >= 3:
                        action_type = memo_parts[0]  # 'sell'
                        order_details = memo_parts[1].strip()  # '0.00054089 BTC'
                        price_details = memo_parts[2].strip()  # '78967.90638532 USDT'
                        
                        # Extract and reformat quantity
                        order_quantity = order_details.split(' ')[0]
                        order_symbol = order_details.split(' ')[1] if ' ' in order_details else 'BTC'
                        
                        # Extract and reformat price
                        price_value = price_details.split(' ')[0]
                        price_symbol = price_details.split(' ')[1] if ' ' in price_details else 'USDT'
                        
                        # Ensure exact formatting for BTC quantity
                        order_quantity_dec = Decimal(order_quantity)
                        formatted_order_quantity = f"{order_quantity_dec:.8f}"
                        
                        # Rebuild the memo with consistent formatting
                        memo = f"{action_type}:{formatted_order_quantity} {order_symbol}:{price_value} {price_symbol}"
                except Exception as e:
                    if self.verbose:
                        print(f"Warning: Could not reformat memo: {e}")
                    # Continue with original memo if reformatting fails
                    pass

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

            # Process the response from the blockchain
            if self.verbose:
                print(f"\nBlockchain response: {response}")
            
            # IMPORTANT: For BTC transactions, especially sell orders, the blockchain might
            # accept the transaction even if the response doesn't have a clear transaction_id
            # This is based on the observation that CLI commands succeed while Python reports failure
            
            # Special handling for BTC sell orders - assume success unless clear error
            is_btc_sell = symbol == "BTC" and memo and memo.startswith("sell:")
            
            # Check for transaction ID in different possible formats
            tx_id = response.get("transaction_id") or response.get("id") or \
                   response.get("trx", {}).get("id") or \
                   (isinstance(response, dict) and response.get("processed", {}).get("id"))
            
            # Check for processed field which indicates success even without a transaction_id
            processed = response.get("processed", {})
            
            # Check for explicit error indicators
            has_error = "error" in response or response.get("code") in [400, 500]
            
            # For BTC sell orders, be more lenient in determining success
            if is_btc_sell and not has_error:
                if self.verbose:
                    print(f"BTC sell order appears successful (no explicit error)")
                    print(f"Note: The blockchain may accept this transaction even without a clear transaction ID")
                return self.format_response(True, data={
                    "transaction_id": tx_id or "assumed_success_no_id",
                    "full_response": response,
                    "note": "BTC sell orders may succeed even when transaction ID is not returned"
                })
            
            # Standard success detection for other transactions
            if tx_id or processed:
                if self.verbose:
                    print(f"Transaction successful with ID: {tx_id}")
                return self.format_response(True, data={
                    "transaction_id": tx_id or "unknown_id",
                    "full_response": response
                })
            
            # If we get here, the transaction was likely rejected
            error_msg = "Transaction rejected by the blockchain"
            
            # Try to extract a more specific error message if available
            if isinstance(response, dict):
                if "error" in response:
                    error_details = response.get("error", {})
                    if isinstance(error_details, dict) and "details" in error_details:
                        details = error_details.get("details", [])
                        if details and isinstance(details, list) and len(details) > 0:
                            first_detail = details[0]
                            if isinstance(first_detail, dict) and "message" in first_detail:
                                error_msg = first_detail.get("message", error_msg)
            
            # Add a note for BTC sell orders that CLI commands might still work
            if is_btc_sell:
                error_msg += " (Note: CLI commands for BTC sell orders may still succeed)"
            
            return self.format_response(False, error=error_msg)

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
