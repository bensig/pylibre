import os
import json
from dotenv import load_dotenv
import argparse
from .client import LibreClient


# Command-Line Interface (CLI)
def main():
    parser = argparse.ArgumentParser(description='Libre Blockchain Client')
    parser.add_argument('--env-file', default='.env.testnet', help='Environment file path')
    parser.add_argument('--contract', required=True, help='Contract account name')
    parser.add_argument('--action', required=True, help='Action name')
    parser.add_argument('--actor', required=True, help='Account executing the action')
    parser.add_argument('--symbol', help='Token symbol for balance check')
    parser.add_argument('--unlock', action='store_true', help='Unlock wallet before executing action')
    parser.add_argument('--index-position', help='Index position for table queries')
    parser.add_argument('--key-type', help='Key type for table queries')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--data', help='Action data as JSON string')
    group.add_argument('--get-balance', action='store_true', help='Get token balance')
    
    args = parser.parse_args()

    load_dotenv(args.env_file)
    api_url = os.getenv("API_URL")
    if not api_url:
        raise ValueError("Missing required environment variable: API_URL")

    client = LibreClient(api_url)
    client.load_account_keys(args.env_file)

    if args.unlock:
        unlock_result = client.unlock_wallet(args.actor, f"{args.actor}_wallet.pwd")
        if not unlock_result.get("success", False):
            print(json.dumps(unlock_result))
            return

    if args.get_balance:
        if not args.symbol:
            raise ValueError("--symbol is required with --get-balance")
        balance = client.get_currency_balance(args.contract, args.actor, args.symbol)
        print(json.dumps(balance))
        return

    if args.action == 'get_table':
        table_data = json.loads(args.data)
        if table_data.get("get_all", False):  # New flag to use get_table instead of get_table_rows
            rows = client.get_table(
                code=args.contract,
                table=table_data["table"],
                scope=table_data.get("scope", args.actor),
                index_position=table_data.get("index_position", args.index_position),
                key_type=table_data.get("key_type", args.key_type)
            )
        else:
            rows = client.get_table_rows(
                code=args.contract,
                table=table_data["table"],
                scope=table_data.get("scope", args.actor),
                limit=table_data.get("limit", 10),
                lower_bound=table_data.get("lower_bound", ""),
                upper_bound=table_data.get("upper_bound", ""),
                index_position=table_data.get("index_position", args.index_position),
                key_type=table_data.get("key_type", args.key_type),
                reverse=table_data.get("reverse", False)
            )
        print(json.dumps(rows))
        return

    action_data = json.loads(args.data)
    response = client.execute_action(
        contract=args.contract,
        action_name=args.action,
        data=action_data,
        actor=args.actor
    )
    print(json.dumps(response))

if __name__ == "__main__":
    main()
