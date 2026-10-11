"""Import-boundary checks; these do not replace Hermes catalog validation."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import textwrap
import venv

import pytest


ROOT = Path(__file__).resolve().parents[1]

# Match Hermes' directory import boundary: a namespaced package whose search
# path is the plugin directory, without adding that directory to sys.path.
DIRECTORY_LOADER = """
import importlib.util
from pathlib import Path
import sys
import types

def load_directory(plugin_dir):
    namespace = types.ModuleType("hermes_plugins")
    namespace.__path__ = []
    namespace.__package__ = "hermes_plugins"
    sys.modules["hermes_plugins"] = namespace
    name = "hermes_plugins.doctorpack"
    spec = importlib.util.spec_from_file_location(
        name, plugin_dir / "__init__.py",
        submodule_search_locations=[str(plugin_dir)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

plugin_dir = Path(sys.argv[1]).resolve()
assert not Path.cwd().is_relative_to(plugin_dir)
assert str(plugin_dir) not in sys.path
assert str(plugin_dir.parent) not in sys.path
"""


def run_python(python, cwd, *args):
    # Nothing in these tests should consult the user's Hermes home or pip config.
    env = dict(os.environ)
    env.update(
        HOME=str(cwd),
        USERPROFILE=str(cwd),
        HERMES_HOME=str(cwd / "synthetic-hermes-home"),
        PIP_CONFIG_FILE=os.devnull,
        PIP_NO_INDEX="1",
    )
    result = subprocess.run(
        [str(python), "-I", *map(str, args)],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def venv_python(path, *, with_pip=False):
    venv.EnvBuilder(with_pip=with_pip).create(path)
    return path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


@pytest.fixture(scope="module")
def isolated_python(tmp_path_factory):
    """No editable install, third-party packages, or user-site imports."""
    return venv_python(tmp_path_factory.mktemp("directory-env"))


@pytest.fixture(scope="module")
def built_distributions(tmp_path_factory):
    """Build an sdist and a wheel from that sdist, entirely offline."""
    work = tmp_path_factory.mktemp("wheel-env")
    source = work / "source"
    source.mkdir()
    for name in ("pyproject.toml", "README.md", "LICENSE", "MANIFEST.in", "__init__.py", "plugin.yaml"):
        shutil.copy2(ROOT / name, source / name)
    shutil.copytree(ROOT / "hermes_doctorpack", source / "hermes_doctorpack")
    shutil.copytree(ROOT / "tests", source / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    wheels = work / "wheels"
    run_python(
        sys.executable, work, "-m", "build", "--no-isolation",
        "--outdir", wheels, source,
    )
    return work


@pytest.fixture(scope="module")
def installed_python(built_distributions):
    """Install the real wheel offline into a separate, empty venv."""
    work = built_distributions
    wheel, = (work / "wheels").glob("hermes_doctorpack-*.whl")
    python = venv_python(work / "installed", with_pip=True)
    # Dependency resolution is tested separately. No network is needed to test
    # this distribution's entry point and isolation from the source checkout.
    run_python(python, work, "-m", "pip", "install", "--no-index", "--no-deps", wheel)
    return python


def test_source_distribution_includes_directory_plugin(built_distributions):
    sdist, = (built_distributions / "wheels").glob("hermes_doctorpack-*.tar.gz")
    with tarfile.open(sdist) as archive:
        names = {name.split("/", 1)[-1] for name in archive.getnames()}
    # The bundled loading tests must also work from an extracted source archive.
    assert {"__init__.py", "plugin.yaml", "MANIFEST.in", "tests/test_loading.py"} <= names


def test_directory_load_without_installed_package(isolated_python, tmp_path):
    script = DIRECTORY_LOADER + textwrap.dedent("""
        from importlib import metadata

        assert importlib.util.find_spec("hermes_doctorpack") is None
        try:
            metadata.distribution("hermes-doctorpack")
        except metadata.PackageNotFoundError:
            pass
        else:
            raise AssertionError("An installed package would mask directory loading")
        plugin = load_directory(plugin_dir)
        assert callable(plugin.register)
        assert plugin.register.__module__ == "hermes_plugins.doctorpack.hermes_doctorpack"
        inner = sys.modules[plugin.register.__module__]
        assert Path(inner.__file__).resolve() == plugin_dir / "hermes_doctorpack" / "__init__.py"
        assert "hermes_doctorpack" not in sys.modules
    """)
    run_python(isolated_python, tmp_path, "-c", script, ROOT)


def test_installed_wheel_entry_point_discovery(installed_python, tmp_path):
    script = textwrap.dedent("""
        from importlib import metadata
        import json
        from pathlib import Path
        import sys

        repo = Path(sys.argv[1]).resolve()
        assert not Path.cwd().is_relative_to(repo)
        assert str(repo) not in sys.path
        entries = metadata.entry_points(group="hermes_agent.plugins", name="doctorpack")
        entry, = entries
        assert entry.value == "hermes_doctorpack"
        plugin = entry.load()
        assert callable(plugin.register)
        assert plugin.register.__module__ == "hermes_doctorpack"
        assert Path(plugin.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
        assert not Path(plugin.__file__).resolve().is_relative_to(repo)
        distribution = metadata.distribution("hermes-doctorpack")
        assert any(str(path).endswith(".dist-info/WHEEL") for path in distribution.files)
        direct_url = json.loads(distribution.read_text("direct_url.json"))
        assert not direct_url.get("dir_info", {}).get("editable", False)
        assert "archive_info" in direct_url
    """)
    run_python(installed_python, tmp_path, "-c", script, ROOT)


def test_directory_load_prefers_local_package_over_installed_wheel(installed_python, tmp_path):
    script = DIRECTORY_LOADER + textwrap.dedent("""
        from importlib import metadata

        metadata.distribution("hermes-doctorpack")
        plugin = load_directory(plugin_dir)
        assert plugin.register.__module__ == "hermes_plugins.doctorpack.hermes_doctorpack"
        inner = sys.modules[plugin.register.__module__]
        assert Path(inner.__file__).resolve() == plugin_dir / "hermes_doctorpack" / "__init__.py"
        assert "hermes_doctorpack" not in sys.modules
    """)
    run_python(installed_python, tmp_path, "-c", script, ROOT)


def test_shim_without_package_context_uses_installed_wheel(installed_python, tmp_path):
    script = textwrap.dedent("""
        from pathlib import Path
        import runpy
        import sys

        shim = runpy.run_path(str(Path(sys.argv[1]) / "__init__.py"))
        assert callable(shim["register"])
        assert shim["register"].__module__ == "hermes_doctorpack"
        plugin = sys.modules["hermes_doctorpack"]
        assert Path(plugin.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    """)
    run_python(installed_python, tmp_path, "-c", script, ROOT)


@pytest.mark.parametrize("with_installed_copy", [False, True])
@pytest.mark.parametrize(
    ("broken_import", "error_type", "message", "missing_name"),
    [
        (
            'raise ImportError("synthetic internal import failure")',
            "ImportError", "synthetic internal import failure", None,
        ),
        (
            "import doctorpack_synthetic_missing_dependency",
            "ModuleNotFoundError",
            "No module named 'doctorpack_synthetic_missing_dependency'",
            "doctorpack_synthetic_missing_dependency",
        ),
    ],
)
def test_directory_preserves_internal_import_failures(
    isolated_python, installed_python, tmp_path, with_installed_copy,
    broken_import, error_type, message, missing_name,
):
    plugin_dir = tmp_path / "broken-plugin"
    plugin_dir.mkdir()
    shutil.copy2(ROOT / "__init__.py", plugin_dir / "__init__.py")
    shutil.copytree(ROOT / "hermes_doctorpack", plugin_dir / "hermes_doctorpack")
    (plugin_dir / "hermes_doctorpack" / "audit.py").write_text(broken_import, encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    script = DIRECTORY_LOADER + textwrap.dedent(f"""
        try:
            load_directory(plugin_dir)
        except Exception as exc:
            assert type(exc).__name__ == {error_type!r}, repr(exc)
            assert str(exc) == {message!r}, repr(exc)
            assert getattr(exc, "name", None) == {missing_name!r}, repr(exc)
        else:
            raise AssertionError("The internal import failure was hidden")
        assert "hermes_doctorpack" not in sys.modules
    """)
    python = installed_python if with_installed_copy else isolated_python
    run_python(python, outside, "-c", script, plugin_dir)
