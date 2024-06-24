from pathlib import Path
import plyvel
import os
import importlib
import pkgutil
from google.protobuf.message import DecodeError, Message
import urwid
import json
import datetime
import warnings

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

TX_INDEX_PATH = Path().home().joinpath(".cometbft/data/tx_index.db")
STATE_PATH = Path().home().joinpath(".cometbft/data/state.db")
BLOCKSTORE_PATH = Path().home().joinpath(".cometbft/data/blockstore.db")

palette = [
    ('red', 'light red', ''),  # Define the red color for text
    ('reversed', 'standout', ''),  # Focus map for buttons
]

def load_proto_modules(proto_root):
    modules = []
    for root, _, files in os.walk(proto_root):
        for file in files:
            if file.endswith("_pb2.py"):
                try:
                    module_name = os.path.splitext(file)[0]
                    module_path = os.path.join(root, file)
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    modules.append(module)
                except Exception as e:
                    print(f"Failed to load proto module {module_name}: {e}")
    return modules

def get_proto_message_classes(modules):
    message_classes = []
    for module in modules:
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, Message):
                message_classes.append(attr)
    return message_classes

def try_decode_with_all_protos(data, message_classes):
    for message_class in message_classes:
        message_instance = message_class()
        try:
            message_instance.ParseFromString(data)
            return message_instance
        except:
            pass
    raise DecodeError("Could not decode data with any proto message class")

def sort_keys(key):
    try:
        # Try to convert the key to an integer for numerical sorting
        return int(key)
    except ValueError:
        # If conversion fails, sort by the key as a string
        return key

class CometBFTDebug:
    def __init__(self):
        os.chdir(Path(__file__).parent)
        proto_root = Path(__file__).parent.parent.parent
        modules = load_proto_modules(proto_root)
        self.message_classes = get_proto_message_classes(modules)
        self.load_db()

        self.current_prefix = ""
        self.previous_key_stack = []
        self.body = []
        self.main_widget = urwid.Padding(self.menu(self.current_prefix), left=2, right=2)
        self.footer = urwid.Columns([urwid.Text("Press 'q' to quit"), urwid.Text(self.get_database_size_readable(), align='right')])
        self.top = urwid.Overlay(
            urwid.LineBox(urwid.Frame(
                self.main_widget,
                footer=self.footer), title="CometBFT Explorer"),
            urwid.SolidFill(u'\N{MEDIUM SHADE}'),
            align='center', width=('relative', 100),
            valign='middle', height=('relative', 100),
            min_width=20, min_height=9
        )
        self.loop = urwid.MainLoop(self.top,palette=palette, unhandled_input=self.unhandled_keypress)

    def get_database_size_readable(self):
        path = Path().home().joinpath(".cometbft/data")
        if not path.exists():
            return "Database Size: 0 B"
        size = sum(f.stat().st_size for f in path.glob('**/*') if f.is_file())
        # Make size human readable
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"Database Size: {size:.2f} {unit}"
            size /= 1024.0

    def get_subdirs_and_keys(self, keys, prefix):
        subdirs = {}
        leaf_keys = set()
        prefix_len = len(prefix)

        for key in keys:
            if key.startswith(prefix):
                remaining_key = key[prefix_len:].lstrip(":")
                parts = self.split_key(remaining_key)
                if parts:
                    first_part = parts[0]
                    if len(parts) > 1:
                        if first_part in subdirs:
                            subdirs[first_part] += 1
                        else:
                            subdirs[first_part] = 1
                    else:
                        leaf_keys.add(first_part)
        return subdirs, leaf_keys

    def menu(self, prefix):
        body = [urwid.Text(f"{prefix}")] if prefix else [urwid.Text("Root")]
        keys = self.db.keys()

        subdirs, leaf_keys = self.get_subdirs_and_keys(keys, prefix)

        if prefix:  # Add back button if not at root level
            back_button = urwid.Button("Back")
            urwid.connect_signal(back_button, 'click', self.back_to_parent)
            body.append(urwid.AttrMap(back_button, None, focus_map='reversed'))

        if not subdirs and not leaf_keys:
            body.append(urwid.Text("No keys found."))

        for subdir, count in sorted(subdirs.items()):
            button = urwid.Button(f"{subdir}/ ({count})")
            urwid.connect_signal(button, 'click', self.navigate_to, prefix + subdir + self.add_separator(prefix))
            body.append(urwid.AttrMap(button, None, focus_map='reversed'))

        for key in sorted(leaf_keys):
            button = urwid.Button(key)
            urwid.connect_signal(button, 'click', self.show_value, prefix + key)
            body.append(urwid.AttrMap(button, None, focus_map='reversed'))

        return urwid.ListBox(urwid.SimpleFocusListWalker(body))

    def add_separator(self, prefix):
        return ":"

    def split_key(self, key):
        parts = [key]
        for sep in [":"]:
            new_parts = []
            for part in parts:
                new_parts.extend(part.split(sep))
            parts = new_parts
        return parts

    def navigate_to(self, button, key_prefix):
        if key_prefix == "":
            self.previous_key_stack.append(".") # Add placeholder to stack for root level
        self.previous_key_stack.append(self.current_prefix)
        self.current_prefix = key_prefix
        self.main_widget.original_widget = self.menu(key_prefix)

    def show_value(self, button, key):
        value = self.db[key]
        text = urwid.Text(f"Key: {key}\n\nValue:\n{value}")
        back_button = urwid.Button("Back")
        urwid.connect_signal(back_button, 'click', self.back_to_menu)
        list_walker = urwid.SimpleFocusListWalker([text, urwid.AttrMap(back_button, None, focus_map='reversed')])
        self.main_widget.original_widget = urwid.ListBox(list_walker)

    def back_to_parent(self, button):
        previous_key = self.previous_key_stack.pop()
        if previous_key == ".":
            self.current_prefix = ""
        else:
            self.current_prefix = previous_key
        self.main_widget.original_widget = self.menu(previous_key)

    def back_to_menu(self, button):
        self.main_widget.original_widget = self.menu(self.current_prefix)

    def unhandled_keypress(self, key):
        if key == 'q':
            raise urwid.ExitMainLoop()

    def load_db(self):
        self.block_store_db = plyvel.DB(str(BLOCKSTORE_PATH), create_if_missing=True)
        self.state_db = plyvel.DB(str(STATE_PATH), create_if_missing=True)
        self.tx_index_db = plyvel.DB(str(TX_INDEX_PATH), create_if_missing=True)
        
        self.readable_block_store_db = {}
        for key, value in self.block_store_db:
            try:
                readable_key = key.decode()
                self.readable_block_store_db[readable_key] = None
            except UnicodeDecodeError:
                try:
                    readable_key = try_decode_with_all_protos(key, self.message_classes)
                    self.readable_block_store_db[readable_key] = None
                except:
                    continue
            try:
                readable_value = try_decode_with_all_protos(value, self.message_classes)
                self.readable_block_store_db[readable_key] = readable_value
            except:
                try:
                    readable_value = value.decode()
                    self.readable_block_store_db[readable_key] = readable_value
                except UnicodeDecodeError:
                    continue

           

        self.readable_state_db = {}
        for key, value in self.state_db:
            try:
                readable_key = key.decode()
                self.readable_state_db[readable_key] = None
            except UnicodeDecodeError:
                try:
                    readable_key = try_decode_with_all_protos(key, self.message_classes)
                    self.readable_state_db[readable_key] = None
                except:
                    continue
            try:
                readable_value = try_decode_with_all_protos(value, self.message_classes)
                self.readable_state_db[readable_key] = readable_value
            except:
                try:
                    readable_value = value.decode()
                    self.readable_state_db[readable_key] = readable_value
                except UnicodeDecodeError:
                    continue
        self.readable_tx_index_db = {}
        for key, value in self.tx_index_db:
            try:
                readable_key = key.decode()
                self.readable_tx_index_db[readable_key] = None
            except UnicodeDecodeError:
                try:
                    readable_key = try_decode_with_all_protos(key, self.message_classes)
                    self.readable_tx_index_db[readable_key] = None
                except:
                    continue
            try:
                readable_value = try_decode_with_all_protos(value, self.message_classes)
                self.readable_tx_index_db[readable_key] = readable_value
            except:
                try:
                    readable_value = value.decode()
                    self.readable_tx_index_db[readable_key] = readable_value
                except UnicodeDecodeError:
                    continue
       
        # Combine all databases into one and prepend the database name to the key
        self.db = {}
        for key in self.readable_block_store_db:
            self.db[f"blockstore:{key}"] = self.readable_block_store_db[key]
        for key in self.readable_state_db:
            self.db[f"state:{key}"] = self.readable_state_db[key]
        for key in self.readable_tx_index_db:
            self.db[f"tx_index:{key}"] = self.readable_tx_index_db[key]

        
        # Sort keys a-z but if the key can be converted to an integer, sort by that integer
        self.db = {k: v for k, v in sorted(self.db.items(), key=lambda x: sort_keys(x[0]))}

    def run(self):
        self.loop.run()
        
if __name__ == "__main__":
    cometbft_debug = CometBFTDebug()
    cometbft_debug.run()