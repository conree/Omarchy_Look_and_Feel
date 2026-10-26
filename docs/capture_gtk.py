#!/usr/bin/env python3
"""Render a GTK 3 example before/after the production generated palette.

Run: python3 -B docs/capture_gtk.py
Requires GTK 3, PyGObject and broadwayd. Uses a private Broadway display and
temporary HOME; no session settings or real application profiles are modified.
This is a native GTK demonstration, not a claim of all-app visual acceptance.
"""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import time

SOURCE = Path(__file__).resolve().parents[1]
OUTPUT = SOURCE / 'docs/screenshots'


def render():
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, Gdk, GLib
    settings = Gtk.Settings.get_default()
    assert settings, 'Private Broadway display unavailable'
    settings.set_property('gtk-theme-name', 'Adwaita')
    settings.set_property('gtk-font-name', 'DejaVu Sans 11')
    settings.set_property('gtk-application-prefer-dark-theme', False)
    window = Gtk.OffscreenWindow()
    window.set_default_size(640, 400)
    window.get_style_context().add_class('background')
    def background(widget, context):
        Gtk.render_background(widget.get_style_context(), context, 0, 0,
                              widget.get_allocated_width(), widget.get_allocated_height())
        return False
    window.connect('draw', background)
    outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    window.add(outer)
    header = Gtk.HeaderBar(title='Project files', subtitle='GTK 3 example')
    header.set_show_close_button(False)
    header.pack_end(Gtk.Button(label='New folder'))
    outer.pack_start(header, False, False, 0)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16, margin=24)
    outer.pack_start(box, True, True, 0)
    entry = Gtk.Entry()
    entry.set_text('Search this folder')
    box.pack_start(entry, False, False, 0)
    model = Gtk.ListStore(str, str)
    for row in [('Documents', 'Folder'), ('Pictures', 'Folder'), ('Notes.txt', 'Text document'), ('README.md', 'Markdown document')]:
        model.append(row)
    tree = Gtk.TreeView(model=model)
    for index, heading in enumerate(('Name', 'Type')):
        column = Gtk.TreeViewColumn(heading, Gtk.CellRendererText(), text=index)
        column.set_expand(True)
        tree.append_column(column)
    box.pack_start(tree, True, True, 0)
    tree.get_selection().select_path(Gtk.TreePath.new_from_indices([0]))
    box.pack_start(Gtk.Label(label='4 items · One selected', xalign=0), False, False, 0)
    window.show_all()
    tree.grab_focus()

    def capture(name):
        until = time.monotonic() + .3
        while time.monotonic() < until:
            while GLib.MainContext.default().pending():
                GLib.MainContext.default().iteration(False)
            time.sleep(.01)
        image = window.get_pixbuf()
        assert image and image.get_width() == 640
        image.savev(str(OUTPUT / (name + '.png')), 'png', [], [])

    capture('gtk-before')
    sys.path.insert(0, str(SOURCE))
    from application_themes import gtk_stylesheet, palette
    colors = palette(Path(os.environ.get('OMARCHY_PATH', '/usr/share/omarchy')) / 'themes/catppuccin')
    css = gtk_stylesheet('', colors)
    provider = Gtk.CssProvider()
    errors = []
    provider.connect('parsing-error', lambda provider, section, error: errors.append(str(error)))
    provider.load_from_data(css)
    assert not errors, errors
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
    capture('gtk-after')
    window.destroy()
    print('Native GTK 3 captures: Adwaita before, production Catppuccin CSS after.')


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='laf-readme-gtk-') as directory:
        env = dict(os.environ, HOME=directory, XDG_CONFIG_HOME=directory + '/config',
                   XDG_STATE_HOME=directory + '/state', XDG_DATA_HOME=directory + '/data',
                   XDG_CACHE_HOME=directory + '/cache', XDG_RUNTIME_DIR=directory,
                   GDK_BACKEND='broadway', BROADWAY_DISPLAY=':5', GTK_THEME='Adwaita',
                   DBUS_SESSION_BUS_ADDRESS='', GSETTINGS_BACKEND='memory',
                   PYTHONDONTWRITEBYTECODE='1')
        with open(Path(directory) / 'broadway.log', 'w+') as log:
            daemon = subprocess.Popen(['broadwayd', '--unixsocket=' + directory + '/http.sock', ':5'], env=env, stdout=log, stderr=log)
            try:
                for _ in range(100):
                    if daemon.poll() is not None:
                        log.seek(0)
                        raise RuntimeError(log.read())
                    if (Path(directory) / 'broadway6.socket').exists():
                        break
                    time.sleep(.02)
                subprocess.run([sys.executable, '-B', __file__, '--render'], env=env, check=True, timeout=20)
            finally:
                daemon.terminate()
                daemon.wait(timeout=5)


if __name__ == '__main__':
    render() if '--render' in sys.argv else main()
