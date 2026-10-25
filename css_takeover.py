"""Remove competing appearance declarations while keeping CSS layout intact.

This scanner understands comments, strings, escapes, and nested functions and
blocks. It intentionally rejects imports: an external stylesheet must not be
silently treated as controlled. It never executes or follows CSS URLs.
"""
import re

COLOR_PROPERTIES = {'color', 'background', 'background-color', 'background-image',
                    'border-color', 'border-top-color', 'border-bottom-color',
                    'border-left-color', 'border-right-color', 'outline-color',
                    'box-shadow', 'text-shadow', '-gtk-icon-shadow', 'caret-color',
                    'text-decoration-color', 'fill', 'stroke'}
FONT_PROPERTIES = {'font', 'font-family', 'font-size'}


def _tokens(text):
    i, start, stack = 0, 0, []
    while i < len(text):
        c = text[i]
        if text.startswith('/*', i):
            end = text.find('*/', i + 2)
            if end < 0:
                raise ValueError('unterminated CSS comment')
            i = end + 2
            continue
        if c in '\"\'':
            quote = c
            i += 1
            while i < len(text) and text[i] != quote:
                i += 2 if text[i] == '\\' else 1
            if i >= len(text):
                raise ValueError('unterminated CSS string')
        elif c == '\\':
            i += 2
            continue
        elif c in '([':
            stack.append(c)
        elif c in ')]':
            if not stack or stack.pop() != ( '(' if c == ')' else '['):
                raise ValueError('unbalanced CSS function')
        elif not stack and c in '{};':
            yield text[start:i], c
            start = i + 1
        i += 1
    if stack:
        raise ValueError('unbalanced CSS function')
    yield text[start:], ''


def _plain(text):
    return re.sub(r'/\*.*?\*/', '', text, flags=re.S).strip()


def strip_appearance(text):
    # Fonts already owned by the plugin have separate transaction ownership.
    from app_font_actions import BEGIN, END
    protected = None
    if BEGIN in text or END in text:
        if text.count(BEGIN) != 1 or text.count(END) != 1 or text.index(BEGIN) > text.index(END):
            raise ValueError('malformed managed font CSS block')
        a, b = text.index(BEGIN), text.index(END) + len(END)
        protected = text[a:b]
        text = text[:a] + '/* LAF_FONT_PLACEHOLDER */' + text[b:]
    output, contexts = [], []
    for token, delimiter in _tokens(text):
        plain = _plain(token)
        if plain.casefold().startswith('@import'):
            raise ValueError('CSS imports require a supported stylesheet adapter before takeover')
        if delimiter == '{':
            contexts.append(plain)
            output.extend((token, delimiter))
            continue
        keep = True
        if plain.casefold().startswith('@define-color'):
            keep = False
        elif contexts and not any('@font-face' in context.casefold() for context in contexts):
            prop = plain.split(':', 1)[0].strip().casefold()
            special = any(re.search(r'(icon|symbol|katex|math|mermaid|fa-)', context, re.I) for context in contexts)
            keep = prop not in COLOR_PROPERTIES and (special or prop not in FONT_PROPERTIES)
            if prop.startswith('--') and any(word in prop for word in ('color', 'background')):
                keep = False
        if keep:
            output.append(token)
            if delimiter == ';':
                output.append(';')
        if delimiter == '}':
            if not contexts:
                raise ValueError('unbalanced CSS block')
            contexts.pop()
            output.append('}')
    if contexts:
        raise ValueError('unbalanced CSS block')
    result = ''.join(output)
    if protected is not None:
        result = result.replace('/* LAF_FONT_PLACEHOLDER */', protected)
    return result
