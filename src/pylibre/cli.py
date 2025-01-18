import os
import json
import argparse
from .client import LibreClient
import sys
from .dex import DexClient

def create_parser():
    parser = argparse.ArgumentParser(
        description='Libre Blockchain Client CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Global options (--api-url, --network, --config) must come BEFORE the command
    
    # Get token balance
    pylibre balance bentester USDT
    
    # Get table data with filtering
    pylibre table farm.libre account BTCUSD --lower-bound cesarcv
    """
    )

    # Global options
    parser.add_argument('--config', default='config/config.yaml', 
                       help='Config file path (default: config/config.yaml)')
    parser.add_argument('--network', default='testnet',
                       choices=['mainnet', 'testnet'],
                       help='Network to use (default: testnet)')
    parser.add_argument('--api-url', 
                       help='Override API URL (e.g., https://testnet.libre.org)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Balance command
    balance_parser = subparsers.add_parser('balance', 
        help='Get token balance',
        description="""
        Get token balance for an account. Contract is optional for common tokens:
        - USDT: usdt.libre (8 decimals)
        - BTC: btc.libre (8 decimals)
        - LIBRE: eosio.token (4 decimals)
        
        Examples:
          # Check balance with auto-detected contract
          pylibre balance bentester USDT
          
          # Check balance with explicit contract
          pylibre balance --contract eosio.token bentester LIBRE
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    balance_parser.add_argument('--contract', help='Token contract (optional for USDT/BTC/LIBRE)')
    balance_parser.add_argument('account', help='Account to check')
    balance_parser.add_argument('symbol', help='Token symbol (e.g., USDT)')

    # Table command
    table_parser = subparsers.add_parser('table', 
        help='Query table data from smart contracts (paginated)',
        description="""
        Query table data from smart contracts with optional filtering.
        Note: This command returns a maximum of 10 rows by default.
        Use --limit to fetch more rows, or use 'table-all' command to fetch all rows.
        
        Examples:
          # Get default 10 rows
          pylibre table stake.libre stake stake.libre
          
          # Get filtered rows with pagination
          pylibre table stake.libre stake stake.libre --limit 100 --lower-bound 1 --upper-bound 1
          
          # Get rows using secondary index
          pylibre table farm.libre account BTCUSD --limit 1 --lower-bound cesarcv --upper-bound cesarcv --index-position primary --key-type name
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    table_parser.add_argument('contract', help='Contract account (e.g., farm.libre)')
    table_parser.add_argument('table', help='Table name (e.g., account)')
    table_parser.add_argument('scope', help='Table scope (e.g., BTCUSD)')
    table_parser.add_argument('--limit', type=int, help='Number of rows to fetch')
    table_parser.add_argument('--lower-bound', help='Lower bound for table query')
    table_parser.add_argument('--upper-bound', help='Upper bound for table query')
    table_parser.add_argument('--index-position', help='Index position for table queries (e.g., primary)')
    table_parser.add_argument('--key-type', help='Key type for table queries (e.g., name)')

    # Table-all command
    table_all_parser = subparsers.add_parser('table-all', 
        help='Get all rows from a table (auto-pagination)',
        description="""
        Fetch all rows from a smart contract table by automatically handling pagination.
        This is useful when you need to retrieve the complete table contents.
        Progress will be displayed while fetching.
        
        Examples:
          # Get all rows from a table
          pylibre table-all stake.libre stake stake.libre
          
          # Get all rows using a secondary index
          pylibre table-all stake.libre stake stake.libre --index-position 2 --key-type name
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
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
    transfer_parser = subparsers.add_parser('transfer', 
        help='Transfer tokens',
        description="""
        Transfer tokens between accounts. Contract is optional for common tokens:
        - USDT: usdt.libre (8 decimals)
        - BTC: btc.libre (8 decimals)
        - LIBRE: eosio.token (4 decimals)
        
        Examples:
          # Transfer with auto-detected contract
          pylibre transfer bentester bentest3 "1.00000000 USDT"
          
          # Transfer with explicit contract and memo
          pylibre transfer --contract usdt.libre bentester bentest3 "1.00000000 USDT" "memo"
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    transfer_parser.add_argument('from_account', help='Sender account')
    transfer_parser.add_argument('to_account', help='Recipient account')
    transfer_parser.add_argument('quantity', help='Amount with symbol (e.g., "1.00000000 USDT")')
    transfer_parser.add_argument('memo', nargs='?', default="", help='Transfer memo (optional)')
    transfer_parser.add_argument('--contract', help='Token contract (optional for USDT/BTC/LIBRE)')

    # DEX commands
    dex_parser = subparsers.add_parser('dex', help='DEX operations')
    dex_subparsers = dex_parser.add_subparsers(dest='dex_command', help='DEX commands')
    
    # DEX orderbook command
    orderbook_parser = dex_subparsers.add_parser('orderbook', 
        help='Get DEX orderbook',
        description="Get the current orderbook for a trading pair"
    )
    orderbook_parser.add_argument('base_symbol', help='Base token symbol (e.g., LIBRE)')
    orderbook_parser.add_argument('quote_symbol', help='Quote token symbol (e.g., BTC)')
    
    # DEX order command
    order_parser = dex_subparsers.add_parser('order', 
        help='Place order on DEX',
        description="Place a buy or sell order on the DEX"
    )
    order_parser.add_argument('account', help='Trading account')
    order_parser.add_argument('order_type', choices=['buy', 'sell'], help='Order type')
    order_parser.add_argument('quantity', help='Amount to trade')
    order_parser.add_argument('base_symbol', help='Base token symbol (e.g., LIBRE)')
    order_parser.add_argument('quote_symbol', help='Quote token symbol (e.g., BTC)')
    order_parser.add_argument('price', help='Price per unit')

    return parser

def print_usage():
    """Print usage information for the PyLibre CLI tool."""
    print("""PyLibre CLI - Interact with Libre blockchain

Usage:
    pylibre [--network <network>] [--api-url URL] <command> [<args>...]

Commands:
    balance <account> <symbol>
        Get token balance
        Example: pylibre balance bentester USDT

    table <contract> <table> <scope> [--index <pos>] [--key-type <type>]
        Get table rows (paginated)
        Example: pylibre table stake.libre stake stake.libre

    table-all <contract> <table> <scope> [--index <pos>] [--key-type <type>]
        Get all table rows
        Example: pylibre table-all stake.libre stake stake.libre

    transfer <from> <to> <quantity> [memo]
        Transfer tokens
        Example: pylibre transfer bentester bentest3 "1.00000000 USDT" "memo"

    execute <contract> <action> <actor> <data>
        Execute contract action
        Example: pylibre execute reward.libre updateall bentester '{"max_steps":"500"}'

    dex orderbook <base_symbol> <quote_symbol>
        Get DEX orderbook
        Example: pylibre dex orderbook LIBRE BTC

    dex order <account> <order_type> <quantity> <base_symbol> <quote_symbol> <price>
        Place order on DEX
        Example: pylibre dex order bentester buy 100 LIBRE BTC 100

Options:
    --network        Network to use [default: testnet]
    --api-url URL    Override API endpoint URL
    --config PATH    Config file path [default: config/config.yaml]
    --help          Show this help message
""")

def main():
    try:
        parser = create_parser()
        args = parser.parse_args()
        
        # Initialize client with config and network settings
        client = LibreClient(
            api_url=args.api_url,
            network=args.network,
            config_path=args.config,
            verbose=args.verbose
        )

        # Add DEX client
        dex = DexClient(client)

        # Handle different commands
        if args.command == 'table':
            result = client.get_table_rows(
                code=args.contract,
                table=args.table,
                scope=args.scope,
                limit=args.limit if args.limit else 10,
                lower_bound=args.lower_bound if args.lower_bound else "",
                upper_bound=args.upper_bound if args.upper_bound else "",
                index_position=args.index_position if args.index_position else "",
                key_type=args.key_type if args.key_type else ""
            )
            print(json.dumps(result))
            
        elif args.command == 'table-all':
            result = client.get_table(
                code=args.contract,
                table=args.table,
                scope=args.scope,
                index_position=args.index_position if hasattr(args, 'index_position') else "",
                key_type=args.key_type if hasattr(args, 'key_type') else ""
            )
            print(json.dumps(result))
            
        elif args.command == 'transfer':                
            result = client.transfer(
                from_account=args.from_account,
                to_account=args.to_account,
                quantity=args.quantity,
                memo=args.memo,
                contract=args.contract  # Will be None if not specified
            )
            print(json.dumps(result, indent=2))
            
        elif args.command == 'balance':
            result = client.get_currency_balance(
                contract=args.contract,  # Will be None if not specified
                account=args.account,
                symbol=args.symbol
            )
            print(json.dumps(result))
            
        elif args.command == 'execute':                
            result = client.execute_action(
                contract=args.contract,
                action_name=args.action,
                data=json.loads(args.data),
                actor=args.actor
            )
            print(json.dumps(result))
            
        elif args.command == 'dex':
            if args.dex_command == 'orderbook':
                result = dex.fetch_order_book(
                    quote_symbol=args.quote_symbol,
                    base_symbol=args.base_symbol
                )
                print(json.dumps(result, indent=2))
                
            elif args.dex_command == 'order':
                result = dex.place_order(
                    account=args.account,
                    order_type=args.order_type,
                    quantity=args.quantity,
                    price=args.price,
                    quote_symbol=args.quote_symbol,
                    base_symbol=args.base_symbol
                )
                print(json.dumps(result, indent=2))

        else:
            print(json.dumps({
                "success": False,
                "error": f"Unknown command: {args.command}"
            }))
            return 1
            
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e)
        }))
        return 1

if __name__ == "__main__":
    main()
