from pylibre import LibreClient
import json
import time

# Initialize client
client = LibreClient("https://testnet.libre.org", verbose=True)
client.load_account_keys('.env.testnet')

# Verify private keys are loaded
if not client.private_keys:
    print("⚠️  No private keys loaded. Please check your .env.testnet file")
    print("Expected format:")
    print("ACCOUNT_DEXTESTER=5K...")
    print("ACCOUNT_DEXTRADER=5J...")
    exit(1)

# Get the first account from loaded private keys
test_account = next(iter(client.private_keys))
print(f"\n🔑 Using account: {test_account}")

print("\n" + "="*50)
print("🧪 Test 1: Transfer with explicit contract")
print("="*50)

print(f"\n💰 Getting initial LIBRE balance for {test_account}")
initial_balance = float(client.get_currency_balance(
    contract="eosio.token",
    account=test_account,
    symbol="LIBRE"
).split()[0])
print(f"Initial Balance: {initial_balance:.4f} LIBRE")

if initial_balance < 0.0001:
    print("⚠️  Warning: Account has insufficient LIBRE balance for test")
    exit(1)

print(f"\n💸 Transferring 0.0001 LIBRE from {test_account} to dextrader (with explicit contract)")
result = client.transfer(
    contract="eosio.token",
    from_account=test_account,
    to_account="dextrader",
    quantity="0.0001 LIBRE",
    memo="Test with explicit contract"
)
print("Transfer result:", json.dumps(result, indent=2))

if not result.get("success") or not result.get("data", {}).get("transaction_id"):
    print("❌ Transfer failed or no transaction ID returned")
    exit(1)

# Wait for transaction to process
print("\nWaiting 2 seconds for transaction to process...")
time.sleep(2)

print(f"\n💰 Getting final balance for {test_account}")
final_balance = float(client.get_currency_balance(
    contract="eosio.token",
    account=test_account,
    symbol="LIBRE"
).split()[0])
print(f"Final Balance: {final_balance:.4f} LIBRE")

# Calculate and format the difference correctly
difference = final_balance - initial_balance
print(f"\n🔍 Balance difference: {difference:.4f} LIBRE")
if abs(difference + 0.0001) < 0.00001:
    print("✅ Test 1: Balance decreased by expected amount")
else:
    print("❌ Test 1: Unexpected balance difference")
    print(f"Expected: -0.0001 LIBRE")
    print(f"Actual: {difference:.4f} LIBRE")

print("\n" + "="*50)
print("🧪 Test 2: Transfer with auto-detected contract")
print("="*50)

print(f"\n💰 Getting initial balance for {test_account}")
initial_balance = float(client.get_currency_balance(
    account=test_account,
    symbol="LIBRE"  # No contract specified - should auto-detect
).split()[0])
print(f"Initial Balance: {initial_balance:.4f} LIBRE")

print(f"\n🔍 Auto-detecting contract for symbol LIBRE...")
print(f"\n💸 Transferring 0.0001 LIBRE from {test_account} to dextrader (auto-detecting contract)")
result = client.transfer(
    from_account=test_account,
    to_account="dextrader",
    quantity="0.0001 LIBRE",  # No contract specified - should auto-detect eosio.token
    memo="Test with auto-detected contract"
)
print("Transfer result:", json.dumps(result, indent=2))

if not result.get("success") or not result.get("data", {}).get("transaction_id"):
    print("❌ Transfer failed or no transaction ID returned")
    exit(1)

# Wait for transaction to process
print("\nWaiting 2 seconds for transaction to process...")
time.sleep(2)

print(f"\n💰 Getting final balance for {test_account}")
final_balance = float(client.get_currency_balance(
    account=test_account,
    symbol="LIBRE"  # No contract specified - should auto-detect
).split()[0])
print(f"Final Balance: {final_balance:.4f} LIBRE")

# Calculate and format the difference correctly
difference = final_balance - initial_balance
print(f"\n🔍 Balance difference: {difference:.4f} LIBRE")
if abs(difference + 0.0001) < 0.00001:
    print("✅ Test 2: Balance decreased by expected amount")
else:
    print("❌ Test 2: Unexpected balance difference")
    print(f"Expected: -0.0001 LIBRE")
    print(f"Actual: {difference:.4f} LIBRE")

print("\n" + "="*50)
print("🧪 Test 3: Query Table Rows")
print("="*50)

print("\n📊 Getting rows from farm.libre contract")
rows = client.get_table_rows(
    code="farm.libre",
    table="account",
    scope="BTCUSD",
    limit=5  # Limit to 5 rows for example
)
print(f"\nFirst {len(rows)} rows from farm.libre account table:")
print(json.dumps(rows, indent=2))

print("\n" + "="*50)
print("🧪 Test 4: Query Entire Table with Pagination")
print("="*50)

print("\n📊 Getting all rows from stake.libre contract")
all_rows = client.get_table(
    code="stake.libre",
    table="stake",
    scope="stake.libre"
)
print(f"\nFound {len(all_rows)} total rows in stake.libre stake table")
print("First 2 rows as example:")
print(json.dumps(all_rows[:2], indent=2))

print("\n" + "="*50)
print("🧪 Test 5: Get Currency Stats")
print("="*50)

print("\n📊 Getting currency stats for LIBRE token")
stats = client.get_currency_stats(
    contract="eosio.token",
    symbol="LIBRE"
)
print("\nLIBRE token stats:")
print(json.dumps(stats, indent=2))

print("\n📊 Getting currency stats for USDT token")
stats = client.get_currency_stats(
    contract="usdt.libre",
    symbol="USDT"
)
print("\nUSDT token stats:")
print(json.dumps(stats, indent=2))