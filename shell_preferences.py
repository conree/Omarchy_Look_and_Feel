"""Own font size and Flea opacity separately in the shared shell TOML."""
import math
import re
import tomllib

FIELDS = {'font/base-size', 'flea/background-alpha'}


def _locations(text, field):
    section, key = field.split('/')
    current, found, insertion = '', [], None
    for i, line in enumerate(text.splitlines(keepends=True)):
        heading = re.fullmatch(r'\s*\[([^\[\]]+)\]\s*(?:#.*)?\r?\n?', line)
        if heading:
            current = heading[1].strip()
            if current == section:
                insertion = i + 1
        elif re.match(r'\s*\[', line):
            current = ''
        elif current == section and re.match(r'\s*' + re.escape(key) + r'\s*=', line):
            found.append((i, line))
    if len(found) > 1:
        raise ValueError('Duplicate shell setting: ' + field)
    return found, insertion


def decode(raw):
    text = raw.decode('utf-8')
    values = tomllib.loads(text)
    if '"""' in text or "'''" in text:
        raise ValueError('Multiline shell TOML needs manual review; settings preserved')
    data = {'_text': text}
    for field in FIELDS:
        section, key = field.split('/')
        table = values.get(section, {})
        if not isinstance(table, dict):
            raise ValueError('Shell settings need ordinary section tables')
        found, _ = _locations(text, field)
        if key in table:
            value = table[key]
            if not found or type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError('Unsupported shell setting: ' + field)
            if field == 'flea/background-alpha' and not 0 <= value <= 1:
                raise ValueError('Flea background opacity must be between 0 and 1')
        elif found:
            raise ValueError('Ambiguous shell setting: ' + field)
        # Adding another section may terminate an EOF line. Treat that newline
        # as layout, so another control cannot appear to change this field.
        data[field] = found[0][1].rstrip('\r\n') + '\n' if found else None
    return data


def encode(data):
    text = data.get('_text', '')
    before = decode(text.encode())
    for field in sorted(FIELDS):
        wanted = data.get(field)
        if before[field] == wanted:
            continue
        section, key = field.split('/')
        if wanted is not None:
            if not isinstance(wanted, str) or len(wanted.splitlines()) != 1:
                raise ValueError('Invalid shell setting restoration')
            probe = decode(('[' + section + ']\n' + wanted + '\n').encode())
            if probe[field] is None:
                raise ValueError('Invalid shell setting restoration')
        found, insertion = _locations(text, field)
        lines = text.splitlines(keepends=True)
        if found:
            i = found[0][0]
            lines[i:i + 1] = [wanted] if wanted is not None else []
        elif wanted is not None:
            if insertion is None:
                if lines and not lines[-1].endswith('\n'):
                    lines[-1] += '\n'
                lines.extend(['[' + section + ']\n', wanted])
            else:
                if not lines[insertion - 1].endswith('\n'):
                    lines[insertion - 1] += '\n'
                lines.insert(insertion, wanted)
        text = ''.join(lines)
    actual = decode(text.encode())
    if any(actual[field] != data.get(field) for field in FIELDS):
        raise ValueError('Shell setting restoration did not match')
    return text.encode()
