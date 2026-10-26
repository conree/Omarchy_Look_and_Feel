"""Read-only capability checks with actionable installation guidance."""
import shutil


def inspect():
    checks=[]
    def add(name, okay, areas, remedy):
        checks.append({'name':name, 'available':bool(okay), 'areas':areas, 'remedy':remedy if not okay else ''})
    for name, command, areas, package in (
        ('Font discovery','fc-list',['fonts'],'fontconfig'),
        ('Font matching','fc-match',['fonts'],'fontconfig'),
        ('Omarchy dispatcher','omarchy',['theme','background'],'omarchy'),
        ('Omarchy theme command','omarchy-theme-set',['theme'],'omarchy'),
        ('Omarchy background command','omarchy-theme-bg-set',['background'],'omarchy'),
        ('Omarchy shell','omarchy-shell',['theme','background'],'omarchy'),
        ('Hyprland control','hyprctl',['theme'],'hyprland'),
        ('Application process checks','pgrep',['fonts','theme'],'procps-ng'),
        ('Terminal reload signals','pkill',['fonts','theme'],'procps-ng'),
    ):
        add(name, shutil.which(command), areas, 'Install the '+package+' package.')
    try:
        import desktop_fonts
        desktop_fonts._settings()
        available=True
    except (ImportError, ValueError, RuntimeError):
        available=False
    add('Desktop settings',available,['desktop','fonts','theme','icons'], 'Install python-gobject and gsettings-desktop-schemas.')
    try:
        from controller import OMARCHY_ROOT
        from theme_runtime import require_offline_support
        require_offline_support(OMARCHY_ROOT)
        available=True
    except (OSError, RuntimeError):
        available=False
    add('Safe theme generation',available,['theme'], 'Use an Omarchy build with the supported OMARCHY_THEME_HEADLESS branch; this build cannot safely apply themes.')
    try:
        from PySide6.QtCore import QPluginLoader
        from PySide6.QtGui import QFont
        available=True
    except ImportError:
        available=False
    add('Qt metadata and font validation',available,['qt','fonts','font-restore'], 'Install pyside6.')
    from qt_integration import plugins
    found=plugins()
    add('Shared Qt 5/6 integration', bool(found.get(5,set()) & found.get(6,set())), ['qt'], 'Install compatible qt5ct and qt6ct packages, then press Apply and sign out and back in once.')
    return {'checks':checks, 'ready':all(row['available'] for row in checks),
            'bootUnlock':'explicit administrator approval; standard unsigned Omarchy UKIs only', 'renderedAppearanceVerified':False}


def require(area):
    failures=[row for row in inspect()['checks'] if area in row['areas'] and not row['available']]
    if failures:
        raise RuntimeError(' '.join(dict.fromkeys(row['remedy'] for row in failures)))
