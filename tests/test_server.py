import unittest
from unittest.mock import patch
import server
from home import Home

class TurnTests(unittest.TestCase):
    def setUp(self):
        server.home = Home()

    @patch('server.load_model')
    @patch('server.generate_text')
    def test_model_tool_call_changes_simulated_state(self, generate, load):
        generate.side_effect = ['<tool_call><function=set_light><parameter=room>kitchen</parameter><parameter=on>false</parameter></function></tool_call>', 'Done.']
        result = server.run_turn('Turn off the kitchen light', speak=False)
        self.assertFalse(result['state']['lights']['kitchen']['on'])
        self.assertTrue(result['events'][0]['ok'])
        self.assertEqual(result['answer'], 'Done.')

    @patch('server.load_model')
    @patch('server.generate_text')
    def test_invalid_tool_does_not_change_state(self, generate, load):
        generate.side_effect = ['<tool_call><function=set_temperature><parameter=temperature>99</parameter></function></tool_call>', 'That setting is invalid.']
        result = server.run_turn('Set thermostat to 99', speak=False)
        self.assertEqual(result['state']['climate']['temperature'], 21)
        self.assertFalse(result['events'][0]['ok'])

if __name__ == '__main__': unittest.main()
