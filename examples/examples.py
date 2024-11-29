from pylibre import LibreClient
import json
import time

# Initialize client
client = LibreClient("https://testnet.libre.org")
client.load_account_keys('.env.testnet')

print("\n📊 Getting table data from farm.libre contract")
farm_data = client.get_table(
    code="farm.libre",
    table="account",
    scope="BTCUSD"
)
print("Farm Data:", farm_data)

print("\n💰 Getting balance for bentester")
initial_balance = client.get_currency_balance(
    contract="usdt.libre",
    account="bentester",
    symbol="USDT"
)[0]
print("Initial Balance:", initial_balance)

print("\n💸 Transferring 0.001 USDT from bentester to bentest3 (with explicit contract)")
result = client.transfer(
    contract="usdt.libre",
    from_account="bentester",
    to_account="bentest3",
    quantity="0.00100000 USDT",
    memo="Test"
)
print("Transfer result:", json.dumps(result, indent=2))

print("\n💸 Transferring 0.001 USDT from bentester to bentest3 (auto-detecting contract)")
result = client.transfer(
    from_account="bentester",
    to_account="bentest3",
    quantity="0.00100000 USDT",  # Contract will be determined from "USDT"
    memo="Test"
)
print("Transfer result:", json.dumps(result, indent=2))

print("\n💰 Getting balance again for bentester - should be less by 0.001 USDT")
print("Waiting 1 seconds for transaction to process...")
time.sleep(1)

final_balance = client.get_currency_balance(
    contract="usdt.libre",
    account="bentester",
    symbol="USDT"
)[0]
print("Final Balance:", final_balance)

# Convert balances to float and compare
initial_amount = float(initial_balance.split()[0])
final_amount = float(final_balance.split()[0])
difference = initial_amount - final_amount

print(f"\n🔍 Balance difference: {difference:.8f} USDT")
if abs(difference - 0.002) < 0.00000001:
    print("✅ Transfer amount verified correctly")
else:
    print("❌ Unexpected balance difference")

print("\n" + "="*50)
print("📋 Stake Table Comparison")
print("="*50)

print("\n1. 📊 Testing get_table_rows with limit=1:")
stake_data_single = client.get_table_rows(
    code="stake.libre",
    table="stake",
    scope="stake.libre",
    limit=1
)
print(f"\nSingle row test - rows retrieved: {len(stake_data_single)}")
print("Single entry:", json.dumps(stake_data_single, indent=2))

print("\n2. 📊 Using get_table (getting ALL rows):")
stake_data_all = client.get_table(
    code="stake.libre",
    table="stake",
    scope="stake.libre"
)
print(f"\nTotal rows retrieved: {len(stake_data_all)}")
print("First few entries:", json.dumps(stake_data_all[:3], indent=2))

print("\n3. 📑 Using get_table_rows (limited to 10 rows by default):")
stake_data_limited = client.get_table_rows(
    code="stake.libre",
    table="stake",
    scope="stake.libre"
)
print(f"\nTotal rows retrieved: {len(stake_data_limited)}")
print("All entries:", json.dumps(stake_data_limited, indent=2))

print("\n" + "="*50)
print("Single row test successful:", "✅" if len(stake_data_single) == 1 else "❌")
print("Difference confirmed:", "✅ More rows retrieved with get_table" if len(stake_data_all) > len(stake_data_limited) else "❌ Unexpected result")

print("\n" + "="*50)
print("🔄 Contract Action Execution")
print("="*50)

print("\n📝 Executing updateall action on reward.libre contract:")
action_result = client.execute_action(
    contract="reward.libre",
    action_name="updateall",
    actor="bentester",
    data={
        "max_steps": "500"
    }
)
print("Action result:", json.dumps(action_result, indent=2))