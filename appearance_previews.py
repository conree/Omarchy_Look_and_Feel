"""Read-only, bounded catalog previews; no toolkit activation or config writes.

Theme previews use the same effective palette as the application adapters.
Icon samples follow the installed theme's index, XDG roots and inheritance;
they are illustrative files, not proof of an application's active icon theme.
"""
from __future__ import annotations

import configparser
from pathlib import Path
import stat

MAX_METADATA_BYTES = 1024 * 1024
MAX_ICON_BYTES = 4 * 1024 * 1024
MAX_DIRECTORIES = 1024
MAX_THEMES = 32
MAX_DEPTH = 8
MAX_FILE_PROBES = 8192
SAMPLE_NAMES = ('folder', 'text-x-generic', 'preferences-system')


class _PreviewLimit(Exception):
    pass


def theme_preview(sources):
    """Mirror Apply's last palette-bearing source precedence, without fallback
    after a malformed effective palette. Return None if it cannot be previewed.
    """
    from application_themes import palette
    try:
        source = next((Path(path) for path in reversed(sources)
                       if (Path(path) / 'colors.toml').is_file()
                       or (Path(path) / 'alacritty.toml').is_file()), None)
        if source is None:
            return None
        path = source / 'colors.toml'
        if not path.is_file():
            path = source / 'alacritty.toml'
        if not stat.S_ISREG(path.stat().st_mode) or path.stat().st_size > MAX_METADATA_BYTES:
            return None
        colors = palette(source)
        swatches = list(dict.fromkeys(colors[key] for key in
                       ('red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'accent')
                       if key in colors))
        return {key: colors[key] for key in ('background', 'foreground', 'accent', 'mode')} | {
            'swatches': swatches,
        }
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, RuntimeError):
        return None


class IconPreviews:
    """A small icon lookup cache scoped to one inventory, at 32 logical pixels.

    Uses the first index.theme, all same-name roots, local-theme matches before
    inherited ones, and hicolor last. No unthemed application fallback is used.
    Lookup follows https://specifications.freedesktop.org/icon-theme/latest/ .
    """

    def __init__(self, roots):
        self.roots = []
        for root in roots:
            try:
                path = Path(root).resolve(strict=True)
                if path.is_dir() and path not in self.roots:
                    self.roots.append(path)
            except (OSError, RuntimeError):
                continue
            if len(self.roots) >= 32:
                break
        self.cache = {}
        self.remaining_probes = MAX_FILE_PROBES

    def _file(self, path, limit):
        try:
            resolved = path.resolve(strict=True)
            if not any(resolved.is_relative_to(root) for root in self.roots):
                return None
            info = resolved.stat()
            if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= limit:
                return None
            return resolved
        except (OSError, RuntimeError):
            return None

    def _metadata(self, name):
        from icon_actions import supported_name
        if name in self.cache:
            return self.cache[name]
        self.cache[name] = None
        if not supported_name(name):
            return None
        # An invalid first index shadows later indexes, just as it does for Apply.
        first = next((root / name / 'index.theme' for root in self.roots
                      if (root / name / 'index.theme').exists()), None)
        if first is None:
            return None
        path = self._file(first, MAX_METADATA_BYTES)
        if path is None:
            return None
        try:
            parser = configparser.RawConfigParser(strict=True)
            parser.read_string(path.read_text(encoding='utf-8'))
            if not parser.get('Icon Theme', 'Name', fallback='').strip():
                return None
            parser.getboolean('Icon Theme', 'Hidden', fallback=False)
            directories = self._list(parser, 'Directories')
            if not directories:
                return None
            directories += self._list(parser, 'ScaledDirectories')
            parents = self._list(parser, 'Inherits')
            if len(directories) > MAX_DIRECTORIES or len(parents) > MAX_THEMES:
                return None
            if any(not supported_name(parent) for parent in parents):
                return None
            ranked = []
            for index, directory in enumerate(dict.fromkeys(directories)):
                if any(part in ('', '.', '..') for part in directory.split('/')):
                    return None
                size = parser.getint(directory, 'Size')
                scale = parser.getint(directory, 'Scale', fallback=1)
                kind = parser.get(directory, 'Type', fallback='Threshold')
                if not 0 < size <= 8192 or not 0 < scale <= 16:
                    return None
                if kind == 'Scalable':
                    low = parser.getint(directory, 'MinSize', fallback=size)
                    high = parser.getint(directory, 'MaxSize', fallback=size)
                    if not 0 < low <= high <= 8192:
                        return None
                elif kind == 'Threshold':
                    threshold = parser.getint(directory, 'Threshold', fallback=2)
                    if not 0 <= threshold <= 8192:
                        return None
                    low, high = size - threshold, size + threshold
                elif kind == 'Fixed':
                    low = high = size
                else:
                    return None
                distance = max(low * scale - 32, 32 - high * scale, 0)
                exact = scale == 1 and low <= 32 <= high
                ranked.append((not exact, distance, index, directory))
            result = (tuple(item[3] for item in sorted(ranked)), tuple(parents))
            self.cache[name] = result
            return result
        except (OSError, UnicodeError, ValueError, configparser.Error):
            return None

    @staticmethod
    def _list(parser, key):
        return [item.strip() for item in parser.get('Icon Theme', key, fallback='').split(',')
                if item.strip()]

    def _find(self, theme, icon, seen, depth=0):
        if theme in seen or len(seen) >= MAX_THEMES or depth > MAX_DEPTH:
            return None
        seen.add(theme)
        data = self._metadata(theme)
        if data is None:
            return None
        directories, parents = data
        for directory in directories:
            for root in self.roots:
                for suffix in ('.png', '.svg', '.xpm'):
                    if self.remaining_probes <= 0:
                        raise _PreviewLimit
                    self.remaining_probes -= 1
                    path = self._file(root / theme / directory / (icon + suffix), MAX_ICON_BYTES)
                    if path is not None:
                        return str(path)
        for parent in parents:
            # hicolor is the final fallback, even if listed before another parent.
            if parent == 'hicolor':
                continue
            found = self._find(parent, icon, seen, depth + 1)
            if found is not None:
                return found
        return None

    def samples(self, theme):
        self.remaining_probes = MAX_FILE_PROBES
        if self._metadata(theme) is None:
            return []
        result = []
        for name in SAMPLE_NAMES:
            try:
                source = self._find(theme, name, set())
                if source is None and theme != 'hicolor':
                    source = self._find('hicolor', name, set())
            except _PreviewLimit:
                break
            if source is not None:
                result.append({'name': name, 'source': source})
        return result
