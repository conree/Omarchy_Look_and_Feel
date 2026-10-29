"""Field ownership for terminal fonts and opacity, preserving unrelated text.

These codecs never evaluate terminal configuration. Unsupported TOML layouts
are refused rather than rewritten with a guessed meaning.
"""
import re
import tomllib

FONT_FIELDS = {
    'ghostty-config': {'font-import'},
    'kitty-config': {'font_family', 'font_size'},
    'foot-config': {'main/font', 'main/dpi-aware'},
    'alacritty-config': {'font'},
    'wezterm-config': {'fonts'},
}
OPACITY_FIELDS = {
    'ghostty-config': {'background-opacity', 'background-opacity-cells', 'opacity-css-import'},
    'kitty-config': {'background_opacity'},
    'foot-config': {'colors/alpha', 'colors-dark/alpha', 'colors-light/alpha'},
    'alacritty-config': {'window/opacity'},
    'wezterm-config': {'opacity'},
}
FIELDS = {name: FONT_FIELDS[name] | OPACITY_FIELDS[name]
          for name in FONT_FIELDS if name != 'wezterm-config'}


def _heading(line):
    match = re.fullmatch(r'\s*\[([^\[\]]+)\]\s*(?:[#;].*)?\n?', line)
    return match[1].strip() if match else None


def _matches(target, text, field):
    section, key = field.split('/', 1) if '/' in field else ('', field)
    current, matches = '', []
    for index, line in enumerate(text.splitlines(keepends=True)):
        if target in {'foot-config', 'alacritty-config'}:
            heading = _heading(line)
            if heading is not None:
                current = heading
                continue
        if field == 'font-import':
            matched = re.fullmatch(r'\s*config-file\s*=\s*["\']?look-and-feel-font\.conf["\']?\s*\n?', line)
        elif field == 'opacity-css-import':
            from pathlib import Path
            from transaction import FILE_TARGETS
            import json
            expected = str(Path.home() / FILE_TARGETS['ghostty-opacity-css'])
            match = re.fullmatch(r'\s*gtk-custom-css\s*=\s*(.*?)\s*\n?', line)
            matched = bool(match and match[1] in {expected, json.dumps(expected)})
        else:
            separator = r'\s+' if target == 'kitty-config' else r'\s*=\s*'
            matched = current == section and re.match(r'\s*' + re.escape(key) + separator, line)
            if target == 'alacritty-config' and not current:
                matched = matched or re.match(r'\s*window\.opacity\s*=', line)
        if matched:
            matches.append((index, line))
    if len(matches) > 1:
        raise ValueError(f'{target}: duplicate managed setting {field}')
    return matches


def _font_blocks(text):
    lines, blocks, start = text.splitlines(keepends=True), [], None
    for index, line in enumerate(lines + ['[__end__]\n']):
        heading = _heading(line)
        if heading is None:
            continue
        if start is not None:
            blocks.append((start, index, ''.join(lines[start:index])))
            start = None
        if heading == 'font' or heading.startswith('font.'):
            start = index
    return blocks


def decode(target, raw):
    text = raw.decode('utf-8')
    if target == 'alacritty-config':
        parsed = tomllib.loads(text)
        # Line-based editing must never mistake a multiline literal for config.
        if '\"\"\"' in text or "'''" in text:
            raise ValueError('Alacritty multiline strings need manual configuration')
        if 'font' in parsed and not _font_blocks(text):
            raise ValueError('Alacritty fonts need ordinary [font] tables')
        if 'opacity' in parsed.get('window', {}) and not _matches(target, text, 'window/opacity'):
            raise ValueError('Alacritty opacity needs [window] or window.opacity syntax')
    data = {'_text': text}
    for field in FIELDS[target]:
        if field == 'font':
            data[field] = [row[2] for row in _font_blocks(text)]
        else:
            found = _matches(target, text, field)
            data[field] = found[0][1] if found else None
    return data


def _replace(target, text, field, wanted):
    lines = text.splitlines(keepends=True)
    if field == 'font':
        blocks = _font_blocks(text)
        at = blocks[0][0] if blocks else len(lines)
        for start, end, _ in reversed(blocks):
            del lines[start:end]
        if wanted:
            lines.insert(at, ''.join(wanted))
        return ''.join(lines)
    found = _matches(target, text, field)
    if found:
        index = found[0][0]
        lines[index:index + 1] = [wanted] if wanted is not None else []
    elif wanted is not None:
        section = field.split('/', 1)[0] if '/' in field else ''
        if section:
            at = next((i + 1 for i, line in enumerate(lines) if _heading(line) == section), None)
            if at is None:
                if lines and not lines[-1].endswith('\n'):
                    lines[-1] += '\n'
                lines.extend(['[' + section + ']\n', wanted])
            else:
                lines.insert(at, wanted)
        else:
            if lines and not lines[-1].endswith('\n'):
                lines[-1] += '\n'
            lines.append(wanted)
    return ''.join(lines)


def encode(target, data):
    text = data.get('_text', '')
    old = decode(target, text.encode())
    desired = {field: data.get(field, [] if field == 'font' else None) for field in FIELDS[target]}
    for field in sorted(FIELDS[target]):
        wanted = desired[field]
        if old.get(field) != wanted:
            text = _replace(target, text, field, wanted)
    # Reject a malformed restoration payload before the transaction writes it.
    actual = decode(target, text.encode())
    if any(actual.get(field) != desired[field] for field in FIELDS[target]):
        raise ValueError('Unsupported terminal preference restoration')
    return text.encode()
