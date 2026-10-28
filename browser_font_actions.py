"""Offline default-profile font preferences. The browser must remain closed."""
from contextlib import contextmanager
from pathlib import Path
import copy,json,os,socket
import subprocess

FIELDS = {
    'standard': ('webkit','webprefs','fonts','standard','Zyyy'),
    'serif': ('webkit','webprefs','fonts','serif','Zyyy'),
    'sansserif': ('webkit','webprefs','fonts','sansserif','Zyyy'),
    'fixed': ('webkit','webprefs','fonts','fixed','Zyyy'),
    'size': ('webkit','webprefs','default_font_size'),
    'fixed_size': ('webkit','webprefs','default_fixed_font_size'),
}


def family_notes(system_family, terminal_family, desktop_ids):
    """Explain Chromium's first-family-only menu without changing font faces."""
    if 'brave-browser.desktop' not in desktop_ids:
        return []
    try:
        result = subprocess.run(['fc-list', ':scalable=true', '--format', '%{family[0]}\t%{family}\n'],
                                capture_output=True, text=True, timeout=5, check=True)
        if len(result.stdout) > 1024 * 1024:
            return []
        primary, aliases = set(), set()
        for line in result.stdout.splitlines():
            first, separator, names = line.partition('\t')
            if separator:
                primary.add(first)
                aliases.update(names.split(','))
        return [f'Brave may display Custom for {family} in its font menu. '
                'The selected font family name is preserved.'
                for family in dict.fromkeys((system_family, terminal_family))
                if family in aliases and family not in primary]
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return []


def values(data):
    if not isinstance(data, dict):raise ValueError('invalid browser preferences')
    result={}
    for key, parts in FIELDS.items():
        node=data
        for part in parts:
            if not isinstance(node,dict):raise ValueError('unsupported browser font preference structure')
            if part not in node:
                node=None
                break
            node=node[part]
            if node is None and part != parts[-1]:
                raise ValueError('unsupported null browser preference structure')
        result[key]=node
    validate(result)
    return result


def validate(row):
    if not isinstance(row,dict) or set(row)!=set(FIELDS):raise ValueError('invalid browser font snapshot')
    for key,value in row.items():
        if value is None:continue
        if key in ('size','fixed_size'):
            if type(value) is not int or not 1 <= value <= 200:raise ValueError('invalid browser font size')
        elif not isinstance(value,str) or len(value)>300 or any(ord(c)<32 for c in value):
            raise ValueError('invalid browser font family')


def merge(data,row):
    values(data);validate(row);result=copy.deepcopy(data)
    for key,parts in FIELDS.items():
        node=result
        for part in parts[:-1]:
            node=node.setdefault(part,{})
        if row[key] is None:node.pop(parts[-1],None)
        else:node[parts[-1]]=row[key]
    return result


def busy(path):
    lock=Path(path).parent.parent/'SingletonLock'
    return lock.exists() or lock.is_symlink()


def assert_closed_default(path):
    path=Path(path)
    from transaction import _ensure_home_path
    _ensure_home_path(path,allow_missing_leaf=False)
    if busy(path):
        raise RuntimeError('Close Brave and keep it closed until font Apply or Undo finishes.')
    state=path.parent.parent/'Local State'
    if state.exists():
        _ensure_home_path(state,allow_missing_leaf=False)
        data=json.loads(state.read_text())
        if not isinstance(data,dict) or not isinstance(data.get('profile',{}),dict):
            raise ValueError('unsupported browser profile metadata')
        if data.get('profile',{}).get('last_used','Default')!='Default':
            raise RuntimeError('the supported browser profile is not selected')


@contextmanager
def lock_paths(paths):
    # The transaction's own lock serializes plugin writers. Chromium does not
    # honor an advisory Python lock: require it to remain closed, and check at
    # each write as well. Do not manufacture a Chromium SingletonLock.
    browsers=[Path(p) for p in paths if Path(p).name=='Preferences']
    for path in browsers:assert_closed_default(path)
    yield


def build(system_family,system_size,terminal_family,terminal_size,desktop_ids):
    if 'brave-browser.desktop' not in desktop_ids:return {},[]
    from transaction import FILE_TARGETS
    from global_font_actions import HOME,_read
    path=HOME/FILE_TARGETS['brave-default-preferences']
    if not path.is_file():return {},[{'app':'Brave','action':'profile-unresolved','reason':'The supported default browser profile was not found.'}]
    state=path.parent.parent/'Local State'
    if state.is_file():
        last=json.loads(_read(state)).get('profile',{}).get('last_used','Default')
        if last!='Default':return {},[{'app':'Brave','action':'profile-unresolved','reason':'The selected browser profile needs a reviewed font adapter.'}]
    data=json.loads(_read(path))
    selected={'standard':system_family,'serif':system_family,'sansserif':system_family,'fixed':terminal_family,
              'size':round(system_size*96/72),'fixed_size':round(terminal_size*96/72)}
    if values(data) == selected:return {},[]
    if busy(path):return {},[{'app':'Brave','action':'close-and-apply','reason':'Save work and close the browser, then keep it closed while applying its font defaults.'}]
    return {'brave-default-preferences':(json.dumps(merge(data,selected),ensure_ascii=False,separators=(',',':'))+'\n').encode()},[]
