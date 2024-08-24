import urwid
import json
import warnings

from contracting.storage.driver import Driver
from xian.tools.export_state import main as export_state
from pathlib import Path

driver = Driver()
DIMENSION_SEPARATORS = ['.', ':']

warnings.filterwarnings("ignore", category=DeprecationWarning)

palette = [
    ('red', 'light red', ''),  # Define the red color for text
    ('reversed', 'standout', ''),  # Focus map for buttons
]

class Explorer:
    def __init__(self):
        self.current_prefix = ""
        self.previous_key_stack = []
        self.body = []
        self.main_widget = urwid.Padding(self.menu(self.current_prefix), left=2, right=2)
        self.footer = urwid.Columns([urwid.Text("Press 'q' to quit"), urwid.Text(self.get_database_size_readable(), align='right')])
        self.top = urwid.Overlay(
            urwid.LineBox(urwid.Frame(
                self.main_widget,
                footer=self.footer), title="State Explorer"),
            urwid.SolidFill(u'\N{MEDIUM SHADE}'),
            align='center', width=('relative', 100),
            valign='middle', height=('relative', 100),
            min_width=20, min_height=9
        )
        self.loop = urwid.MainLoop(self.top,palette=palette, unhandled_input=self.unhandled_keypress)

    def get_database_size_readable(self):
        path = Path().home().joinpath(".cometbft/xian")
        if not path.exists():
            return "Database Size: 0 B"
        size = sum(f.stat().st_size for f in path.glob('**/*') if f.is_file())
        # Make size human-readable
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"Database Size: {size:.2f} {unit} ({len(driver.keys_from_disk(''))} keys)"
            size /= 1024.0


    def get_subdirs_and_keys(self, keys, prefix):
        subdirs = {}
        leaf_keys = set()
        prefix_len = len(prefix)

        for key in keys:
            if key.startswith(prefix):
                remaining_key = key[prefix_len:].lstrip(DIMENSION_SEPARATORS[0]).lstrip(DIMENSION_SEPARATORS[1])
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
        keys = driver.keys_from_disk(prefix)

        subdirs, leaf_keys = self.get_subdirs_and_keys(keys, prefix)

        if prefix:  # Add back button if not at root level
            back_button = urwid.Button("Back")
            urwid.connect_signal(back_button, 'click', self.back_to_parent)
            body.append(urwid.AttrMap(back_button, None, focus_map='reversed'))

        if not prefix:
            # Red Text
            genesis_create_button = urwid.Button("Export State")
            urwid.connect_signal(genesis_create_button, 'click', lambda button: self.ask_signing_key())
            body.append(urwid.AttrMap(genesis_create_button, 'red', focus_map='reversed'))

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
        if prefix and prefix[-1] in DIMENSION_SEPARATORS:
            return DIMENSION_SEPARATORS[1]
        else:
            return DIMENSION_SEPARATORS[0]

    def split_key(self, key):
        parts = [key]
        for sep in DIMENSION_SEPARATORS:
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

    def edit_value(self, button, key, current_value):
        edit = urwid.Edit(("I say", u"New value:\n"), edit_text=str(current_value))
        save_button = urwid.Button("Save")
        urwid.connect_signal(save_button, 'click', lambda button: self.save_value(button, key, edit))
        cancel_button = urwid.Button("Cancel")
        urwid.connect_signal(cancel_button, 'click', self.back_to_menu)
        list_walker = urwid.SimpleFocusListWalker([edit, urwid.AttrMap(save_button, None, focus_map='reversed'), urwid.AttrMap(cancel_button, None, focus_map='reversed')])
        self.main_widget.original_widget = urwid.ListBox(list_walker)

    def save_value(self, button, key, edit):
        new_value = self.parse_value(edit.get_edit_text())
        driver.set(key, new_value)
        driver.commit()
        self.back_to_menu(button)

    def parse_value(self, value):
        try:
            parsed_value = json.loads(value)
            return parsed_value
        except json.JSONDecodeError:
            pass
        
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            return value

    def show_value(self, button, key):
        value = driver.get(key)
        text = urwid.Text(f"Key: {key}\n\nValue:\n{value}")
        edit_button = urwid.Button("Edit Value")
        urwid.connect_signal(edit_button, 'click', lambda button: self.edit_value(button, key, value))
        back_button = urwid.Button("Back")
        urwid.connect_signal(back_button, 'click', self.back_to_menu)
        list_walker = urwid.SimpleFocusListWalker([text, urwid.AttrMap(edit_button, None, focus_map='reversed'), urwid.AttrMap(back_button, None, focus_map='reversed')])
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

    def ask_signing_key(self, genesis_create_button=None):
        sk_input = urwid.Edit("Enter founder's signing key: ")
        sk_button = urwid.Button("Export")
        urwid.connect_signal(sk_button, 'click', lambda button: self.export_genesis_block(sk_input))
        back_button = urwid.Button("Back")
        urwid.connect_signal(back_button, 'click', self.back_to_menu)
        list_walker = urwid.SimpleFocusListWalker([sk_input, urwid.AttrMap(sk_button, None, focus_map='reversed'), urwid.AttrMap(back_button, None, focus_map='reversed')])
        self.main_widget.original_widget = urwid.ListBox(list_walker)
        

    def export_genesis_block(self, sk_input, button=None):
        try:
            export_state(sk_input.get_edit_text(), Path.cwd())
            success_text = urwid.Text(f"Genesis block exported")
            back_button = urwid.Button("Back to menu")
            urwid.connect_signal(back_button, 'click', self.back_to_menu)
            list_walker = urwid.SimpleFocusListWalker([success_text, urwid.AttrMap(back_button, None, focus_map='reversed')])
            self.main_widget.original_widget = urwid.ListBox(list_walker)
        except Exception as e:
            error_text = urwid.Text(f"Error: {e}")
            back_button = urwid.Button("Back")
            urwid.connect_signal(back_button, 'click', self.ask_signing_key)
            list_walker = urwid.SimpleFocusListWalker([error_text, urwid.AttrMap(back_button, None, focus_map='reversed')])
            self.main_widget.original_widget = urwid.ListBox(list_walker)
            return

    def run(self):
        self.loop.run()

if __name__ == "__main__":
    Explorer().run()
