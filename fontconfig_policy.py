"""Narrow, byte-preserving repair of a user's generic-monospace rule.

Only the reviewed Omarchy family/prepend_first rule is edited. Its first-value
test cannot take over an explicitly requested family just because fontconfig
added monospace later as a fallback. System rules run earlier on some systems;
this file cannot recover an original generic request they have already changed.
"""
from dataclasses import dataclass, field
import re
from xml.parsers import expat
from xml.sax.saxutils import escape

DEFAULT = '<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n<fontconfig>\n</fontconfig>\n'


@dataclass
class Node:
    tag: str
    attrs: dict
    start: int
    open_end: int
    close_start: int = 0
    end: int = 0
    children: list = field(default_factory=list)
    text: list = field(default_factory=list)


def _tag_end(raw, start):
    quote = None
    for index in range(start, len(raw)):
        value = raw[index]
        if quote is not None:
            if value == quote:
                quote = None
        elif value in (34, 39):
            quote = value
        elif value == 62:
            return index + 1
    raise ValueError('Incomplete fontconfig XML tag')


def _parse(raw):
    if len(raw) > 16 * 1024 * 1024:
        raise ValueError('Fontconfig configuration exceeds the size limit')
    parser = expat.ParserCreate()
    stack, roots = [], []

    def start(tag, attrs):
        if len(stack) >= 64:
            raise ValueError('Fontconfig XML nesting exceeds the reviewed limit')
        node = Node(tag, attrs, parser.CurrentByteIndex,
                    _tag_end(raw, parser.CurrentByteIndex))
        (stack[-1].children if stack else roots).append(node)
        stack.append(node)

    def end(tag):
        node = stack.pop()
        node.close_start = parser.CurrentByteIndex
        node.end = (_tag_end(raw, node.close_start)
                    if raw[node.close_start:node.close_start + 2] == b'</'
                    else node.close_start)

    def doctype(name, system, public, internal):
        if name != 'fontconfig' or public or internal or system not in (None, 'fonts.dtd', 'urn:fontconfig:fonts.dtd'):
            raise ValueError('Custom fontconfig DTDs or entities need a reviewed adapter')

    def entity(*args):
        raise ValueError('Fontconfig entity declarations need a reviewed adapter')

    def declaration(version, encoding, standalone):
        if version != '1.0' or (encoding and encoding.casefold() != 'utf-8'):
            raise ValueError('Fontconfig configuration must use XML 1.0 and UTF-8')

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = lambda text: stack[-1].text.append(text) if stack else None
    parser.StartDoctypeDeclHandler = doctype
    parser.XmlDeclHandler = declaration
    parser.EntityDeclHandler = entity
    parser.ExternalEntityRefHandler = lambda *args: 0
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    try:
        parser.Parse(raw, True)
    except expat.ExpatError as exc:
        raise ValueError('Fontconfig configuration is not supported XML: ' + str(exc)) from exc
    if len(roots) != 1 or roots[0].tag != 'fontconfig' or roots[0].attrs or ''.join(roots[0].text).strip():
        raise ValueError('Expected a plain fontconfig document')
    return roots[0]


def _value(node, tag):
    if node.tag != tag or node.attrs or node.children:
        return None
    return ''.join(node.text).strip()


def _simple_test(node):
    if (node.tag != 'test' or len(node.children) != 1
            or node.attrs.get('name') != 'family'
            or set(node.attrs) - {'name', 'qual', 'compare', 'target'}
            or node.attrs.get('compare', 'eq') != 'eq'
            or node.attrs.get('target', 'pattern') not in ('pattern', 'default')
            or ''.join(node.text).strip()):
        return None
    return _value(node.children[0], 'string')


def _reviewed_rule(node):
    if (node.tag != 'match' or node.attrs not in ({}, {'target': 'pattern'})
            or [child.tag for child in node.children] != ['test', 'edit']
            or ''.join(node.text).strip()):
        return None
    test, edit = node.children
    if (_simple_test(test) != 'monospace'
            or test.attrs.get('qual', 'any') not in ('any', 'first')
            or edit.attrs != {'name': 'family', 'mode': 'prepend_first', 'binding': 'strong'}
            or len(edit.children) != 1 or ''.join(edit.text).strip()
            or not _value(edit.children[0], 'string')):
        return None
    return test, edit.children[0]


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)


def _check_unrelated(node, family):
    # Following includes could edit arbitrary additional files or import another
    # family override; neither belongs to this exact target's transaction.
    if any(item.tag == 'include' for item in _walk(node)):
        raise ValueError('Fontconfig includes need a reviewed adapter; existing configuration was preserved')
    if node.tag == 'alias':
        sources = [_value(child, 'family') for child in node.children if child.tag == 'family']
        if not sources or any(value is None or value.casefold() in {'monospace', family.casefold()} for value in sources):
            raise ValueError('A competing fontconfig family alias needs review; existing configuration was preserved')
        return
    family_edits = [item for item in _walk(node) if item.tag == 'edit' and item.attrs.get('name') == 'family']
    if family_edits:
        # A first-family equality test for another explicit name proves the
        # rule cannot take over monospace or the selected terminal family.
        unrelated_first = any(
            (value := _simple_test(child)) and child.attrs.get('qual') == 'first'
            and value.casefold() not in {'monospace', family.casefold()}
            for child in node.children)
        if node.tag != 'match' or node.attrs not in ({}, {'target': 'pattern'}) or not unrelated_first:
            raise ValueError('An unrecognized fontconfig family override needs review; existing configuration was preserved')
    if any(item.tag == 'alias' for item in _walk(node)):
        raise ValueError('A nested fontconfig alias needs review; existing configuration was preserved')


def validate_rules(rules):
    """Journal values contain only complete reviewed match elements."""
    if not isinstance(rules, list) or len(rules) > 64:
        raise ValueError('Invalid managed fontconfig rule list')
    for text in rules:
        if not isinstance(text, str):
            raise ValueError('Invalid managed fontconfig rule')
        raw = text.encode('utf-8')
        wrapped = b'<fontconfig>' + raw + b'</fontconfig>'
        root = _parse(wrapped)
        if (len(root.children) != 1 or _reviewed_rule(root.children[0]) is None
                or wrapped[root.children[0].start:root.children[0].end] != raw):
            raise ValueError('Managed fontconfig metadata contains an unreviewed rule')


def _configuration(raw):
    root = _parse(raw)
    nodes = [node for node in root.children if _reviewed_rule(node) is not None]
    families = [_value(_reviewed_rule(node)[1], 'string') for node in nodes] or ['']
    for node in root.children:
        if node not in nodes:
            for family in families:
                _check_unrelated(node, family)
    return root, nodes


def decode(text):
    if not text.strip():
        return {'_text': text, 'monospace-rule': []}
    raw = text.encode('utf-8')
    _, nodes = _configuration(raw)
    rules = [raw[node.start:node.end].decode('utf-8') for node in nodes]
    validate_rules(rules)
    return {'_text': text, 'monospace-rule': rules}


def encode(data):
    """Merge only reviewed match spans into the latest unowned XML bytes."""
    text = data.get('_text', '')
    if not isinstance(text, str):
        raise ValueError('Invalid fontconfig document')
    rules = data.get('monospace-rule', [])
    validate_rules(rules)
    if not text.strip() and not rules:
        return text
    raw = (text if text.strip() else DEFAULT).encode('utf-8')
    root, nodes = _configuration(raw)
    edits = []
    if len(nodes) == len(rules):
        edits = [(node.start, node.end, rule.encode('utf-8')) for node, rule in zip(nodes, rules)]
    elif nodes:
        edits = [(node.start, node.end, b'') for node in nodes]
        edits[0] = (nodes[0].start, nodes[0].end, '\n'.join(rules).encode('utf-8'))
    elif rules:
        addition = ('\n' + '\n'.join(rules) + '\n').encode('utf-8')
        if raw[root.open_end - 2:root.open_end] == b'/>':
            edits.append((root.open_end - 2, root.open_end, b'>' + addition + b'</fontconfig>'))
        else:
            edits.append((root.close_start, root.close_start, addition))
    for start, end, replacement in sorted(edits, reverse=True):
        raw = raw[:start] + replacement + raw[end:]
    result = raw.decode('utf-8')
    if decode(result)['monospace-rule'] != rules:
        raise ValueError('Fontconfig rule merge readback did not match')
    return result


def build(text, family):
    if (not isinstance(family, str) or not family or len(family) > 300
            or any(ord(char) < 32 for char in family)):
        raise ValueError('Invalid fontconfig font family')
    try:
        wanted = escape(family).encode('utf-8')
        raw = text.encode('utf-8')
    except UnicodeError as exc:
        raise ValueError('Fontconfig configuration and font family must be valid UTF-8') from exc
    if not raw.strip():
        raw = DEFAULT.encode('utf-8')
    root = _parse(raw)
    edits = []
    for node in root.children:
        reviewed = _reviewed_rule(node)
        if reviewed is None:
            _check_unrelated(node, family)
            continue
        test, value = reviewed
        opening = raw[test.start:test.open_end]
        if 'qual' in test.attrs:
            opening, count = re.subn(rb'\bqual\s*=\s*([\"\']).*?\1', b'qual="first"', opening, count=1)
            if count != 1:
                raise ValueError('Unsupported fontconfig qualifier syntax')
        else:
            opening = opening[:-1] + b' qual="first">'
        edits.extend(((test.start, test.open_end, opening),
                      (value.open_end, value.close_start, wanted)))
    if not edits:
        rule = (b'  <match target="pattern">\n'
                b'    <test name="family" qual="first"><string>monospace</string></test>\n'
                b'    <edit name="family" mode="prepend_first" binding="strong"><string>'
                + wanted + b'</string></edit>\n  </match>\n')
        if raw[root.open_end - 2:root.open_end] == b'/>':
            edits.append((root.open_end - 2, root.open_end, b'>\n' + rule + b'</fontconfig>'))
        else:
            edits.append((root.close_start, root.close_start, b'\n' + rule))
    for start, end, replacement in sorted(edits, reverse=True):
        raw = raw[:start] + replacement + raw[end:]
    _parse(raw)
    return raw.decode('utf-8')
