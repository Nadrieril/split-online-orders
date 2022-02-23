import json
from dataclasses import is_dataclass

# Default behavior is not customizable which sucks.
class RecursiveJsonEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o.__class__, "__json__"):
            return o.__json__()
        elif is_dataclass(o.__class__):
            return o.__dict__
        else:
            return json.JSONEncoder.default(self, o)

JSON_ARGS = dict(cls=RecursiveJsonEncoder, ensure_ascii=False)
