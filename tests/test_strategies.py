import unittest
from unittest.mock import Mock, patch
from pylibre.strategies.random_walk import RandomWalkStrategy
from pylibre import LibreClient
from decimal import Decimal

class TestRandomWalkStrategy(unittest.TestCase):
    def setUp(self):
        # Create mock client
        self.mock_client = Mock(spec=LibreClient)
        
        # Create mock DEX with proper return values
        self.mock_dex = Mock()
        self.mock_dex.place_order = Mock(return_value={
            "success": True,
            "data": {"transaction_id": "test_txid"}
        })
        
        self.mock_dex.fetch_order_book = Mock(return_value={
            "bids": [
                {"account": "bentester", "identifier": 1},
                {"account": "other", "identifier": 2}
            ],
            "offers": [
                {"account": "bentester", "identifier": 3},
                {"account": "other", "identifier": 4}
            ]
        })
        
        self.mock_dex.cancel_order = Mock(return_value={
            "success": True,
            "data": {"transaction_id": "test_cancel_txid"}
        })
        
        # Set the mock DEX as an attribute of the mock client
        self.mock_client.dex = self.mock_dex
        
        self.config = {
            'current_price': Decimal('0.0000000100'),
            'min_change_percentage': Decimal('0.01'),
            'max_change_percentage': Decimal('0.20'),
            'spread_percentage': Decimal('0.02'),
            'quantity': '100.00000000',
            'interval': 1
        }
        
        self.strategy = RandomWalkStrategy(
            client=self.mock_client,
            account="bentester",
            quote_symbol="BTC",
            base_symbol="LIBRE",
            config=self.config
        )
        # Explicitly set the dex attribute on the strategy
        self.strategy.dex = self.mock_dex

    def test_generate_signal(self):
        with patch('random.uniform') as mock_uniform, \
             patch('random.choice') as mock_choice:
            
            mock_uniform.return_value = 0.05  # Will be converted to Decimal in strategy
            mock_choice.return_value = 1
            
            signal = self.strategy.generate_signal()
            
            self.assertIn('price', signal)
            self.assertIn('movement_percentage', signal)
            self.assertIn('spread_percentage', signal)
            
            expected_price = Decimal('0.0000000100') * (Decimal('1') + Decimal('0.05'))
            self.assertEqual(signal['price'], expected_price)
            self.assertEqual(signal['movement_percentage'], Decimal('5.00'))

    def test_place_orders(self):
        signal = {
            'price': Decimal('0.0000000100'),
            'movement_percentage': Decimal('5.0'),
            'spread_percentage': Decimal('0.02')
        }
        
        result = self.strategy.place_orders(signal)
        self.assertTrue(result)
        
        # Verify order placement calls
        self.assertEqual(self.mock_dex.place_order.call_count, 2)
        
        # Verify bid order
        bid_call = self.mock_dex.place_order.call_args_list[0][1]
        self.assertEqual(bid_call['order_type'], 'buy')
        self.assertEqual(bid_call['account'], 'bentester')
        
        # Verify ask order
        ask_call = self.mock_dex.place_order.call_args_list[1][1]
        self.assertEqual(ask_call['order_type'], 'sell')
        self.assertEqual(ask_call['account'], 'bentester')

    def test_cancel_orders(self):
        result = self.strategy.cancel_orders()
        self.assertTrue(result)
        
        # Verify fetch_order_book was called
        self.mock_dex.fetch_order_book.assert_called_once()
        
        # Verify cancellation calls
        self.assertEqual(self.mock_dex.cancel_order.call_count, 2)
        
        # Verify cancel order parameters
        cancel_calls = self.mock_dex.cancel_order.call_args_list
        self.assertEqual(cancel_calls[0][1]['order_id'], 1)  # First bid
        self.assertEqual(cancel_calls[1][1]['order_id'], 3)  # First offer

if __name__ == '__main__':
    unittest.main() 