import os
import json

class Config:

    _cfg_data = None
    _cfg_file = None

    def __init__(self, *cfg_path: str):
        # Ensure the path is relative to the directory of this file
        base_path = os.path.dirname(os.path.abspath(__file__))
        self._cfg_file = os.path.join(base_path, *cfg_path)
        self.load()

    def load(self):
        with open(self._cfg_file, encoding='utf-8') as f:
            self._cfg_data = json.load(f)

    def dump(self):
        with open(self._cfg_file, 'w', encoding='utf-8') as f:
            json.dump(self._cfg_data, f, ensure_ascii=False, sort_keys=True, indent=4)

    def get(self, key, reload=False):
        if reload: self.load()
        return self._cfg_data[key] if key in self._cfg_data else None

    def set(self, key, value, dump=True):
        self._cfg_data[key] = value
        if dump: self.dump()