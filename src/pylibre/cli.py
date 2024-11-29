import os
import json
from dotenv import load_dotenv
import argparse
from .client import LibreClient

def create_parser():
    parser = argparse.ArgumentParser(
        description='Libre Blockchain Client CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Global options (--api-url, --env-file) must come BEFORE the command:
    pylibre --api-url https://testnet.libre.org --env-file .env.custom balance usdt.libre bentester USDT

    # Command-specific options come AFTER the command:
    pylibre --api-url https://testnet.libre.org table reward.libre rewards bentester --limit 10

    # Available commands:
    
    # Get token balance
    pylibre balance usdt.libre bentester USDT

    # Get table data (with pagination)
    pylibre table reward.libre rewards bentester --limit 10

    # Get all table data
    pylibre table-all reward.libre rewards bentester

    # Execute contract action
    pylibre execute reward.libre updateall bentester '{"max_steps":"500"}'

    # Transfer tokens
    pylibre transfer usdt.libre bentester bentest2 "1.0000 USDT" "memo"
    """
    )

    # Global options
    parser.add_argument('--env-file', default='.env.testnet', 
                       help='Environment file path (default: .env.testnet)')
    parser.add_argument('--api-url', 
                       help='API URL (e.g., https://testnet.libre.org) - overrides API_URL from env file')
    parser.add_argument('--unlock', action='store_true',
                       help='Unlock wallet for the account (requires password file in .env)')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Balance command
    balance_parser = subparsers.add_parser('balance', help='Get token balance')
    balance_parser.add_argument('contract', help='Token contract (e.g., usdt.libre)')
    balance_parser.add_argument('account', help='Account to check')
    balance_parser.add_argument('symbol', help='Token symbol (e.g., USDT)')

    # Table command
    table_parser = subparsers.add_parser('table', help='Get table rows')
    table_parser.add_argument('contract', help='Contract account')
    table_parser.add_argument('table', help='Table name')
    table_parser.add_argument('scope', help='Table scope')
    table_parser.add_argument('--limit', type=int, default=10, help='Number of rows to fetch')
    table_parser.add_argument('--index-position', help='Index position for table queries')
    table_parser.add_argument('--key-type', help='Key type for table queries')

    # Table-all command
    table_all_parser = subparsers.add_parser('table-all', help='Get all table rows')
    table_all_parser.add_argument('contract', help='Contract account')
    table_all_parser.add_argument('table', help='Table name')
    table_all_parser.add_argument('scope', help='Table scope')
    table_all_parser.add_argument('--index-position', help='Index position for table queries')
    table_all_parser.add_argument('--key-type', help='Key type for table queries')

    # Execute command
    execute_parser = subparsers.add_parser('execute', help='Execute contract action')
    execute_parser.add_argument('contract', help='Contract account')
    execute_parser.add_argument('action', help='Action name')
    execute_parser.add_argument('actor', help='Account executing the action')
    execute_parser.add_argument('data', help='Action data as JSON string')

    # Transfer command
    transfer_parser = subparsers.add_parser('transfer', help='Transfer tokens')
    transfer_parser.add_argument('contract', help='Token contract')
    transfer_parser.add_argument('from_account', help='Sender account')
    transfer_parser.add_argument('to_account', help='Recipient account')
    transfer_parser.add_argument('quantity', help='Amount with symbol (e.g., "1.0000 USDT")')
    transfer_parser.add_argument('memo', nargs='?', default='', help='Transfer memo')

    return parser

def unlock_wallet_if_needed(client, args, account):
    """Helper function to unlock wallet if needed"""
    if args.unlock:
        result = client.unlock_wallet(account, f"{account}_wallet.pwd")
        if not result.get('success'):
            print(f"Error unlocking wallet: {result.get('error')}")
            return False
    return True

def print_usage():
    """Print usage information for the PyLibre CLI tool."""
    print("""PyLibre CLI - Interact with Libre blockchain

Usage:
    pylibre [--api-url URL] <command> [<args>...]

Commands:
    balance <contract> <account> <symbol>
        Get token balance
        Example: pylibre balance usdt.libre bentester USDT

    table <contract> <table> <scope> [--index <pos>] [--key-type <type>]
        Get table rows (paginated)
        Example: pylibre table stake.libre stake stake.libre

    table-all <contract> <table> <scope> [--index <pos>] [--key-type <type>]
        Get all table rows
        Example: pylibre table-all stake.libre stake stake.libre

    transfer <contract> <from> <to> <quantity> [memo]
        Transfer tokens
        Example: pylibre transfer usdt.libre bentester bentest3 "1.00000000 USDT" "memo"

    execute <contract> <action> <actor> <data>
        Execute contract action
        Example: pylibre execute reward.libre updateall bentester '{"max_steps":"500"}'

Options:
    --api-url URL    API endpoint URL [default: https://testnet.libre.org]
    --help          Show this help message

Note: For testnet operations, use --api-url https://testnet.libre.org
      For mainnet operations, use --api-url https://lb.libre.org
""")

def main():
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Load environment variables
    load_dotenv(args.env_file)
    api_url = args.api_url or os.getenv("API_URL")
    if not api_url:
        print("Error: API URL must be provided either through --api-url argument or API_URL environment variable")
        return 1

    client = LibreClient(api_url)
    client.load_account_keys(args.env_file)

    if args.command == 'balance':
        result = client.get_currency_balance(args.contract, args.account, args.symbol)
        print(json.dumps(result))

    elif args.command == 'table':
        result = client.get_table_rows(
            code=args.contract,
            table=args.table,
            scope=args.scope,
            limit=args.limit,
            index_position=args.index_position,
            key_type=args.key_type
        )
        print(json.dumps(result))

    elif args.command == 'table-all':
        result = client.get_table(
            code=args.contract,
            table=args.table,
            scope=args.scope,
            index_position=args.index_position,
            key_type=args.key_type
        )
        print(json.dumps(result))

    elif args.command == 'execute':
        if not unlock_wallet_if_needed(client, args, args.actor):
            return 1
        result = client.execute_action(
            contract=args.contract,
            action_name=args.action,
            data=json.loads(args.data),
            actor=args.actor
        )
        print(json.dumps(result))

    elif args.command == 'transfer':
        if not unlock_wallet_if_needed(client, args, args.from_account):
            return 1
        result = client.transfer(
            contract=args.contract,
            from_account=args.from_account,
            to_account=args.to_account,
            quantity=args.quantity,
            memo=args.memo
        )
        print(json.dumps(result))

if __name__ == "__main__":
    main()
