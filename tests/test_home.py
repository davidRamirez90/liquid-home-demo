import unittest
from home import Home, parse_calls

class HomeTests(unittest.TestCase):
    def setUp(self):
        self.home = Home()

    def test_light_action_changes_only_requested_room(self):
        self.home.apply('set_light', {'room': 'living room', 'on': False})
        self.assertFalse(self.home.state['lights']['living room']['on'])
        self.assertTrue(self.home.state['lights']['kitchen']['on'])

    def test_rejects_invalid_brightness_without_mutation(self):
        before = self.home.snapshot()
        with self.assertRaises(ValueError):
            self.home.apply('set_light', {'room': 'kitchen', 'brightness': 101})
        self.assertEqual(self.home.snapshot(), before)

    def test_music_and_temperature(self):
        self.home.apply('set_music', {'playing': True, 'playlist': 'Jazz', 'volume': 35})
        self.home.apply('set_temperature', {'temperature': 21})
        self.assertEqual(self.home.state['music']['playlist'], 'Jazz')
        self.assertEqual(self.home.state['climate']['temperature'], 21)

    def test_unknown_tool_is_rejected(self):
        with self.assertRaises(ValueError):
            self.home.apply('unlock_door', {})

    def test_parse_native_tool_call(self):
        text = '<tool_call>\n<function=set_light>\n<parameter=room>kitchen</parameter>\n<parameter=on>false</parameter>\n</function>\n</tool_call>'
        self.assertEqual(parse_calls(text), [{'name': 'set_light', 'arguments': {'room': 'kitchen', 'on': False}}])

if __name__ == '__main__':
    unittest.main()
