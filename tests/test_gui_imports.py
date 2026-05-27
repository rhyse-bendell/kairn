import pytest


def test_gui_imports():
    pytest.importorskip("PySide6")
    import kairn.apps.desktop.main  # noqa: F401
    import kairn.apps.desktop.tabs.dashboard  # noqa: F401
    import kairn.apps.desktop.tabs.sources  # noqa: F401
    import kairn.apps.desktop.tabs.agents  # noqa: F401
    import kairn.apps.desktop.tabs.artifacts  # noqa: F401
    import kairn.apps.desktop.tabs.timeline  # noqa: F401
    import kairn.apps.desktop.tabs.categories  # noqa: F401
    import kairn.apps.desktop.tabs.analysis  # noqa: F401
    import kairn.apps.desktop.tabs.exports  # noqa: F401
    import kairn.apps.desktop.tabs.diagnostics  # noqa: F401
