"""A deliberately isolated, in-memory smart-home simulator."""
import copy
import json
import re

ROOMS = ('living room', 'kitchen', 'bedroom')

def schema(name, description, properties, required):
    return {'type': 'function', 'function': {'name': name, 'description': description, 'parameters': {'type': 'object', 'properties': properties, 'required': required}}}

TOOLS = [
    schema('set_light', 'Set a room light on or off, or adjust brightness (0-100).', {'room': {'type': 'string', 'enum': list(ROOMS)}, 'on': {'type': 'boolean'}, 'brightness': {'type': 'integer'}}, ['room']),
    schema('set_music', 'Control simulated music playback, playlist and volume (0-100).', {'playing': {'type': 'boolean'}, 'playlist': {'type': 'string'}, 'volume': {'type': 'integer'}}, []),
    schema('set_temperature', 'Set thermostat target temperature in Celsius (16-30).', {'temperature': {'type': 'number'}}, ['temperature']),
    schema('activate_scene', 'Activate a simulated home scene.', {'scene': {'type': 'string', 'enum': ['relax', 'focus', 'good night']}}, ['scene']),
]

def parse_calls(text):
    calls = []
    for match in re.finditer(r'<tool_call>\s*<function=([^>\n]+)>(.*?)</function>\s*</tool_call>', text, re.S):
        args = {}
        for p in re.finditer(r'<parameter=([^>\n]+)>(.*?)</parameter>', match.group(2), re.S):
            value = p.group(2).strip()
            try:
                value = json.loads(value)
            except (ValueError, TypeError):
                pass
            args[p.group(1).strip()] = value
        calls.append({'name': match.group(1).strip(), 'arguments': args})
    return calls

class Home:
    def __init__(self):
        self.state = {'lights': {room: {'on': True, 'brightness': value} for room, value in zip(ROOMS, (70, 85, 45))}, 'music': {'playing': False, 'playlist': 'Chill Mix', 'volume': 40}, 'climate': {'temperature': 21}}

    def snapshot(self):
        return copy.deepcopy(self.state)

    def apply(self, name, args):
        if not isinstance(args, dict):
            raise ValueError('Arguments must be an object')
        if name == 'set_light':
            if set(args) - {'room', 'on', 'brightness'} or args.get('room') not in ROOMS or not ({'on', 'brightness'} & args.keys()):
                raise ValueError('Choose a valid room and light setting')
            if 'on' in args and type(args['on']) is not bool:
                raise ValueError('on must be true or false')
            if 'brightness' in args and (type(args['brightness']) is not int or not 0 <= args['brightness'] <= 100):
                raise ValueError('Brightness must be an integer from 0 to 100')
            light = self.state['lights'][args['room']]
            light.update({k: v for k, v in args.items() if k != 'room'})
        elif name == 'set_music':
            if not args or set(args) - {'playing', 'playlist', 'volume'}:
                raise ValueError('Choose a valid music setting')
            if 'playing' in args and type(args['playing']) is not bool:
                raise ValueError('playing must be true or false')
            if 'playlist' in args and (not isinstance(args['playlist'], str) or not 1 <= len(args['playlist'].strip()) <= 80):
                raise ValueError('Playlist must be a nonempty name')
            if 'volume' in args and (type(args['volume']) is not int or not 0 <= args['volume'] <= 100):
                raise ValueError('Volume must be an integer from 0 to 100')
            self.state['music'].update(args)
        elif name == 'set_temperature':
            value = args.get('temperature')
            if set(args) != {'temperature'} or type(value) not in (int, float) or not 16 <= value <= 30:
                raise ValueError('Temperature must be between 16 and 30°C')
            self.state['climate']['temperature'] = value
        elif name == 'activate_scene':
            if set(args) != {'scene'} or args['scene'] not in ('relax', 'focus', 'good night'):
                raise ValueError('Unknown scene')
            scene = args['scene']
            for light in self.state['lights'].values():
                light.update(on=scene != 'good night', brightness={'relax': 30, 'focus': 90, 'good night': 10}[scene])
            self.state['music'].update(playing=scene != 'good night', playlist={'relax': 'Chill Mix', 'focus': 'Deep Focus', 'good night': 'Chill Mix'}[scene])
        else:
            raise ValueError('Unknown tool: ' + str(name))
        return self.snapshot()
