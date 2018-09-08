import importlib_resources
import json
from collections import OrderedDict


DEFAULTS = json.loads(importlib_resources.read_text('AnkiPy', 'defaults.json'), object_pairs_hook=OrderedDict)
