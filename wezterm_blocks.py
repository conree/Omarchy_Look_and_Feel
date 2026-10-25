"""Independent font/theme overrides in ordinary WezTerm configuration files.

Original Lua is retained, never evaluated here. Only a final top-level return of
`config` is supported. Lexing strings/comments and block nesting prevents an
override being injected into a function, string, or conditional return.
"""
import json
import re

DEFAULT = 'local config = {}\nreturn config\n'
ROLES = ('fonts', 'theme')


def _tokens(text, comments=False):
    i = 0
    while i < len(text):
        start = i
        if text[i].isspace():
            i += 1
            continue
        comment = text.startswith('--', i)
        if comment:
            i += 2
        long = re.match(r'\[(=*)\[', text[i:])
        if long:
            end = text.find(']' + long[1] + ']', i + len(long[0]))
            if end < 0:
                raise ValueError('Unterminated Lua long string or comment')
            i = end + len(long[1]) + 2
            if not comment:
                yield 'STRING', start, i
            elif comments:
                yield 'COMMENT', start, i
        elif comment:
            end = text.find('\n', i)
            i = len(text) if end < 0 else end + 1
            if comments:
                yield 'COMMENT', start, i
        elif text[i] in '\"\'':
            quote = text[i]
            i += 1
            while i < len(text) and text[i] != quote:
                i += 2 if text[i] == '\\' else 1
            if i >= len(text):
                raise ValueError('Unterminated Lua string')
            i += 1
            yield 'STRING', start, i
        else:
            word = re.match(r'[A-Za-z_][A-Za-z_0-9]*', text[i:])
            i += len(word[0]) if word else 1
            yield text[start:i], start, i


def insertion(text):
    tokens = list(_tokens(text))
    stack, returns, bound = [], [], False
    for index, (word, start, end) in enumerate(tokens):
        if not stack:
            if word == 'local' and [row[0] for row in tokens[index:index + 3]] == ['local', 'config', '=']:
                bound = True
            if word == 'return':
                returns.append(index)
        if word in ('(', '[', '{', 'function', 'if', 'do', 'repeat'):
            stack.append(word)
        elif word in (')', ']', '}', 'end', 'until'):
            allowed = {')': {'('}, ']': {'['}, '}': {'{'}, 'end': {'function', 'if', 'do'}, 'until': {'repeat'}}
            if not stack or stack.pop() not in allowed[word]:
                raise ValueError('Unsupported Lua block structure')
    if stack or not bound or len(returns) != 1 or [t[0] for t in tokens[returns[0]:]] not in (['return', 'config'], ['return', 'config', ';']):
        raise ValueError('WezTerm needs a local config and a final unconditional return config')
    position = tokens[returns[0]][1]
    line = text.rfind('\n', 0, position) + 1
    if text[line:position].strip():
        raise ValueError('WezTerm return config must be on its own line')
    return line


def decode(text):
    data = {'body': text or DEFAULT, 'fonts': None, 'theme': None}
    comments = {a for kind, a, b in _tokens(text, comments=True) if kind == 'COMMENT'}
    for role in ROLES:
        for suffix in ('BEGIN', 'END'):
            marker = '-- Look and Feel ' + role + ' ' + suffix + '\n'
            if marker in text and text.index(marker) not in comments:
                raise ValueError('WezTerm managed marker is inside a Lua literal')
    for role in ROLES:
        begin = '-- Look and Feel ' + role + ' BEGIN\n'
        end = '-- Look and Feel ' + role + ' END\n'
        body = data['body']
        if begin not in body and end not in body:
            continue
        if body.count(begin) != 1 or body.count(end) != 1:
            raise ValueError('Malformed WezTerm managed block')
        a, b = body.index(begin), body.index(end)
        if b < a or (a and body[a - 1] != '\n'):
            raise ValueError('Malformed WezTerm managed block')
        data[role] = body[a + len(begin):b]
        data['body'] = body[:a] + body[b + len(end):]
    insertion(data['body'])
    if any(data[role] for role in ROLES) and encode(data) != text:
        raise ValueError('WezTerm managed blocks must precede the final return in canonical order')
    return data


def encode(data):
    body = data.get('body') or DEFAULT
    at = insertion(body)
    blocks = ''.join('-- Look and Feel ' + role + ' BEGIN\n' + data[role] + '-- Look and Feel ' + role + ' END\n'
                     for role in ROLES if data.get(role))
    return body[:at] + blocks + body[at:]


def fonts(text, family, size):
    data = decode(text)
    data['fonts'] = f'config.font = require("wezterm").font({json.dumps(family, ensure_ascii=False)}, {{ weight = "Regular" }})\nconfig.font_size = {int(size)}\n'
    return encode(data)


def ansi(colors):
    from application_themes import readable
    names = ['background', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'foreground',
             'muted', 'bright_red', 'bright_green', 'bright_yellow', 'bright_blue', 'bright_magenta', 'bright_cyan', 'foreground']
    return [readable(colors.get('color' + str(i), colors.get(name, colors.get(name.removeprefix('bright_'), colors['foreground']))), colors['background'])
            for i, name in enumerate(names)]


def theme(text, colors):
    data = decode(text)
    values = {key: colors[value] for key, value in {
        'foreground': 'foreground', 'background': 'background', 'cursor_bg': 'foreground',
        'cursor_border': 'foreground', 'cursor_fg': 'background',
        'selection_bg': 'selection', 'selection_fg': 'selection_foreground',
    }.items()}
    if any(not re.fullmatch(r'#[0-9a-fA-F]{6}', value) for value in values.values()):
        raise ValueError('WezTerm palette must contain hex colors')
    lines = ['config.color_scheme = nil', 'config.colors = {']
    lines.extend('  ' + key + ' = ' + json.dumps(value) + ',' for key, value in values.items())
    colors16 = ansi(colors)
    for key, group in [('ansi', colors16[:8]), ('brights', colors16[8:])]:
        lines.append('  ' + key + ' = { ' + ', '.join(json.dumps(c) for c in group) + ' },')
    lines.append('}')
    data['theme'] = '\n'.join(lines) + '\n'
    return encode(data)
