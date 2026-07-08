from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read_script(name: str) -> str:
    return (REPO_ROOT / name).read_text(encoding="utf-8").lower()


def test_windows_launcher_scripts_exist() -> None:
    assert (REPO_ROOT / "launch_kairn_gui.bat").is_file()
    assert (REPO_ROOT / "setup_kairn.bat").is_file()


def test_launch_script_is_not_an_installer() -> None:
    launch_script = _read_script("launch_kairn_gui.bat")

    forbidden_terms = [
        "pip install",
        "install -e",
        "kairn-gui",
        'mkdir "kairn_workspace"',
        "mkdir kairn_workspace",
    ]
    for term in forbidden_terms:
        assert term not in launch_script

    assert "-m kairn.apps.desktop.main" in launch_script


def test_setup_script_handles_installation() -> None:
    setup_script = _read_script("setup_kairn.bat")

    assert "pip install" in setup_script
    assert ".[gui]" in setup_script
    assert "venv" in setup_script
