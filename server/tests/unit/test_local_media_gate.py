"""S6a: the inert local-media process qualification gate (`local_media_gate.py`).

Everything here uses synthetic temp roots: a fake "native" tree, and real byte copies of the
package loaded under unique names so module eviction and re-import, plugin-class identity and
aliases are exercised for real. Nothing imports or executes Hermes, no entry exists in the shipped
manifest, and no test asserts anything about an actual native build. The autouse fixture is the
ONLY place the private `sys` key is reset (test-only; the product has no such path).
"""

from __future__ import annotations

import ast
import importlib
import importlib.machinery
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import threading
import types
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from hmp_plugin import compat as real_compat
from hmp_plugin import local_media_gate as real_gate

PACKAGE = Path(__file__).resolve().parents[2] / "hmp_plugin"
SERVER_DIR = PACKAGE.parent
GATE_SOURCE = (PACKAGE / "local_media_gate.py").read_text(encoding="utf-8")
KEY = "_hermes_hmp_local_media_process_state"
FORMAT = "hmp-local-media-1"
SECRET = "SECRET_PRIVATE_ROOT_q7"
SHA = "0123456789abcdef0123456789abcdef01234567"
COPIED = ("compat.py", "contract.py", "logging_policy.py", "local_media_gate.py")
PRELIMINARY_EXTRAS = [
    "gateway/session_context.py",
    "hermes_state_common.py",
    "hermes_state_titles.py",
    "tools/image_generation_managed.py",
    "tools/image_generation_tool.py",
    "tools/image_source.py",
]


@pytest.fixture(autouse=True)
def _isolate_anchor():
    """Test-only: start every test with no anchor and put the original back afterwards."""
    missing = object()
    old = sys.__dict__.get(KEY, missing)
    sys.__dict__.pop(KEY, None)
    try:
        yield
    finally:
        for name in [n for n in sys.modules if n.startswith("hmpgate_")]:
            del sys.modules[name]
        if old is missing:
            sys.__dict__.pop(KEY, None)
        else:
            sys.__dict__[KEY] = old


REFUSALS = (real_gate._RefusedError, OSError, ValueError)


def seed_fresh_anchor() -> tuple[Any, Any, list[Any]]:
    import _thread

    anchor = (1, _thread.allocate_lock(), [None])
    sys.__dict__[KEY] = anchor
    return anchor


def cell() -> list[Any]:
    return sys.__dict__[KEY][2]


# --------------------------------------------------------------------------------------------
# The synthetic world: a fake native tree + a copied package loaded under a unique name.
# --------------------------------------------------------------------------------------------

NATIVE_FILES = {"a.py": b"A = 1\n", "b/c.py": b"C = 2\n", "d.py": b"D = 3\n"}
READ_FILES = ["a.py", "b/c.py"]


def load_package(
    plugin: Path, name: str, *, real_probe: bool = False
) -> tuple[types.ModuleType, Any, Any]:
    spec = importlib.util.spec_from_file_location(
        name, plugin / "__init__.py", submodule_search_locations=[str(plugin)]
    )
    assert spec is not None and spec.loader is not None
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
    gate = importlib.import_module(f"{name}.local_media_gate")
    compat = importlib.import_module(f"{name}.compat")
    if not real_probe:  # no Hermes here: the dependency probe is exercised in its own tests
        compat.probe_read_dependencies = lambda **_kw: ()
    return package, gate, compat


def evict(name: str) -> None:
    """What the Hermes loader's `_evict_modules` does: the package and every submodule."""
    for key in [k for k in sys.modules if k == name or k.startswith(name + ".")]:
        del sys.modules[key]


def file_digest_oracle(root: Path, files: list[str]) -> str:
    fp = real_compat.compute_read_bridge_fingerprint(root, files)
    assert fp is not None
    return fp


class World:
    def __init__(
        self,
        tmp_path: Path,
        label: str = "w",
        like: World | None = None,
        *,
        data: dict[str, bytes] | None = None,
        listed: list[str] | None = None,
        real_probe: bool = False,
    ) -> None:
        self._real_probe = real_probe
        self._data = dict(NATIVE_FILES if data is None else data)
        self._native = sorted(self._data if listed is None else listed)
        base = tmp_path / f"{SECRET}_{label}"
        base.mkdir()
        self.base = base
        self.plugin = base / "plugin"
        self.plugin.mkdir()
        for name in COPIED:
            shutil.copy(PACKAGE / name, self.plugin / name)
        (self.plugin / "__init__.py").write_text("", encoding="utf-8")
        (self.plugin / "helper.py").write_text("HELPER = 1\n", encoding="utf-8")
        if like is None:
            self.root = (base / "native").resolve()
            for rel, data in self._data.items():
                path = self.root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            (self.root / ".git").mkdir()
            (self.root / ".git" / "HEAD").write_text(SHA + "\n", encoding="utf-8")
            self.read_list = base / "read.json"
            self.read_list.write_text(
                json.dumps({"format": 1, "bridge_files": READ_FILES, "builds": []}),
                encoding="utf-8",
            )
            self.manifest_path = base / "media.json"
        else:
            self.root = like.root
            self.read_list = like.read_list
            self.manifest_path = like.manifest_path
        self.plugin = self.plugin.resolve()
        self.pkg = f"hmpgate_{uuid.uuid4().hex[:10]}"
        self.package, self.gate, self.compat = load_package(
            self.plugin, self.pkg, real_probe=real_probe
        )
        if like is None:
            self.write_manifest()

    # --- identity oracles (independent of the gate's own digest code) ---
    def native_files(self) -> list[str]:
        return self._native

    def hmp_files(self) -> list[str]:
        return sorted(p.name for p in self.plugin.glob("*.py"))

    def native_fp(self) -> str:
        return file_digest_oracle(self.root, self.native_files())

    def read_fp(self) -> str:
        return file_digest_oracle(self.root, READ_FILES)

    def hmp_fp(self) -> str:
        return file_digest_oracle(self.plugin, self.hmp_files())

    def git(self) -> str | None:
        return real_compat.resolve_git_head_sha(self.root)

    def entry(self, **kw: Any) -> dict[str, Any]:
        out = {
            "label": "synthetic",
            "git_sha": self.git(),
            "native_fingerprint": self.native_fp(),
            "hmp_fingerprint": self.hmp_fp(),
            "source_sha": None,
            "qualified_by": "synthetic test",
            "qualified_at": "2026-10-01",
        }
        out.update(kw)
        return out

    def write_manifest(
        self,
        builds: list[dict[str, Any]] | None = None,
        *,
        native: list[str] | None = None,
        hmp: list[str] | None = None,
    ) -> None:
        doc = {
            "format": FORMAT,
            "native_files": native if native is not None else self.native_files(),
            "hmp_files": hmp if hmp is not None else self.hmp_files(),
            "builds": [self.entry()] if builds is None else builds,
        }
        self.manifest_path.write_text(json.dumps(doc), encoding="utf-8")

    def identity(self, **kw: Any) -> Any:
        values = {"fingerprint": self.read_fp(), "git_sha": self.git()}
        values.update(kw)
        return self.compat.BuildIdentity(**values)

    def modules(self) -> tuple[types.ModuleType, ...]:
        return (self.package, self.gate, self.compat)

    def factory(self, **kw: Any) -> Callable[[], bool]:
        args: dict[str, Any] = {
            "preload": self.modules,
            "hermes_root": self.root,
            "plugin_dir": self.plugin,
            "manifest_path": self.manifest_path,
            "read_compat_path": self.read_list,
        }
        identity = kw.pop("identity", None) or self.identity()
        args.update(kw)
        return self.gate.media_listener_qualifier(identity, **args)

    def reimport(self) -> None:
        evict(self.pkg)
        self.package, self.gate, self.compat = load_package(
            self.plugin, self.pkg, real_probe=self._real_probe
        )

    def edit_native(self, rel: str, data: bytes) -> None:
        (self.root / rel).write_bytes(data)

    def append_hmp(self, name: str = "helper.py", text: str = "# edit\n") -> str:
        path = self.plugin / name
        original = path.read_text(encoding="utf-8")
        path.write_text(original + text, encoding="utf-8")
        return original

    def restore_hmp(self, original: str, name: str = "helper.py") -> None:
        (self.plugin / name).write_text(original, encoding="utf-8")


@pytest.fixture
def world(tmp_path: Path) -> World:
    return World(tmp_path)


def cell_value() -> Any:
    return cell()[0]


def admitted(world: World, **kw: Any) -> Callable[[], bool]:
    callback = world.factory(**kw)
    assert callback() is True
    return callback


# --------------------------------------------------------------------------------------------
# Shipped data and pins
# --------------------------------------------------------------------------------------------


def test_shipped_manifest_is_exactly_the_empty_inventory() -> None:
    raw = json.loads((PACKAGE / "local_media_supported_builds.json").read_text(encoding="utf-8"))
    assert set(raw) == {"format", "native_files", "hmp_files", "builds"}
    assert raw["format"] == FORMAT
    assert raw["builds"] == []
    read = json.loads((PACKAGE / "read_compat_builds.json").read_text(encoding="utf-8"))
    assert len(read["bridge_files"]) == 16
    assert raw["native_files"] == sorted(set(read["bridge_files"]) | set(PRELIMINARY_EXTRAS))
    assert len(raw["native_files"]) == 22
    # Every top-level plugin source, including this gate and the reviewed batch module.
    assert raw["hmp_files"] == sorted(p.name for p in PACKAGE.glob("*.py"))
    assert {"local_media_gate.py", "local_media_active_batch.py", "adapter.py"} <= set(
        raw["hmp_files"]
    )
    parsed = real_gate.load_media_manifest(PACKAGE / "local_media_supported_builds.json")
    assert parsed.builds == ()
    assert list(parsed.native_files) == raw["native_files"]
    assert list(parsed.hmp_files) == raw["hmp_files"]


def test_wheel_ships_the_media_manifest() -> None:
    text = (SERVER_DIR / "pyproject.toml").read_text(encoding="utf-8")
    assert '"local_media_supported_builds.json"' in text


def test_manifest_limits_are_the_frozen_constants() -> None:
    g = real_gate
    assert (g.MAX_MANIFEST_BYTES, g.MAX_NATIVE_PATHS, g.MAX_HMP_PATHS, g.MAX_BUILDS) == (
        256 * 1024,
        256,
        256,
        128,
    )
    assert (g.MAX_TEXT_CHARS, g.MAX_PATH_BYTES, g.MAX_DIR_ENTRIES) == (256, 1024, 512)
    assert (g.MAX_FILE_BYTES, g.MAX_TOTAL_BYTES) == (8 * 1024 * 1024, 64 * 1024 * 1024)
    assert g.ANCHOR_KEY == KEY and g.MEDIA_MANIFEST_FORMAT == FORMAT


def test_media_dependencies_extend_read_dependencies_with_verified_title_and_lineage() -> None:
    read = real_compat.READ_DEPENDENCIES
    media = real_gate.MEDIA_DEPENDENCIES
    assert media[: len(read)] == read
    extra = media[len(read) :]
    assert [(s.module, s.qualname) for s in extra] == [
        ("hermes_state", "SessionDB.get_session_by_title"),
        ("hermes_state", "SessionDB.get_compression_lineage"),
    ]
    assert len(set(media)) == len(media)
    # No approval, direct-send or write dependency leaks into the media probe table.
    assert not [s for s in media if s.module.startswith(("tools.approval", "tools.clarify"))]
    # Defining files of the two additions are in the preliminary native inventory.
    native = json.loads((PACKAGE / "local_media_supported_builds.json").read_text())["native_files"]
    assert "hermes_state_titles.py" in native and "hermes_state_compression.py" in native


def test_media_dependencies_cover_every_bridge_db_method_and_the_runner_reach() -> None:
    from hmp_plugin import bridge

    qualnames = {s.qualname for s in real_gate.MEDIA_DEPENDENCIES if s.qualname}
    for method in bridge.REACHED_METHODS["db"]:
        assert f"SessionDB.{method}" in qualnames, method
    for method in bridge.REACHED_METHODS["runner"]:
        assert any(q.endswith(f".{method}") for q in qualnames), method
    for method in bridge.REACHED_METHODS["adapter"]:
        assert any(q.endswith(f".{method}") for q in qualnames), method
    assert "SessionStore.lookup_by_session_key" in qualnames
    assert "_profile_runtime_scope" in qualnames


def test_gate_import_surface_is_compat_and_stdlib_only() -> None:
    allowed_abs = {
        "_thread",
        "contextlib",
        "hashlib",
        "importlib.machinery",
        "json",
        "os",
        "re",
        "stat",
        "sys",
        "collections.abc",
        "dataclasses",
        "pathlib",
        "types",
        "typing",
        "__future__",
    }
    tree = ast.parse(GATE_SOURCE)
    seen_abs: set[str] = set()
    seen_rel: list[tuple[str | None, list[str]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            seen_abs.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                seen_rel.append((node.module, [a.name for a in node.names]))
            else:
                seen_abs.add(node.module or "")
    assert seen_abs <= allowed_abs
    assert seen_rel == [(None, ["compat"])]
    dynamic = {"__import__", "import_module", "find_spec"}
    builtins_exec = {"exec", "eval", "compile"}  # `re.compile` is an attribute, not the builtin
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                assert func.id not in dynamic | builtins_exec
            else:
                assert getattr(func, "attr", "") not in dynamic
    # Module level imports only; none of the lanes it must stay independent of is named.
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {
        n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)
    }
    for word in (
        "approval_listener_qualifier",
        "direct_send_build_qualified",
        "logging",
        "log_event",
    ):
        assert word not in names
    assert "logging" not in seen_abs


def test_gate_source_has_no_reset_delete_or_second_write_path() -> None:
    tree = ast.parse(GATE_SOURCE)
    set_defaults = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "setdefault"
    ]
    assert len(set_defaults) == 1
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Delete)]
    mutators = {"pop", "popitem", "clear", "update", "remove", "__setitem__", "__delitem__"}
    assert not [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and getattr(n.func, "attr", "") in mutators
        and any(w in ast.unparse(n.func.value) for w in ("__dict__", "cell", "anchor", "lock"))
    ]
    stores = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Subscript)
        and isinstance(n.ctx, (ast.Store, ast.Del))
        and ("cell" in ast.unparse(n.value) or "__dict__" in ast.unparse(n.value))
    ]
    assert len(stores) == 1  # `cell[0] = new`, inside `_first_transition` only
    transition = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_first_transition"
    )
    assert any(s is st for s in ast.walk(transition) for st in stores)
    public = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    assert not [n for n in public if "reset" in n.lower() or n.startswith("set_")]
    # The only top-level statement that touches the anchor is the guarded setdefault.
    top_level_calls = [
        n
        for stmt in tree.body
        if isinstance(stmt, ast.If)
        for n in ast.walk(stmt)
        if isinstance(n, ast.Call)
    ]
    assert any(getattr(n.func, "attr", "") == "setdefault" for n in top_level_calls)


def test_import_has_no_filesystem_or_native_effect_and_only_creates_the_anchor() -> None:
    code = (
        "import sys, json\n"
        "import hmp_plugin.compat\n"
        "sys.__dict__.pop('_hermes_hmp_local_media_process_state', None)\n"
        "events = []\n"
        "def hook(event, args):\n"
        "    if event in ('open', 'os.listdir', 'os.scandir', 'os.mkdir', 'os.remove',\n"
        "                 'os.rename', 'subprocess.Popen', 'os.system', 'socket.connect'):\n"
        "        path = str(args[0]) if args else ''\n"
        "        if not (event == 'open' and 'local_media_gate' in path):\n"
        "            events.append([event, path])\n"
        "sys.addaudithook(hook)\n"
        "known = set(sys.modules)\n"
        "import hmp_plugin.local_media_gate as g\n"
        "anchor = sys.__dict__[g.ANCHOR_KEY]\n"
        "print(json.dumps({'events': events, 'shape': [type(anchor).__name__, len(anchor),\n"
        "    anchor[0], type(anchor[2]).__name__, anchor[2]],\n"
        "    'bad': sorted(set(sys.modules) - known - {'hmp_plugin.local_media_gate'})}))\n"
    )
    env = {**os.environ, "PYTHONPATH": str(SERVER_DIR)}
    done = subprocess.run(
        [sys.executable, "-B", "-c", code], env=env, capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr[-500:]
    out = json.loads(done.stdout.strip().splitlines()[-1])
    assert out["events"] == []
    assert out["shape"] == ["tuple", 3, 1, "list", [None]]
    assert out["bad"] == []


# --------------------------------------------------------------------------------------------
# Strict manifest parser
# --------------------------------------------------------------------------------------------


def good_entry(**kw: Any) -> dict[str, Any]:
    out: dict[str, Any] = {
        "label": "synthetic",
        "git_sha": None,
        "native_fingerprint": "a" * 64,
        "hmp_fingerprint": "b" * 64,
        "source_sha": None,
        "qualified_by": "synthetic",
        "qualified_at": "2026-10-01",
    }
    out.update(kw)
    return out


def good_doc(**kw: Any) -> dict[str, Any]:
    out: dict[str, Any] = {
        "format": FORMAT,
        "native_files": ["a.py", "b/c.py"],
        "hmp_files": ["x.py", "y.py"],
        "builds": [good_entry()],
    }
    out.update(kw)
    return out


def parse(doc: Any) -> Any:
    return real_gate.parse_media_manifest(json.dumps(doc).encode("utf-8"))


def test_parser_accepts_the_exact_shape_with_explicit_nulls_and_hex() -> None:
    parsed = parse(
        good_doc(builds=[good_entry(git_sha=SHA, source_sha=SHA), good_entry(label="two")])
    )
    assert parsed.native_files == ("a.py", "b/c.py") and parsed.hmp_files == ("x.py", "y.py")
    assert parsed.builds[0].git_sha == SHA and parsed.builds[1].git_sha is None
    assert parse(good_doc(builds=[])).builds == ()
    assert parse(good_doc(builds=[], native_files=[], hmp_files=[])).native_files == ()


BAD_PATHS = [
    "/abs.py",
    "../up.py",
    "a/../b.py",
    "./a.py",
    "a//b.py",
    "a/",
    "",
    "a\\b.py",
    "a\0b.py",
    "a\nb.py",
    "a\x7fb.py",
    "é\ud800.py",
    "x" * 1021 + ".py",  # 1024 bytes is allowed below, 1025 is not
    5,
    None,
]


@pytest.mark.parametrize("path", BAD_PATHS, ids=[repr(p)[:24] for p in BAD_PATHS])
def test_parser_refuses_unsafe_native_paths(path: Any) -> None:
    if isinstance(path, str) and len(path) == 1024:
        parse(good_doc(native_files=[path]))  # exactly at the bound is fine
        path = path + "x"
    with pytest.raises(ValueError):
        parse(good_doc(native_files=[path]))


@pytest.mark.parametrize("path", ["sub/x.py", "x.txt", "x.pyc", ".py", "../x.py", "/x.py"])
def test_parser_refuses_non_top_level_python_hmp_paths(path: str) -> None:
    with pytest.raises(ValueError):
        parse(good_doc(hmp_files=[path]))


def test_parser_refuses_unsorted_duplicate_and_oversized_lists() -> None:
    for bad in (["b.py", "a.py"], ["a.py", "a.py"]):
        with pytest.raises(ValueError):
            parse(good_doc(native_files=bad))
        with pytest.raises(ValueError):
            parse(good_doc(hmp_files=bad))
    parse(good_doc(native_files=[f"n{i:04d}.py" for i in range(256)]))
    with pytest.raises(ValueError):
        parse(good_doc(native_files=[f"n{i:04d}.py" for i in range(257)]))
    parse(good_doc(hmp_files=[f"h{i:04d}.py" for i in range(256)]))
    with pytest.raises(ValueError):
        parse(good_doc(hmp_files=[f"h{i:04d}.py" for i in range(257)]))
    parse(good_doc(builds=[good_entry(label=f"l{i}") for i in range(128)]))
    with pytest.raises(ValueError):
        parse(good_doc(builds=[good_entry(label=f"l{i}") for i in range(129)]))
    with pytest.raises(ValueError):
        parse(good_doc(native_files=[]))  # entries need a native list
    with pytest.raises(ValueError):
        parse(good_doc(hmp_files=[]))
    with pytest.raises(ValueError):
        parse(good_doc(native_files="a.py"))


def test_parser_refuses_top_level_shape_faults() -> None:
    base = good_doc()
    for bad in (
        [],
        "x",
        None,
        {**base, "extra": 1},
        {k: v for k, v in base.items() if k != "builds"},
        {k: v for k, v in base.items() if k != "hmp_files"},
        {**base, "format": 1},
        {**base, "format": "hmp-local-media-2"},
        {**base, "format": ["hmp-local-media-1"]},
        {**base, "builds": {}},
        {**base, "builds": ["x"]},
    ):
        with pytest.raises(ValueError):
            parse(bad)


ENTRY_FAULTS = [
    {"extra": 1},
    {"label": ""},
    {"label": "x" * 257},
    {"label": "a\nb"},
    {"label": "a\ud800"},
    {"label": 1},
    {"label": True},
    {"label": None},
    {"qualified_by": ""},
    {"qualified_by": "x" * 257},
    {"qualified_at": 20261001},
    {"git_sha": ""},
    {"git_sha": "A" * 40},
    {"git_sha": "a" * 39},
    {"git_sha": 1},
    {"source_sha": "g" * 40},
    {"source_sha": True},
    {"native_fingerprint": "A" * 64},
    {"native_fingerprint": "a" * 63},
    {"native_fingerprint": None},
    {"hmp_fingerprint": "b" * 65},
    {"hmp_fingerprint": None},
    {"hmp_fingerprint": 0},
]


@pytest.mark.parametrize("fault", ENTRY_FAULTS, ids=[str(f)[:30] for f in ENTRY_FAULTS])
def test_parser_refuses_entry_faults(fault: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        parse(good_doc(builds=[good_entry(**fault)]))


@pytest.mark.parametrize("missing", sorted(good_entry()))
def test_parser_requires_every_entry_key_explicitly(missing: str) -> None:
    entry = good_entry()
    del entry[missing]  # an absent optional SHA is not the explicit null the format needs
    with pytest.raises(ValueError):
        parse(good_doc(builds=[entry]))


def test_text_at_the_bound_is_accepted() -> None:
    parsed = parse(good_doc(builds=[good_entry(label="x" * 256, qualified_by="é" * 256)]))
    assert len(parsed.builds[0].label) == 256


@pytest.mark.parametrize(
    "raw",
    [
        b'{"format":"hmp-local-media-1","format":"hmp-local-media-1","native_files":[],'
        b'"hmp_files":[],"builds":[]}',
        b'{"format":"hmp-local-media-1","native_files":[],"hmp_files":[],"builds":[],"builds":[]}',
        b'{"format":"hmp-local-media-1","native_files":[],"hmp_files":[],"builds":[NaN]}',
        b'{"format":"hmp-local-media-1","native_files":[],"hmp_files":[],"builds":[Infinity]}',
        b"\xff\xfe",
        b"",
        b"[",
        b"\xef\xbb\xbf" + json.dumps(good_doc()).encode(),
    ],
)
def test_parser_refuses_duplicate_keys_non_finite_and_undecodable_bytes(raw: bytes) -> None:
    with pytest.raises(ValueError):
        real_gate.parse_media_manifest(raw)


def test_duplicate_key_inside_an_entry_is_refused() -> None:
    entry = (
        json.dumps(good_entry())
        .encode()
        .replace(b'"label": "synthetic"', b'"label": "a", "label": "b"')
    )
    raw = (
        b'{"format":"hmp-local-media-1","native_files":["a.py"],"hmp_files":["x.py"],"builds":['
        + entry
        + b"]}"
    )
    with pytest.raises(ValueError):
        real_gate.parse_media_manifest(raw)


def test_manifest_size_cap_applies_to_parse_and_to_the_file_read(tmp_path: Path) -> None:
    body = json.dumps(good_doc(builds=[])).encode()
    padded = body + b" " * (256 * 1024 - len(body))
    assert real_gate.parse_media_manifest(padded).builds == ()
    with pytest.raises(ValueError):
        real_gate.parse_media_manifest(padded + b" ")
    path = tmp_path / "m.json"
    path.write_bytes(padded)
    assert real_gate.load_media_manifest(path).builds == ()
    path.write_bytes(padded + b" ")
    with pytest.raises(REFUSALS):  # refused by the bounded read, before parsing
        real_gate.load_media_manifest(path)


def test_manifest_read_is_no_follow_bounded_and_not_the_unbounded_compat_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = tmp_path / "real.json"
    real.write_text(json.dumps(good_doc(builds=[])), encoding="utf-8")
    link = tmp_path / "link.json"
    link.symlink_to(real)
    with pytest.raises(OSError):
        real_gate.load_media_manifest(link)
    linked_dir = tmp_path / "ld"
    linked_dir.symlink_to(tmp_path)
    # A symlinked PARENT is resolved once (like a root); the leaf is what must not be a link.
    assert real_gate.load_media_manifest(linked_dir / "real.json").builds == ()
    monkeypatch.setattr(
        real_compat,
        "load_read_compat_list",
        lambda *_a, **_k: pytest.fail("the unbounded compat reader must not be used"),
    )
    assert real_gate.load_media_manifest(real).builds == ()
    used = {n.attr for n in ast.walk(ast.parse(GATE_SOURCE)) if isinstance(n, ast.Attribute)}
    assert "load_read_compat_list" not in used


def test_read_and_media_parsers_reject_each_others_files(tmp_path: Path) -> None:
    media = PACKAGE / "local_media_supported_builds.json"
    with pytest.raises(ValueError):
        real_compat.load_read_compat_list(media)  # format is a string, not 1
    read = PACKAGE / "read_compat_builds.json"
    with pytest.raises(ValueError):
        real_gate.parse_media_manifest(read.read_bytes())
    approval = PACKAGE / "approval_supported_builds.json"
    with pytest.raises(ValueError):
        real_gate.parse_media_manifest(approval.read_bytes())


def test_read_list_extraction_is_bounded_strict_and_format_one(tmp_path: Path) -> None:
    path = tmp_path / "read.json"
    good = {"format": 1, "bridge_files": ["a.py", "b/c.py"], "builds": "ignored"}
    path.write_text(json.dumps(good), encoding="utf-8")
    assert real_gate._load_read_files(path) == ("a.py", "b/c.py")
    for bad in (
        {**good, "format": True},
        {**good, "format": 2},
        {**good, "bridge_files": []},
        {**good, "bridge_files": ["b.py", "a.py"]},
        {**good, "bridge_files": ["/abs.py"]},
        {**good, "bridge_files": ["a.py", "a.py"]},
        {"bridge_files": ["a.py"]},
        [],
    ):
        path.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(ValueError):
            real_gate._load_read_files(path)
    path.write_bytes(b" " * (256 * 1024 + 1))
    with pytest.raises(REFUSALS):
        real_gate._load_read_files(path)
    # The real shipped read list extracts to the same 16 files the compat parser sees.
    shipped = PACKAGE / "read_compat_builds.json"
    assert (
        real_gate._load_read_files(shipped)
        == real_compat.load_read_compat_list(shipped).bridge_files
    )


def test_match_uses_both_fingerprints_and_git_semantics_and_ignores_source_sha() -> None:
    g = real_gate
    e = g.MediaBuildEntry("l", SHA, "a" * 64, "b" * 64, "c" * 40, "q", "t")
    nogit = g.MediaBuildEntry("l", None, "a" * 64, "b" * 64, None, "q", "t")

    def m(entry: Any, **kw: Any) -> Any:
        args = {"git_sha": SHA, "native_fingerprint": "a" * 64, "hmp_fingerprint": "b" * 64}
        args.update(kw)
        return g.match_media_build([entry], **args)

    assert m(e) is e and m(nogit, git_sha=None) is nogit
    assert m(e, git_sha=None) is None and m(nogit) is None  # git/no-git never cross
    assert m(e, git_sha="d" * 40) is None
    assert m(e, native_fingerprint="d" * 64) is None
    assert m(e, hmp_fingerprint="d" * 64) is None
    assert (
        g.match_media_build([], git_sha=None, native_fingerprint="a", hmp_fingerprint="b") is None
    )


# --------------------------------------------------------------------------------------------
# Bounded fd-relative reader and the shared pure digest
# --------------------------------------------------------------------------------------------


def read_set(root: Path, rels: list[str]) -> dict[str, bytes]:
    return real_gate._read_set(root, rels, real_gate._Budget())


def test_digest_equals_compat_read_fingerprint_for_regular_files(tmp_path: Path) -> None:
    files = {"z.py": b"zz", "a/b.py": b"\x00\xff" * 100, "m.py": b""}
    for rel, data in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_bytes(data)
    got = read_set(tmp_path, list(files))
    assert got == files
    expected = real_compat.compute_read_bridge_fingerprint(tmp_path, ["m.py", "z.py", "a/b.py"])
    assert real_gate.fingerprint_pairs(got) == expected
    assert real_gate.fingerprint_pairs({}) == real_compat.compute_read_bridge_fingerprint(
        tmp_path, []
    )


def refused(root: Path, rels: list[str]) -> None:
    with pytest.raises(REFUSALS):
        read_set(root, rels)


def test_reader_refuses_symlink_leaf_intermediate_missing_and_traversal(tmp_path: Path) -> None:
    (tmp_path / "real.py").write_text("x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "f.py").write_text("y")
    (tmp_path / "leaf.py").symlink_to(tmp_path / "real.py")
    (tmp_path / "linkdir").symlink_to(tmp_path / "sub")
    for rel in ("leaf.py", "linkdir/f.py", "missing.py", "sub/missing.py", "../real.py", "/x.py"):
        refused(tmp_path, [rel])
    assert read_set(tmp_path, ["real.py", "sub/f.py"]) == {"real.py": b"x", "sub/f.py": b"y"}


def test_reader_refuses_fifo_without_hanging(tmp_path: Path) -> None:
    os.mkfifo(tmp_path / "pipe.py")
    box: list[Any] = []

    def run() -> None:
        try:
            read_set(tmp_path, ["pipe.py"])
        except Exception as exc:
            box.append(exc)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(5)
    assert not worker.is_alive(), "FIFO leaf hung the reader"
    assert box, "FIFO leaf was accepted"


def test_reader_refuses_device_and_directory_leaves(tmp_path: Path) -> None:
    assert stat.S_ISCHR(os.stat("/dev/null").st_mode)
    refused(Path("/dev"), ["null"])
    (tmp_path / "dir.py").mkdir()
    refused(tmp_path, ["dir.py"])
    refused(tmp_path, ["dir.py/x.py"])


def test_reader_refuses_a_file_root_and_a_missing_root(tmp_path: Path) -> None:
    (tmp_path / "f").write_text("x")
    refused(tmp_path / "f", ["x.py"])
    refused(tmp_path / "nope", ["x.py"])


def test_oversize_file_is_refused_before_any_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "big.py").write_bytes(b"x" * 11)
    (tmp_path / "ok.py").write_bytes(b"x" * 10)
    monkeypatch.setattr(real_gate, "MAX_FILE_BYTES", 10)
    monkeypatch.setattr(
        real_gate, "_read_fd", lambda *_a: pytest.fail("read attempted for an oversize file")
    )
    refused(tmp_path, ["big.py"])
    monkeypatch.undo()
    monkeypatch.setattr(real_gate, "MAX_FILE_BYTES", 10)
    assert read_set(tmp_path, ["ok.py"]) == {"ok.py": b"x" * 10}


def test_aggregate_cap_is_charged_before_reading_across_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("a.py", "b.py", "c.py"):
        (tmp_path / name).write_bytes(b"x" * 10)
    monkeypatch.setattr(real_gate, "MAX_TOTAL_BYTES", 30)
    assert len(read_set(tmp_path, ["a.py", "b.py", "c.py"])) == 3
    monkeypatch.setattr(real_gate, "MAX_TOTAL_BYTES", 29)
    calls: list[int] = []
    original = real_gate._read_fd
    monkeypatch.setattr(real_gate, "_read_fd", lambda fd, n: calls.append(n) or original(fd, n))
    refused(tmp_path, ["a.py", "b.py", "c.py"])
    assert len(calls) == 4  # two files read (data + EOF); the third was refused before any read


def test_short_growing_and_changing_files_are_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "f.py"
    path.write_bytes(b"0123456789")
    original = real_gate._read_fd

    monkeypatch.setattr(real_gate, "_read_fd", lambda fd, n: b"")  # truncated underneath us
    refused(tmp_path, ["f.py"])
    monkeypatch.setattr(real_gate, "_read_fd", lambda fd, n: original(fd, n - 3))
    refused(tmp_path, ["f.py"])  # short: a read that stops early and then reports EOF

    def grow(fd: int, n: int) -> bytes:
        with open(path, "ab") as handle:
            handle.write(b"more")
        return original(fd, n)

    monkeypatch.setattr(real_gate, "_read_fd", grow)
    refused(tmp_path, ["f.py"])
    path.write_bytes(b"0123456789")

    def touch(fd: int, n: int) -> bytes:
        data = original(fd, n)
        os.utime(path, ns=(1_000_000_000, 1_000_000_000))  # same size, different mtime/ctime
        return data

    monkeypatch.setattr(real_gate, "_read_fd", touch)
    refused(tmp_path, ["f.py"])

    monkeypatch.setattr(real_gate, "_read_fd", lambda fd, n: "not bytes")
    refused(tmp_path, ["f.py"])
    monkeypatch.setattr(real_gate, "_read_fd", original)
    assert read_set(tmp_path, ["f.py"]) == {"f.py": b"0123456789"}


def open_fds() -> int:
    return len(os.listdir("/dev/fd"))


def test_every_descriptor_is_closed_on_success_and_on_every_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "ok.py").write_bytes(b"ok")
    (tmp_path / "grow.py").write_bytes(b"1234")
    os.mkfifo(tmp_path / "pipe.py")
    (tmp_path / "dir.py").mkdir()
    before = open_fds()
    assert read_set(tmp_path, ["sub/ok.py"])
    for rel in ("pipe.py", "dir.py", "missing.py", "sub/missing.py", "sub/ok.py/x"):
        refused(tmp_path, [rel])
    original = real_gate._read_fd

    def grow(fd: int, n: int) -> bytes:
        (tmp_path / "grow.py").write_bytes(b"123456")
        return original(fd, n)

    monkeypatch.setattr(real_gate, "_read_fd", grow)
    refused(tmp_path, ["grow.py"])
    monkeypatch.setattr(real_gate, "_read_fd", original)
    monkeypatch.setattr(real_gate, "MAX_FILE_BYTES", 1)
    refused(tmp_path, ["sub/ok.py"])
    assert open_fds() == before


def test_a_missing_no_follow_primitive_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "f.py").write_text("x")
    monkeypatch.delattr(os, "O_NOFOLLOW")
    refused(tmp_path, ["f.py"])


# --------------------------------------------------------------------------------------------
# Plugin directory-set equality (importable forms)
# --------------------------------------------------------------------------------------------


def plugin_read(root: Path, rels: list[str]) -> Any:
    return real_gate._read_set(root, rels, real_gate._Budget(), plugin_listing=True)


@pytest.fixture
def plugin_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "pl"
    directory.mkdir()
    (directory / "a.py").write_text("A\n")
    (directory / "b.py").write_text("B\n")
    return directory


def test_plugin_dir_accepts_exact_listing_and_non_importable_extras(plugin_dir: Path) -> None:
    assert set(plugin_read(plugin_dir, ["a.py", "b.py"])) == {"a.py", "b.py"}
    for extra in ("plugin.yaml", "notes.txt", "x.json", "README", "data.pyi.txt", ".DS_Store"):
        (plugin_dir / extra).write_text("x")
    cache = plugin_dir / "__pycache__"
    cache.mkdir()
    (cache / "a.cpython-314.pyc").write_bytes(b"\x00")
    assert set(plugin_read(plugin_dir, ["a.py", "b.py"])) == {"a.py", "b.py"}


@pytest.mark.parametrize("suffix", importlib.machinery.all_suffixes())
def test_every_importable_suffix_shadow_is_refused(plugin_dir: Path, suffix: str) -> None:
    (plugin_dir / f"adapter{suffix}").write_bytes(b"")
    with pytest.raises(REFUSALS):
        plugin_read(plugin_dir, ["a.py", "b.py"])


@pytest.mark.parametrize(
    "name",
    ["adapter.cpython-314-darwin.so", "adapter.abi3.so", "adapter.so", "foo.pyc", "extra.py"],
)
def test_named_shadow_forms_are_refused(plugin_dir: Path, name: str) -> None:
    (plugin_dir / name).write_bytes(b"")
    with pytest.raises(REFUSALS):
        plugin_read(plugin_dir, ["a.py", "b.py"])


def test_extra_subdirectory_symlink_and_fifo_are_refused(plugin_dir: Path, tmp_path: Path) -> None:
    for build in (
        lambda p: (p.mkdir(), (p / "__init__.py").write_text("")),
        lambda p: p.symlink_to(plugin_dir / "a.py"),
        lambda p: p.symlink_to(plugin_dir),
        lambda p: os.mkfifo(p),
    ):
        target = plugin_dir / "extra_thing"
        build(target)
        with pytest.raises(REFUSALS):
            plugin_read(plugin_dir, ["a.py", "b.py"])
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()
    assert plugin_read(plugin_dir, ["a.py", "b.py"])


def test_pycache_must_be_a_real_directory_of_regular_files(
    plugin_dir: Path, tmp_path: Path
) -> None:
    cache = plugin_dir / "__pycache__"
    cache.symlink_to(tmp_path)  # a link to a directory: refused without following
    with pytest.raises(REFUSALS):
        plugin_read(plugin_dir, ["a.py", "b.py"])
    cache.unlink()
    cache.write_text("not a directory")
    with pytest.raises(REFUSALS):
        plugin_read(plugin_dir, ["a.py", "b.py"])
    cache.unlink()
    cache.mkdir()
    for build in (
        lambda p: (p.mkdir(), (p / "n.pyc").write_bytes(b"")),
        lambda p: p.symlink_to(plugin_dir / "a.py"),
        lambda p: os.mkfifo(p),
    ):
        target = cache / "bad"
        build(target)
        with pytest.raises(REFUSALS):
            plugin_read(plugin_dir, ["a.py", "b.py"])
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()
    assert plugin_read(plugin_dir, ["a.py", "b.py"])


def test_directory_listing_is_bounded_at_512_entries(plugin_dir: Path) -> None:
    for i in range(510):
        (plugin_dir / f"n{i}.txt").write_text("")
    assert plugin_read(plugin_dir, ["a.py", "b.py"])  # 512 entries exactly
    (plugin_dir / "one_more.txt").write_text("")
    with pytest.raises(REFUSALS):
        plugin_read(plugin_dir, ["a.py", "b.py"])
    for i in range(510):
        (plugin_dir / f"n{i}.txt").unlink()
    (plugin_dir / "one_more.txt").unlink()
    cache = plugin_dir / "__pycache__"
    cache.mkdir()
    for i in range(513):
        (cache / f"c{i}.pyc").write_bytes(b"")
    with pytest.raises(REFUSALS):
        plugin_read(plugin_dir, ["a.py", "b.py"])


def test_a_missing_listed_plugin_file_is_refused(plugin_dir: Path) -> None:
    with pytest.raises(REFUSALS):
        plugin_read(plugin_dir, ["a.py", "b.py", "gone.py"])


# --------------------------------------------------------------------------------------------
# Anchor creation, layout and foreign anchors
# --------------------------------------------------------------------------------------------


def test_import_creates_the_exact_anchor_once_and_copies_share_it(tmp_path: Path) -> None:
    first = World(tmp_path, "one")
    anchor = sys.__dict__[KEY]
    import _thread

    assert type(anchor) is tuple and len(anchor) == 3
    assert type(anchor[0]) is int and anchor[0] == 1
    assert type(anchor[1]) is _thread.LockType
    assert type(anchor[2]) is list and anchor[2] == [None]
    second = World(tmp_path, "two", like=first)
    reimported = World(tmp_path, "three", like=first)
    assert sys.__dict__[KEY] is anchor  # setdefault never replaces
    assert first.gate is not second.gate is not reimported.gate


def test_baseline_layout_is_primitive_exact_and_holds_no_plugin_object(world: World) -> None:
    admitted(world)
    value = cell_value()
    assert type(value) is tuple and len(value) == 10
    tag, root, plugin, read_files, read_fp, native_files, native_fp, git, hmp_files, hmp_fp = value
    assert tag == "b1" and type(tag) is str
    assert root == str(world.root) and plugin == str(world.plugin)
    assert read_files == tuple(READ_FILES) and native_files == tuple(world.native_files())
    assert hmp_files == tuple(world.hmp_files())
    assert (read_fp, native_fp, hmp_fp) == (world.read_fp(), world.native_fp(), world.hmp_fp())
    assert git == SHA

    def walk(item: Any) -> None:
        if type(item) is tuple:
            for part in item:
                walk(part)
        else:
            assert type(item) in (str, type(None))

    walk(value)  # no Path, class, callable, module, label or receipt data anywhere


def test_closed_cell_is_the_exact_string_and_stays_through_later_changes(world: World) -> None:
    world.write_manifest(builds=[])
    assert world.factory()() is False
    assert cell_value() == "closed" and type(cell_value()) is str


FOREIGN = {
    "schema_2": lambda lock: (2, lock, [None]),
    "schema_true": lambda lock: (True, lock, [None]),
    "list_not_tuple": lambda lock: [1, lock, [None]],
    "length_4": lambda lock: (1, lock, [None], 0),
    "length_2": lambda lock: (1, lock),
    "rlock": lambda lock: (1, __import__("threading").RLock(), [None]),
    "no_lock": lambda lock: (1, object(), [None]),
    "cell_tuple": lambda lock: (1, lock, (None,)),
    "cell_len_2": lambda lock: (1, lock, [None, None]),
    "cell_empty": lambda lock: (1, lock, []),
    "closed_space": lambda lock: (1, lock, ["closed "]),
    "closed_upper": lambda lock: (1, lock, ["Closed"]),
    "baseline_short": lambda lock: (1, lock, [("b1", "r", "p")]),
    "baseline_bad_hex": lambda lock: (
        1,
        lock,
        [("b1", "/r", "/p", ("a.py",), "x" * 64, ("a.py",), "a" * 64, None, ("x.py",), "b" * 64)],
    ),
    "baseline_list_files": lambda lock: (
        1,
        lock,
        [("b1", "/r", "/p", ["a.py"], "a" * 64, ("a.py",), "a" * 64, None, ("x.py",), "b" * 64)],
    ),
    "baseline_tag": lambda lock: (
        1,
        lock,
        [("b2", "/r", "/p", ("a.py",), "a" * 64, ("a.py",), "a" * 64, None, ("x.py",), "b" * 64)],
    ),
    "baseline_unsorted": lambda lock: (
        1,
        lock,
        [
            (
                "b1",
                "/r",
                "/p",
                ("b.py", "a.py"),
                "a" * 64,
                ("a.py", "b.py"),
                "a" * 64,
                None,
                ("x.py",),
                "b" * 64,
            )
        ],
    ),
    "baseline_read_not_subset": lambda lock: (
        1,
        lock,
        [("b1", "/r", "/p", ("z.py",), "a" * 64, ("a.py",), "a" * 64, None, ("x.py",), "b" * 64)],
    ),
    "baseline_path_obj": lambda lock: (
        1,
        lock,
        [
            (
                "b1",
                Path("/r"),
                "/p",
                ("a.py",),
                "a" * 64,
                ("a.py",),
                "a" * 64,
                None,
                ("x.py",),
                "b" * 64,
            )
        ],
    ),
    "cell_int": lambda lock: (1, lock, [0]),
    "cell_false": lambda lock: (1, lock, [False]),
    "cell_dict": lambda lock: (1, lock, [{}]),
    "not_a_tuple": lambda lock: "anchor",
}


@pytest.mark.parametrize("name", sorted(FOREIGN))
def test_foreign_or_malformed_anchor_is_never_repaired_or_overwritten(
    tmp_path: Path, name: str
) -> None:
    import _thread

    foreign = FOREIGN[name](_thread.allocate_lock())
    snapshot = repr(foreign)
    sys.__dict__[KEY] = foreign
    w = World(tmp_path)  # a fresh import runs `setdefault` against the foreign value
    assert sys.__dict__[KEY] is foreign
    calls: list[str] = []
    callback = w.factory(preload=lambda: calls.append("preload") or w.modules())
    assert callback is w.gate._closed and callback() is False
    assert sys.__dict__[KEY] is foreign and repr(foreign) == snapshot
    assert calls == []  # no source work, no preload for an unusable anchor


def test_foreign_cell_content_changes_after_admission_close_the_listener(world: World) -> None:
    callback = admitted(world)
    good = cell_value()
    for forged in (
        "closed ",
        ("b1", *good[1:9], "c" * 64),
        good[:9],
        list(good),
        world.gate.MediaProcessBaseline(*good[1:]),  # a plugin-class instance, never valid
        42,
    ):
        cell()[0] = forged
        assert callback() is False
        assert cell_value() is forged  # untouched, not repaired
        assert world.factory() is world.gate._closed
        assert cell_value() is forged
    cell()[0] = good
    assert callback() is True


def test_anchor_removed_or_replaced_closes_without_recreation(world: World) -> None:
    callback = admitted(world)
    saved = sys.__dict__.pop(KEY)
    assert callback() is False
    assert KEY not in sys.__dict__  # nothing recreated it
    assert world.factory() is world.gate._closed
    assert KEY not in sys.__dict__
    sys.__dict__[KEY] = saved
    assert callback() is True


# --------------------------------------------------------------------------------------------
# Unknown identity, empty manifest, free-threaded
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [None, object(), "x" * 64, (("a" * 64), None)])
def test_unknown_read_identity_closes_with_no_anchor_initialization(world: World, bad: Any) -> None:
    seed = cell_value()
    assert seed is None
    calls: list[str] = []
    callback = world.gate.media_listener_qualifier(
        bad,
        preload=lambda: calls.append("p") or world.modules(),
        hermes_root=world.root,
        plugin_dir=world.plugin,
        manifest_path=world.manifest_path,
        read_compat_path=world.read_list,
    )
    assert callback is world.gate._closed and callback() is False
    assert cell_value() is None and calls == []
    # A real identity later still captures: the earlier unknown read did not latch anything.
    assert world.factory()() is True


def test_identity_lookalike_from_another_class_is_not_a_build_identity(world: World) -> None:
    other = real_compat.BuildIdentity(world.read_fp(), world.git())  # a different compat copy
    callback = world.gate.media_listener_qualifier(
        other,
        preload=world.modules,
        hermes_root=world.root,
        plugin_dir=world.plugin,
        manifest_path=world.manifest_path,
        read_compat_path=world.read_list,
    )
    assert callback is world.gate._closed and cell_value() is None


def trap(world: World, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Any source location, read, git resolution, probe or preload is recorded."""
    calls: list[str] = []
    gate, compat = world.gate, world.compat
    for obj, name in (
        (gate, "_read_set"),
        (gate, "_measure"),
        (gate, "_load_read_files"),
        (gate, "_resolve_root"),
        (gate, "_resolve_plugin_dir"),
        (compat, "locate_hermes_root"),
        (compat, "resolve_git_head_sha"),
        (compat, "probe_read_dependencies"),
        (compat, "compute_read_bridge_fingerprint"),
    ):
        monkeypatch.setattr(
            obj, name, lambda *_a, _n=name, **_k: calls.append(_n) or pytest.fail(_n)
        )
    return calls


def test_empty_manifest_latches_closed_before_locating_or_reading_anything(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    world.write_manifest(builds=[])
    calls = trap(world, monkeypatch)
    reads: list[Path] = []
    original = world.gate._read_one
    monkeypatch.setattr(
        world.gate, "_read_one", lambda p, cap: reads.append(Path(p)) or original(p, cap)
    )
    preloaded: list[int] = []
    callback = world.factory(preload=lambda: preloaded.append(1) or world.modules())
    assert callback is world.gate._closed and callback() is False
    assert calls == [] and preloaded == []
    assert reads == [world.manifest_path]  # exactly the media manifest, nothing else
    assert cell_value() == "closed"


def test_startup_empty_never_reopens_even_after_a_valid_entry_and_new_reload(world: World) -> None:
    world.write_manifest(builds=[])
    assert world.factory()() is False
    world.write_manifest()  # a perfectly matching entry now exists
    assert world.factory()() is False
    world.reimport()
    assert world.factory()() is False
    assert cell_value() == "closed"


def test_shipped_real_manifest_is_closed_with_no_source_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed_fresh_anchor()
    g = real_gate
    reads: list[Path] = []
    original = g._read_one
    monkeypatch.setattr(g, "_read_one", lambda p, cap: reads.append(Path(p)) or original(p, cap))
    for name in ("_read_set", "_load_read_files", "_resolve_root", "_measure"):
        monkeypatch.setattr(g, name, lambda *_a, _n=name, **_k: pytest.fail(_n))
    for name in ("locate_hermes_root", "resolve_git_head_sha", "probe_read_dependencies"):
        monkeypatch.setattr(real_compat, name, lambda *_a, _n=name, **_k: pytest.fail(_n))
    identity = real_compat.BuildIdentity("a" * 64, None)
    preloaded: list[int] = []
    callback = g.media_listener_qualifier(identity, preload=lambda: preloaded.append(1) or ())
    assert callback is g._closed and callback() is False
    assert preloaded == [] and cell_value() == "closed"
    assert reads == [PACKAGE / "local_media_supported_builds.json"]
    # And again, from the latched state: no manifest read at all.
    reads.clear()
    assert g.media_listener_qualifier(identity) is g._closed and reads == []


def test_free_threaded_interpreter_never_creates_or_touches_an_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "_is_gil_enabled", lambda: False, raising=False)
    w = World(tmp_path)
    assert KEY not in sys.__dict__
    assert w.factory() is w.gate._closed and KEY not in sys.__dict__
    seed_fresh_anchor()  # even with an anchor present, nothing is read or written
    calls = trap(w, monkeypatch)
    assert w.factory() is w.gate._closed and calls == [] and cell_value() is None


@pytest.mark.parametrize(
    "probe", [lambda: (_ for _ in ()).throw(RuntimeError("x")), "not callable", None]
)
def test_undecidable_gil_probe_fails_closed_but_an_absent_one_means_gil(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, probe: Any
) -> None:
    if probe is None:
        monkeypatch.delattr(sys, "_is_gil_enabled", raising=False)
        w = World(tmp_path)
        assert KEY in sys.__dict__
        assert w.factory()() is True
        return
    monkeypatch.setattr(sys, "_is_gil_enabled", probe, raising=False)
    w = World(tmp_path)
    assert KEY not in sys.__dict__ and w.factory() is w.gate._closed


def test_admitted_listener_closes_if_the_interpreter_reports_free_threading(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    callback = admitted(world)
    monkeypatch.setattr(sys, "_is_gil_enabled", lambda: False, raising=False)
    assert callback() is False
    monkeypatch.undo()
    assert callback() is True


# --------------------------------------------------------------------------------------------
# Capture refusals latch closed and cannot be repaired
# --------------------------------------------------------------------------------------------


def latched_closed(world: World, **kw: Any) -> None:
    callback = world.factory(**kw)
    assert callback is world.gate._closed and callback() is False
    assert cell_value() == "closed"
    world.write_manifest()  # repair everything the test broke
    assert world.factory() is world.gate._closed  # a startup-closed process never reopens


def test_startup_wrong_native_fingerprint_latches_closed_and_repair_does_not_reopen(
    world: World,
) -> None:
    world.write_manifest(builds=[world.entry(native_fingerprint="0" * 64)])
    latched_closed(world)


def test_startup_wrong_hmp_fingerprint_latches_closed(world: World) -> None:
    world.write_manifest(builds=[world.entry(hmp_fingerprint="0" * 64)])
    latched_closed(world)


def test_startup_wrong_or_missing_git_sha_in_entry_latches_closed(world: World) -> None:
    world.write_manifest(builds=[world.entry(git_sha="f" * 40)])
    latched_closed(world)


def test_git_install_never_matches_a_fingerprint_only_entry(world: World) -> None:
    world.write_manifest(builds=[world.entry(git_sha=None)])
    latched_closed(world)


def test_no_git_install_matches_only_a_null_sha_entry(world: World) -> None:
    shutil.rmtree(world.root / ".git")
    world.write_manifest(builds=[world.entry(git_sha=SHA)])
    assert world.factory() is world.gate._closed
    assert cell_value() == "closed"
    seed_fresh_anchor()
    world.write_manifest(builds=[world.entry(git_sha=None)])
    assert world.factory()() is True


def test_source_sha_is_provenance_only(world: World) -> None:
    world.write_manifest(builds=[world.entry(source_sha="e" * 40)])
    assert world.factory()() is True


def test_unidentifiable_git_metadata_latches_closed(world: World) -> None:
    (world.root / ".git" / "HEAD").write_text("garbage\n")
    callback = world.factory(identity=world.compat.BuildIdentity(world.read_fp(), None))
    assert callback is world.gate._closed and cell_value() == "closed"
    (world.root / ".git" / "HEAD").write_text(SHA + "\n")
    assert world.factory() is world.gate._closed  # repairing the disk does not reopen


def test_missing_listed_native_or_plugin_file_latches_closed(world: World) -> None:
    (world.root / "d.py").rename(world.root / "d.moved")
    assert world.factory() is world.gate._closed and cell_value() == "closed"
    (world.root / "d.moved").rename(world.root / "d.py")
    assert world.factory() is world.gate._closed
    seed_fresh_anchor()
    (world.plugin / "helper.py").rename(world.plugin / "helper.moved")  # a listed HMP file
    assert world.factory() is world.gate._closed


def test_read_identity_drift_latches_closed(world: World) -> None:
    latched_closed(world, identity=world.identity(fingerprint="9" * 64))


def test_read_identity_git_drift_latches_closed(world: World) -> None:
    latched_closed(world, identity=world.identity(git_sha="9" * 40))


def test_read_identity_without_git_when_install_has_git_latches_closed(world: World) -> None:
    latched_closed(world, identity=world.identity(git_sha=None))


def test_read_files_not_covered_by_native_files_latch_closed(world: World) -> None:
    world.write_manifest(native=["a.py", "d.py"])
    world.write_manifest(
        builds=[
            world.entry(
                native_fingerprint=file_digest_oracle(world.root, ["a.py", "d.py"]),
            )
        ],
        native=["a.py", "d.py"],
    )
    latched_closed(world)


def test_malformed_missing_or_oversize_manifest_and_read_list_latch_closed(world: World) -> None:
    world.manifest_path.write_text("{")
    latched_closed(world)
    seed_fresh_anchor()
    world.manifest_path.unlink()
    latched_closed(world)
    seed_fresh_anchor()
    world.write_manifest()
    world.read_list.write_text("{}")
    assert world.factory() is world.gate._closed
    seed_fresh_anchor()
    world.read_list.write_text(
        json.dumps({"format": 1, "bridge_files": ["a.py", "b/c.py"], "builds": []})
    )
    assert world.factory()() is True


def test_symlinked_manifest_or_read_list_is_refused(world: World, tmp_path: Path) -> None:
    real = tmp_path / "real_manifest.json"
    real.write_bytes(world.manifest_path.read_bytes())
    world.manifest_path.unlink()
    world.manifest_path.symlink_to(real)
    assert world.factory() is world.gate._closed and cell_value() == "closed"


def test_symlinked_native_file_or_intermediate_directory_latches_closed(world: World) -> None:
    (world.root / "d.py").unlink()
    (world.root / "d.py").symlink_to(world.root / "a.py")
    assert world.factory() is world.gate._closed and cell_value() == "closed"
    seed_fresh_anchor()
    (world.root / "d.py").unlink()
    (world.root / "d.py").write_bytes(NATIVE_FILES["d.py"])
    shutil.move(world.root / "b", world.root / "b_real")
    (world.root / "b").symlink_to(world.root / "b_real")
    assert world.factory() is world.gate._closed


def test_oversize_aggregate_and_brackets_share_one_budget_per_invocation(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    one_pass = sum(len(b) for b in NATIVE_FILES.values()) + sum(
        (world.plugin / n).stat().st_size for n in world.hmp_files()
    )
    # One measurement fits; the capture needs two (before and after preload), so it is refused...
    monkeypatch.setattr(world.gate, "MAX_TOTAL_BYTES", one_pass + 1)
    assert world.factory() is world.gate._closed and cell_value() == "closed"
    # ...while a callback (one fresh measurement) fits the same cap.
    seed_fresh_anchor()
    monkeypatch.setattr(world.gate, "MAX_TOTAL_BYTES", 2 * one_pass + 1)
    callback = world.factory()
    assert callback() is True
    monkeypatch.setattr(world.gate, "MAX_TOTAL_BYTES", one_pass + 1)
    assert callback() is True
    monkeypatch.setattr(world.gate, "MAX_TOTAL_BYTES", one_pass - 1)
    assert callback() is False
    monkeypatch.setattr(world.gate, "MAX_TOTAL_BYTES", 2 * one_pass + 1)
    assert callback() is True  # a fresh invocation gets a fresh budget


def test_oversize_single_file_closes_capture_and_callback(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(world.gate, "MAX_FILE_BYTES", 5)
    assert world.factory() is world.gate._closed
    seed_fresh_anchor()
    monkeypatch.undo()
    callback = admitted(world)
    monkeypatch.setattr(world.gate, "MAX_FILE_BYTES", 5)
    assert callback() is False
    monkeypatch.undo()
    assert callback() is True


def test_plugin_shadow_forms_refuse_at_capture_and_in_the_callback(world: World) -> None:
    suffixes = importlib.machinery.all_suffixes()
    for suffix in suffixes:
        seed_fresh_anchor()
        shadow = world.plugin / f"adapter{suffix}"
        shadow.write_bytes(b"")
        assert world.factory() is world.gate._closed, suffix
        shadow.unlink()
    seed_fresh_anchor()
    callback = admitted(world)
    for name in ("adapter.cpython-314-darwin.so", "adapter.abi3.so", "foo.pyc", "extra.py"):
        (world.plugin / name).write_bytes(b"")
        assert callback() is False, name
        (world.plugin / name).unlink()
        assert callback() is True, name  # restoration reopens the matching listener
    (world.plugin / "sub").mkdir()
    (world.plugin / "sub" / "__init__.py").write_text("")
    assert callback() is False
    shutil.rmtree(world.plugin / "sub")
    assert callback() is True
    cache = world.plugin / "__pycache__"
    cache.mkdir(exist_ok=True)  # independent of bytecode writing (-B); regular caches are accepted
    (cache / "fifo").touch()
    (cache / "fifo").unlink()
    os.mkfifo(cache / "fifo")
    assert callback() is False
    (cache / "fifo").unlink()
    assert callback() is True


def test_plugin_listing_is_not_hashed_but_unlisted_plugin_py_is_refused(world: World) -> None:
    (world.plugin / "plugin.yaml").write_text("name: x\n")
    (world.plugin / "extra.json").write_text("{}")
    callback = admitted(world)
    (world.plugin / "plugin.yaml").write_text("name: changed\n")  # loader metadata: residual
    assert callback() is True


# --------------------------------------------------------------------------------------------
# Preload and loaded-origin checks
# --------------------------------------------------------------------------------------------


def test_preload_is_required_and_none_never_admits(world: World) -> None:
    callback = world.factory(preload=None)
    assert callback is world.gate._closed and callback() is False
    assert cell_value() == "closed"


@pytest.mark.parametrize(
    "result",
    [None, [], (), "mods", object(), 7],
    ids=["none", "list", "empty_tuple", "str", "object", "int"],
)
def test_preload_wrong_shape_latches_closed(world: World, result: Any) -> None:
    assert world.factory(preload=lambda: result) is world.gate._closed
    assert cell_value() == "closed"


def test_preload_exception_latches_closed_and_does_not_leak(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom() -> Any:
        raise RuntimeError(f"/private/{SECRET}")

    assert world.factory(preload=boom) is world.gate._closed
    out = capsys.readouterr()
    assert SECRET not in out.out + out.err and cell_value() == "closed"


def stub_module(world: World, name: str, **kw: Any) -> types.ModuleType:
    """A module object whose origin facts can each be made wrong."""
    stem = kw.pop("stem", name)
    file = kw.pop("file", str(world.plugin / f"{stem}.py"))
    loader_type = kw.pop("loader", importlib.machinery.SourceFileLoader)
    origin = kw.pop("origin", file)
    mod_name = kw.pop("module_name", f"{world.pkg}.{name}")
    module = types.ModuleType(mod_name)
    spec = importlib.machinery.ModuleSpec(mod_name, loader_type(mod_name, file), origin=origin)
    module.__spec__ = spec
    module.__file__ = file
    assert not kw
    return module


def test_stub_positive_control_passes_the_origin_check(world: World) -> None:
    good = stub_module(world, "helper")
    assert world.factory(preload=lambda: (good, *world.modules()))() is True


@pytest.mark.parametrize(
    "kind",
    [
        "outside_dir",
        "other_dir_same_name",
        "not_source_loader",
        "sourceless_loader",
        "origin_ne_file",
        "unlisted_stem",
        "wrong_name",
        "no_spec",
        "no_file",
        "subclass_loader",
        "namespace_name",
        "wrong_package",
    ],
)
def test_origin_decoys_close_the_candidate(world: World, tmp_path: Path, kind: str) -> None:
    decoy_dir = tmp_path / "decoy"
    decoy_dir.mkdir()
    (decoy_dir / "helper.py").write_text("x")
    sub = type("SubLoader", (importlib.machinery.SourceFileLoader,), {})
    module = {
        "outside_dir": lambda: stub_module(world, "helper", file=str(decoy_dir / "helper.py")),
        "other_dir_same_name": lambda: stub_module(
            world,
            "helper",
            file=str(world.plugin / ".." / "plugin" / ".." / ".." / "decoy" / "helper.py"),
        ),
        "not_source_loader": lambda: stub_module(
            world, "helper", loader=importlib.machinery.ExtensionFileLoader
        ),
        "sourceless_loader": lambda: stub_module(
            world, "helper", loader=importlib.machinery.SourcelessFileLoader
        ),
        "origin_ne_file": lambda: stub_module(
            world, "helper", origin=str(world.plugin / "compat.py")
        ),
        "unlisted_stem": lambda: stub_module(world, "unlisted", stem="unlisted"),
        "wrong_name": lambda: stub_module(world, "helper", module_name="other.helper"),
        "no_spec": lambda: _strip(stub_module(world, "helper"), "__spec__"),
        "no_file": lambda: _strip(stub_module(world, "helper"), "__file__"),
        "subclass_loader": lambda: stub_module(world, "helper", loader=sub),
        "namespace_name": lambda: stub_module(world, "helper", module_name="helper"),
        "wrong_package": lambda: stub_module(world, "helper", module_name="hmpgate_other.helper"),
    }[kind]()
    if kind == "unlisted_stem":
        (world.plugin / "unlisted.py").write_text("x")  # present but not in the manifest list
        world.write_manifest(hmp=[n for n in world.hmp_files() if n != "unlisted.py"])
        world.write_manifest(
            builds=[
                world.entry(
                    hmp_fingerprint=file_digest_oracle(
                        world.plugin, [n for n in world.hmp_files() if n != "unlisted.py"]
                    )
                )
            ],
            hmp=[n for n in world.hmp_files() if n != "unlisted.py"],
        )
        # the extra .py is itself refused, so use a manifest-less stem instead
        (world.plugin / "unlisted.py").unlink()
    assert world.factory(preload=lambda: (module, *world.modules())) is world.gate._closed
    assert cell_value() == "closed"


def _strip(module: types.ModuleType, attr: str) -> types.ModuleType:
    if attr == "__spec__":
        module.__spec__ = None
    else:
        del module.__file__
    return module


def test_out_of_tree_leaf_symlink_alias_is_refused(world: World, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "helper.py").symlink_to(world.plugin / "helper.py")
    alias = stub_module(world, "helper", file=str(outside / "helper.py"))
    assert world.factory(preload=lambda: (alias, *world.modules())) is world.gate._closed
    assert cell_value() == "closed"


def test_whole_directory_alias_of_the_plugin_dir_still_admits(world: World, tmp_path: Path) -> None:
    home = tmp_path / "home_alias"
    home.symlink_to(world.plugin, target_is_directory=True)
    good = stub_module(world, "helper", file=str(home / "helper.py"))
    assert world.factory(preload=lambda: (good, *world.modules()))() is True


@pytest.mark.parametrize("field", ["path", "name"])
def test_loader_path_and_name_must_match_the_spec(world: World, field: str) -> None:
    bad = stub_module(world, "helper")
    loader = importlib.machinery.SourceFileLoader(
        bad.__name__ if field == "path" else "other.name",
        str(world.plugin / "compat.py") if field == "path" else str(world.plugin / "helper.py"),
    )
    bad.__spec__.loader = loader
    assert world.factory(preload=lambda: (bad, *world.modules())) is world.gate._closed
    assert cell_value() == "closed"


def test_build_identity_subclass_is_refused_without_touching_the_anchor(world: World) -> None:
    class Sub(world.compat.BuildIdentity):  # type: ignore[name-defined, misc]
        pass

    before = cell_value()
    callback = world.factory(identity=Sub(world.read_fp(), world.git()))
    assert callback is world.gate._closed and cell_value() == before


def test_symlinked_module_file_and_duplicate_modules_are_refused(world: World) -> None:
    alias = world.plugin / "alias_link.py"
    alias.symlink_to(world.plugin / "helper.py")
    link_module = stub_module(world, "alias_link")
    assert world.factory(preload=lambda: (link_module, *world.modules())) is world.gate._closed
    alias.unlink()
    seed_fresh_anchor()
    package, gate, _compat = world.modules()
    assert world.factory(preload=lambda: (gate, gate)) is world.gate._closed
    seed_fresh_anchor()
    assert world.factory(preload=lambda: [package, gate]) is world.gate._closed
    seed_fresh_anchor()
    assert (
        world.factory(preload=lambda: (package, gate, types.SimpleNamespace()))
        is world.gate._closed
    )


def test_module_subclass_instances_are_not_exact_module_types(world: World) -> None:
    class Sub(types.ModuleType):
        pass

    sub = Sub(f"{world.pkg}.helper")
    sub.__spec__ = importlib.machinery.ModuleSpec(
        sub.__name__,
        importlib.machinery.SourceFileLoader(sub.__name__, str(world.plugin / "helper.py")),
        origin=str(world.plugin / "helper.py"),
    )
    sub.__file__ = str(world.plugin / "helper.py")
    assert world.factory(preload=lambda: (sub,)) is world.gate._closed


def test_sys_modules_names_are_never_consulted_for_origins(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    decoy = types.ModuleType("decoy")
    decoy.__file__ = "/etc/decoy.py"
    for name in (f"{world.pkg}.compat", f"{world.pkg}.local_media_gate", world.pkg):
        monkeypatch.setitem(sys.modules, name, decoy)
    # The tuple holds the real objects this load bound: admitted despite hostile names.
    assert world.factory()() is True
    # And a bad tuple is not rescued by good sys.modules entries.
    seed_fresh_anchor()
    monkeypatch.undo()
    bad = stub_module(world, "helper", file="/etc/passwd")
    assert world.factory(preload=lambda: (bad,)) is world.gate._closed


def test_package_name_is_derived_from_the_gates_own_package_for_home_suffixed_copies(
    world: World,
) -> None:
    alias_name = f"{world.pkg}__home_{'a' * 12}"
    package, gate, compat = load_package(world.plugin, alias_name)
    assert gate.__package__ == alias_name
    callback = gate.media_listener_qualifier(
        compat.BuildIdentity(world.read_fp(), world.git()),
        preload=lambda: (package, gate, compat),
        hermes_root=world.root,
        plugin_dir=world.plugin,
        manifest_path=world.manifest_path,
        read_compat_path=world.read_list,
    )
    assert callback() is True
    # The ORIGINAL copy's modules are the wrong objects for this package name.
    seed_fresh_anchor()
    assert (
        gate.media_listener_qualifier(
            compat.BuildIdentity(world.read_fp(), world.git()),
            preload=world.modules,
            hermes_root=world.root,
            plugin_dir=world.plugin,
            manifest_path=world.manifest_path,
            read_compat_path=world.read_list,
        )
        is gate._closed
    )


def test_preload_runs_only_after_an_exact_match(world: World) -> None:
    calls: list[int] = []
    world.write_manifest(builds=[world.entry(native_fingerprint="0" * 64)])
    assert world.factory(preload=lambda: calls.append(1) or world.modules()) is world.gate._closed
    assert calls == []
    seed_fresh_anchor()
    world.write_manifest()
    assert world.factory(preload=lambda: calls.append(1) or world.modules())() is True
    assert calls == [1]


def test_edit_of_a_listed_plugin_file_during_preload_latches_closed(world: World) -> None:
    def edit() -> Any:
        world.append_hmp()
        return world.modules()

    assert world.factory(preload=edit) is world.gate._closed
    assert cell_value() == "closed"


def test_edit_of_a_native_file_during_preload_latches_closed(world: World) -> None:
    def edit() -> Any:
        world.edit_native("d.py", b"D = 99\n")
        return world.modules()

    assert world.factory(preload=edit) is world.gate._closed


def test_git_head_move_during_preload_latches_closed(world: World) -> None:
    def move() -> Any:
        (world.root / ".git" / "HEAD").write_text("f" * 40 + "\n")
        return world.modules()

    assert world.factory(preload=move) is world.gate._closed


def test_preload_that_only_adds_a_shadow_extension_latches_closed(world: World) -> None:
    def shadow() -> Any:
        (world.plugin / "helper.abi3.so").write_bytes(b"")
        return world.modules()

    assert world.factory(preload=shadow) is world.gate._closed


# --------------------------------------------------------------------------------------------
# Callback behavior after admission
# --------------------------------------------------------------------------------------------


def test_callback_returns_exact_bools(world: World) -> None:
    callback = world.factory()
    assert callback() is True
    world.edit_native("d.py", b"D = 4\n")
    assert callback() is False


def test_native_edit_closes_and_restore_reopens(world: World) -> None:
    callback = admitted(world)
    world.edit_native("d.py", b"D = 4\n")
    assert callback() is False
    world.edit_native("d.py", NATIVE_FILES["d.py"])
    assert callback() is True
    world.edit_native("a.py", b"A = 5\n")  # a read file too
    assert callback() is False
    world.edit_native("a.py", NATIVE_FILES["a.py"])
    assert callback() is True


def test_hmp_edit_closes_and_restore_reopens(world: World) -> None:
    callback = admitted(world)
    for name in ("helper.py", "compat.py", "local_media_gate.py", "__init__.py"):
        original = world.append_hmp(name)
        assert callback() is False, name
        world.restore_hmp(original, name)
        assert callback() is True, name


def test_entry_removal_closes_and_restoration_reopens(world: World) -> None:
    callback = admitted(world)
    entry = world.entry()
    world.write_manifest(builds=[])
    assert callback() is False
    world.write_manifest(builds=[entry])
    assert callback() is True
    world.write_manifest(builds=[world.entry(label="other", native_fingerprint="1" * 64)])
    assert callback() is False
    world.write_manifest(builds=[world.entry(label="other-label")])
    assert callback() is True  # same exact fingerprints under a different label still match


def test_swap_to_another_listed_build_closes_until_restart(world: World) -> None:
    callback = admitted(world)
    first = world.entry()
    world.edit_native("d.py", b"D = 7\n")
    second = world.entry(label="second")
    world.write_manifest(builds=[first, second])  # both builds are listed; disk is the second
    assert callback() is False
    assert world.factory() is world.gate._closed  # nor can a reconnect adopt it
    world.reimport()
    assert world.factory() is world.gate._closed
    world.edit_native("d.py", NATIVE_FILES["d.py"])
    assert callback() is True
    seed_fresh_anchor()  # the OS-restart equivalent: only a fresh process anchor changes this
    world.edit_native("d.py", b"D = 7\n")
    assert world.factory()() is True


def test_manifest_edits_that_change_lists_or_become_invalid_close(world: World) -> None:
    callback = admitted(world)
    good = world.manifest_path.read_text()
    for bad in ("{", "[]", json.dumps({"format": "hmp-local-media-2"}), ""):
        world.manifest_path.write_text(bad)
        assert callback() is False
    world.write_manifest(native=["a.py", "b/c.py", "d.py", "e.py"])
    assert callback() is False
    world.write_manifest(hmp=["__init__.py", "compat.py"])
    assert callback() is False
    world.manifest_path.unlink()
    assert callback() is False
    world.manifest_path.write_text(good)
    assert callback() is True


def test_read_list_edits_close(world: World) -> None:
    callback = admitted(world)
    good = world.read_list.read_text()
    world.read_list.write_text(json.dumps({"format": 1, "bridge_files": ["a.py"], "builds": []}))
    assert callback() is False
    world.read_list.unlink()
    assert callback() is False
    world.read_list.write_text(good)
    assert callback() is True


def test_git_sha_change_or_removal_closes_and_restore_reopens(world: World) -> None:
    callback = admitted(world)
    (world.root / ".git" / "HEAD").write_text("e" * 40 + "\n")
    assert callback() is False
    (world.root / ".git" / "HEAD").write_text("garbage\n")
    assert callback() is False
    shutil.move(world.root / ".git", world.root / ".git.bak")
    assert callback() is False  # no-git now, a baseline that had a SHA
    shutil.move(world.root / ".git.bak", world.root / ".git")
    (world.root / ".git" / "HEAD").write_text(SHA + "\n")
    assert callback() is True


def test_wrong_root_or_moved_plugin_directory_closes(world: World, tmp_path: Path) -> None:
    callback = admitted(world)
    clone_root = tmp_path / "other_native"
    shutil.copytree(world.root, clone_root)
    clone_plugin = tmp_path / "other_plugin"
    shutil.copytree(world.plugin, clone_plugin)

    def current(**kw: Any) -> bool:
        return world.gate._check_current(
            world.gate._decode(cell_value()),
            cell_value(),
            kw.get("hermes_root", world.root),
            kw.get("plugin_dir", world.plugin),
            world.manifest_path,
            world.read_list,
        )

    assert current() is True
    assert current(hermes_root=clone_root) is False  # identical bytes, different root
    assert current(plugin_dir=clone_plugin) is False  # identical bytes, different directory
    assert callback() is True


def test_symlink_alias_of_root_resolves_to_the_same_baseline(world: World, tmp_path: Path) -> None:
    link = tmp_path / "root_link"
    link.symlink_to(world.root)
    callback = world.factory(hermes_root=link)
    assert callback() is True and cell_value()[1] == str(world.root)


def test_extra_plugin_py_added_after_admission_closes_and_removal_reopens(world: World) -> None:
    callback = admitted(world)
    (world.plugin / "new_helper.py").write_text("x = 1\n")
    assert callback() is False
    (world.plugin / "new_helper.py").unlink()
    assert callback() is True


def test_probe_is_fresh_every_check_with_exact_arguments_and_no_cache(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[dict[str, Any]] = []
    results = iter([(), ("some.dep",), (), ()])

    def probe(**kw: Any) -> Any:
        seen.append(kw)
        return next(results)

    monkeypatch.setattr(world.compat, "probe_read_dependencies", probe)
    callback = world.factory()
    assert seen == []  # capture does not probe
    assert [callback(), callback(), callback(), callback()] == [True, False, True, True]
    assert len(seen) == 4
    for kw in seen:
        assert kw["specs"] is world.gate.MEDIA_DEPENDENCIES
        assert kw["bridge_files"] == tuple(world.native_files())
        assert kw["hermes_root"] == world.root
    monkeypatch.setattr(world.compat, "probe_read_dependencies", lambda **_k: ["x"])
    assert callback() is False
    monkeypatch.setattr(world.compat, "probe_read_dependencies", lambda **_k: 0)
    assert callback() is False  # not a sequence: closed, never raises


def test_probe_runs_only_after_every_disk_check_passes(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    callback = admitted(world)
    calls: list[int] = []
    monkeypatch.setattr(world.compat, "probe_read_dependencies", lambda **_k: calls.append(1) or ())
    world.edit_native("d.py", b"D = 8\n")
    assert callback() is False and calls == []  # no native import after a mismatch


# --- the real probe against synthetic dependency modules -------------------------------------

DEP_FILES = {
    "hmpfake_good.py": "class Api:\n    def method(self, x):\n        return x\n\n"
    "def top(a, b=1):\n    return a\n\nCONST = 5\nbuiltin_alias = len\n",
    "hmpfake_unlisted_def.py": "from hmpfake_elsewhere import foreign\n",
    "hmpfake_deco.py": (
        "from hmpfake_elsewhere import deco\n\n@deco\ndef wrapped(x):\n    return x\n"
    ),
}
UNLISTED_FILES = {
    "hmpfake_elsewhere.py": "import functools\n\ndef foreign(x):\n    return x\n\n"
    "def deco(fn):\n    @functools.wraps(fn)\n    def inner(*a, **k):\n        return fn(*a, **k)\n"
    "    return inner\n",
}


@pytest.fixture
def probe_world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    data = {**NATIVE_FILES, **{k: v.encode() for k, v in {**DEP_FILES, **UNLISTED_FILES}.items()}}
    # `hmpfake_elsewhere.py` exists on disk but is deliberately NOT a listed file.
    world = World(tmp_path, data=data, listed=[*NATIVE_FILES, *DEP_FILES], real_probe=True)
    monkeypatch.syspath_prepend(str(world.root))
    yield world
    for name in [n for n in sys.modules if n.startswith("hmpfake_")]:
        del sys.modules[name]


def fake_specs(world: World, *names: tuple[str, str | None]) -> tuple[Any, ...]:
    return tuple(world.compat.DependencySpec(m, q) for m, q in names)


@pytest.mark.parametrize(
    ("spec", "ok"),
    [
        (("hmpfake_good", None), True),
        (("hmpfake_good", "top"), True),
        (("hmpfake_good", "Api"), True),
        (("hmpfake_good", "Api.method"), True),
        (("hmpfake_missing_module", None), False),
        (("hmpfake_good", "absent"), False),
        (("hmpfake_good", "Api.absent"), False),
        (("hmpfake_good", "CONST"), False),  # not callable
        (("hmpfake_good", "builtin_alias"), False),  # no determinable defining file
        (("hmpfake_unlisted_def", "foreign"), False),  # defined in an unlisted file
        (("hmpfake_deco", "wrapped"), False),  # decorator layer lives in an unlisted file
    ],
)
def test_real_probe_missing_nonsignature_and_unlisted_definitions_close(
    probe_world: World, spec: tuple[str, str | None], ok: bool
) -> None:
    w = probe_world
    w.gate.MEDIA_DEPENDENCIES = fake_specs(w, spec)
    assert w.factory()() is ok


def test_real_probe_sees_a_later_unlisted_replacement_each_check(probe_world: World) -> None:
    w = probe_world
    w.gate.MEDIA_DEPENDENCIES = fake_specs(w, ("hmpfake_good", "top"))
    callback = w.factory()
    assert callback() is True
    good = sys.modules["hmpfake_good"]
    original = good.top
    import hmpfake_elsewhere

    good.top = hmpfake_elsewhere.foreign  # a monkeypatch to a function defined in an unlisted file
    assert callback() is False
    good.top = original
    assert callback() is True  # failures and passes are never cached


# --------------------------------------------------------------------------------------------
# Reconnect, reload, aliases, directories
# --------------------------------------------------------------------------------------------


def test_reconnect_semantics_matching_listener_reopens_but_mismatched_one_never_does(
    world: World,
) -> None:
    first = admitted(world)
    original = world.append_hmp()
    during = world.factory()  # a reconnect captured while disk differs from the baseline
    assert during is world.gate._closed
    assert first() is False
    world.restore_hmp(original)
    assert first() is True  # the matching listener reopens after a fresh equal check
    assert during() is False  # the mismatched listener stays closed for its life
    third = world.factory()  # a reconnect after restoration is admitted again
    assert third is not world.gate._closed and third() is True
    assert type(cell_value()) is tuple  # the baseline is still the one first-factory tuple


def test_baseline_is_never_redefined_by_a_later_capture(world: World) -> None:
    admitted(world)
    fixed = cell_value()
    world.edit_native("d.py", b"D = 11\n")
    world.write_manifest(builds=[world.entry(label="newer")])
    assert world.factory() is world.gate._closed
    assert cell_value() is fixed


def test_real_eviction_and_reimport_keeps_the_baseline_across_class_identities(
    world: World,
) -> None:
    first_gate, first_compat = world.gate, world.compat
    first_callback = admitted(world)
    fixed = cell_value()
    world.reimport()
    assert world.gate is not first_gate and world.compat is not first_compat
    assert world.compat.BuildIdentity is not first_compat.BuildIdentity
    assert world.gate.MediaProcessBaseline is not first_gate.MediaProcessBaseline
    second_callback = world.factory()
    assert second_callback is not world.gate._closed and second_callback() is True
    assert cell_value() is fixed  # the same object: not re-baselined, not repaired
    # Change one HMP byte and reload again: the new copy closes, and so does the first copy.
    original = world.append_hmp("contract.py")
    world.reimport()
    third = world.factory()
    assert third is world.gate._closed and third() is False
    assert first_callback() is False and second_callback() is False
    world.restore_hmp(original, "contract.py")
    assert first_callback() is True and second_callback() is True  # matching listeners reopen
    assert third() is False  # the closed-at-capture listener does not
    assert cell_value() is fixed


def test_plugin_class_instance_forged_into_the_cell_closes_without_repair(world: World) -> None:
    admitted(world)
    good = cell_value()
    world.reimport()
    forged = world.gate.MediaProcessBaseline(*good[1:])
    cell()[0] = forged
    assert world.factory() is world.gate._closed
    assert cell_value() is forged
    cell()[0] = good
    assert world.factory()() is True  # another copy's class objects still validate the primitives


def test_two_aliases_of_one_directory_share_one_anchor_and_empty_first_stays_closed(
    tmp_path: Path,
) -> None:
    w = World(tmp_path)
    alias_name = f"{w.pkg}__home_{'b' * 12}"
    package, gate, compat = load_package(w.plugin, alias_name)
    assert gate is not w.gate
    first = w.factory()
    assert first() is True
    second = gate.media_listener_qualifier(
        compat.BuildIdentity(w.read_fp(), w.git()),
        preload=lambda: (package, gate, compat),
        hermes_root=w.root,
        plugin_dir=w.plugin,
        manifest_path=w.manifest_path,
        read_compat_path=w.read_list,
    )
    assert second() is True and first() is True
    evict(alias_name)
    package, gate, compat = load_package(w.plugin, alias_name)
    third = gate.media_listener_qualifier(
        compat.BuildIdentity(w.read_fp(), w.git()),
        preload=lambda: (package, gate, compat),
        hermes_root=w.root,
        plugin_dir=w.plugin,
        manifest_path=w.manifest_path,
        read_compat_path=w.read_list,
    )
    assert third() is True


def test_empty_first_factory_keeps_every_alias_and_reload_closed(tmp_path: Path) -> None:
    w = World(tmp_path)
    w.write_manifest(builds=[])
    assert w.factory()() is False
    w.write_manifest()
    alias_name = f"{w.pkg}__home_{'c' * 12}"
    package, gate, compat = load_package(w.plugin, alias_name)
    kw = {
        "preload": lambda: (package, gate, compat),
        "hermes_root": w.root,
        "plugin_dir": w.plugin,
        "manifest_path": w.manifest_path,
        "read_compat_path": w.read_list,
    }
    assert (
        gate.media_listener_qualifier(compat.BuildIdentity(w.read_fp(), w.git()), **kw)
        is gate._closed
    )
    evict(alias_name)
    package, gate, compat = load_package(w.plugin, alias_name)
    kw["preload"] = lambda: (package, gate, compat)
    assert (
        gate.media_listener_qualifier(compat.BuildIdentity(w.read_fp(), w.git()), **kw)
        is gate._closed
    )
    w.reimport()
    assert w.factory() is w.gate._closed


def test_a_second_plugin_directory_or_native_root_closes_even_with_identical_bytes(
    tmp_path: Path,
) -> None:
    first = World(tmp_path, "one")
    assert first.factory()() is True
    other_plugin = World(tmp_path, "two", like=first)  # same bytes, a different plugin directory
    assert other_plugin.plugin != first.plugin
    assert other_plugin.hmp_fp() == first.hmp_fp()
    callback = other_plugin.factory()
    assert callback is other_plugin.gate._closed and callback() is False
    assert first.factory()() is True  # the original directory is unaffected
    clone_root = tmp_path / "clone_native"
    shutil.copytree(first.root, clone_root)
    assert first.factory(hermes_root=clone_root) is first.gate._closed


def test_nested_factory_inside_preload_proves_the_anchor_lock_is_not_held(world: World) -> None:
    inner_results: list[bool] = []

    def preload() -> Any:
        lock = sys.__dict__[KEY][1]
        assert lock.acquire(False), "the anchor lock was held across preload"
        lock.release()
        inner = world.factory()  # re-enters the gate, which takes the (non-reentrant) lock
        inner_results.append(inner())
        return world.modules()

    box: list[Any] = []
    thread = threading.Thread(
        target=lambda: box.append(world.factory(preload=preload)()), daemon=True
    )
    thread.start()
    thread.join(30)
    assert not thread.is_alive(), "deadlock: the anchor lock was held over preload"
    assert box == [True] and inner_results == [True]


def test_blocked_preload_does_not_block_another_factory_or_the_anchor(world: World) -> None:
    release = threading.Event()
    entered = threading.Event()

    def slow() -> Any:
        entered.set()
        assert release.wait(30)
        return world.modules()

    box: list[Any] = []
    thread = threading.Thread(target=lambda: box.append(world.factory(preload=slow)), daemon=True)
    thread.start()
    assert entered.wait(30)
    lock = sys.__dict__[KEY][1]
    assert lock.acquire(False)  # not held while the first factory sits in preload
    lock.release()
    other = world.factory()  # completes the capture and writes the one baseline
    assert other() is True
    fixed = cell_value()
    release.set()
    thread.join(30)
    assert not thread.is_alive() and box[0]() is True  # the loser compared against the winner
    assert cell_value() is fixed


@pytest.mark.parametrize("variant", ["success", "failure", "mixed"])
def test_eight_concurrent_factories_across_two_copies_make_one_transition_and_agree(
    tmp_path: Path, variant: str
) -> None:
    w = World(tmp_path)
    alias_name = f"{w.pkg}__home_{'d' * 12}"
    package, gate2, compat2 = load_package(w.plugin, alias_name)
    if variant == "failure":
        w.write_manifest(builds=[w.entry(native_fingerprint="0" * 64)])
    writes: list[tuple[str, bool]] = []
    counter_lock = threading.Lock()
    for mod in (w.gate, gate2):
        original = mod._first_transition

        def counted(lock: Any, c: list[Any], new: Any, _o: Any = original) -> Any:
            with counter_lock:
                writes.append(("t", c[0] is None))
                return _o(lock, c, new)

        mod._first_transition = counted
    barrier = threading.Barrier(8)
    results: list[Any] = [None] * 8

    def run(i: int) -> None:
        use_alias = i % 2 == 1
        gate, compat = (gate2, compat2) if use_alias else (w.gate, w.compat)
        mods = (package, gate2, compat2) if use_alias else w.modules()
        preload = (
            (lambda: (_ for _ in ()).throw(RuntimeError("x")))
            if (variant == "mixed" and i == 3)
            else (lambda m=mods: m)
        )
        barrier.wait(30)
        callback = gate.media_listener_qualifier(
            compat.BuildIdentity(w.read_fp(), w.git()),
            preload=preload,
            hermes_root=w.root,
            plugin_dir=w.plugin,
            manifest_path=w.manifest_path,
            read_compat_path=w.read_list,
        )
        results[i] = callback

    threads = [threading.Thread(target=run, args=(i,), daemon=True) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(60)
    assert not any(t.is_alive() for t in threads)
    assert [flag for _, flag in writes].count(True) == 1  # exactly one None-to-value write
    fixed = cell_value()
    outcomes = [cb() for cb in results]
    if variant == "failure":
        assert fixed == "closed" and outcomes == [False] * 8
    elif variant == "success":
        assert type(fixed) is tuple and outcomes == [True] * 8
    else:
        # Either the thread whose preload raised raced first (everything latches closed) or it
        # lost and only that one listener is closed; the outcomes always agree with the cell.
        if fixed == "closed":
            assert outcomes == [False] * 8
        else:
            assert outcomes == [i != 3 for i in range(8)]


# --------------------------------------------------------------------------------------------
# Never raises, never leaks private values
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "_load_read_files",
        "load_media_manifest",
        "_resolve_root",
        "_resolve_plugin_dir",
        "_measure",
        "match_media_build",
        "_anchor_parts",
        "_read_cell",
        "_gil_guard_ok",
        "_manifest_path",
    ],
)
def test_callback_never_raises_whatever_step_fails(
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    callback = admitted(world)

    def boom(*_a: Any, **_k: Any) -> Any:
        raise RuntimeError(f"/Users/{SECRET}/digest-{'f' * 64}")

    monkeypatch.setattr(world.gate, name, boom)
    caplog.set_level("DEBUG")
    assert callback() is False
    monkeypatch.undo()
    assert callback() is True
    seen = capsys.readouterr()
    assert SECRET not in seen.out + seen.err + caplog.text and caplog.records == []


@pytest.mark.parametrize("target", ["resolve_git_head_sha", "probe_read_dependencies"])
def test_compat_failures_never_raise_from_the_callback(
    world: World, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    callback = admitted(world)

    def boom(*_a: Any, **_k: Any) -> Any:
        raise OSError(f"/Users/{SECRET}")

    monkeypatch.setattr(world.compat, target, boom)
    assert callback() is False


@pytest.mark.parametrize(
    "name", ["_capture", "_anchor_parts", "_read_cell", "_first_transition", "_decode"]
)
def test_factory_never_raises_and_returns_the_constant_closed_callback(
    world: World, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    def boom(*_a: Any, **_k: Any) -> Any:
        raise RuntimeError(f"/Users/{SECRET}")

    monkeypatch.setattr(world.gate, name, boom)
    result = world.factory()
    assert result is world.gate._closed and result() is False


def test_no_private_value_reaches_logs_or_streams_on_any_refusal(
    world: World, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("DEBUG")
    callback = admitted(world)
    world.edit_native("d.py", b"D = 5\n")
    (world.plugin / "x.so").write_bytes(b"")
    assert callback() is False
    world.write_manifest(builds=[world.entry(label=f"label-{SECRET}")])
    assert callback() is False
    out = capsys.readouterr()
    assert SECRET not in out.out + out.err + caplog.text and not caplog.records
    for digest in (world.native_fp(), world.hmp_fp()):
        assert digest not in out.out + out.err + caplog.text


# --------------------------------------------------------------------------------------------
# Independence from the other qualification lanes
# --------------------------------------------------------------------------------------------


def test_media_gate_leaves_every_other_lane_state_untouched(world: World) -> None:
    def snapshot() -> tuple[Any, ...]:
        c = real_compat
        return (
            c._approval_process_latch,
            dict(c._approval_probe_cache),
            c._direct_send_qualified_cache,
            world.compat._approval_process_latch,
            dict(world.compat._approval_probe_cache),
            world.compat._direct_send_qualified_cache,
        )

    before = snapshot()
    callback = admitted(world)
    world.edit_native("d.py", b"D = 6\n")
    assert callback() is False
    assert snapshot() == before


def test_admitted_media_does_not_qualify_approval_or_direct_send(
    world: World, tmp_path: Path
) -> None:
    admitted(world)
    empty = tmp_path / "approval.json"
    empty.write_text(json.dumps({"format": 1, "bridge_files": READ_FILES, "builds": []}))
    assert (
        world.compat.approval_build_qualified(
            world.identity(), hermes_root=world.root, compat_path=empty
        )
        is False
    )
    qualifier = world.compat.approval_listener_qualifier(
        world.identity(),
        hermes_root=world.root,
        compat_path=empty,
        read_compat_path=world.read_list,
    )
    assert qualifier() is False
    assert world.compat._approval_process_latch == (None,)  # approval latched itself; media did not


def test_approval_or_read_entries_with_identical_fingerprints_do_not_open_media(
    world: World, tmp_path: Path
) -> None:
    world.write_manifest(builds=[])
    approval = tmp_path / "approval.json"
    approval.write_text(
        json.dumps(
            {
                "format": 1,
                "bridge_files": READ_FILES,
                "builds": [
                    {
                        "label": "x",
                        "fingerprint": world.read_fp(),
                        "git_sha": SHA,
                        "source_sha": None,
                        "qualified_by": "t",
                        "qualified_at": "2026-10-01",
                    }
                ],
            }
        )
    )
    assert world.compat.load_read_compat_list(approval).builds  # a valid read-style list
    with pytest.raises(ValueError):
        world.gate.parse_media_manifest(approval.read_bytes())
    assert world.factory() is world.gate._closed


def test_gate_module_names_no_other_lanes_manifest_or_latch() -> None:
    for word in ("approval_supported", "direct_send_supported", "write_supported", "mobile_"):
        assert word not in GATE_SOURCE
    assert real_gate.MEDIA_COMPAT_FILE == "local_media_supported_builds.json"
    assert real_gate.MEDIA_COMPAT_FILE != real_compat.READ_COMPAT_FILE


def test_default_root_location_is_used_each_check_and_must_match_the_baseline(
    world: World, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(world.compat, "locate_hermes_root", lambda: world.root)
    callback = world.factory(hermes_root=None)
    assert callback() is True
    other = tmp_path / "other_native"
    shutil.copytree(world.root, other)
    monkeypatch.setattr(world.compat, "locate_hermes_root", lambda: other)
    assert callback() is False
    monkeypatch.setattr(world.compat, "locate_hermes_root", lambda: None)
    assert callback() is False

    def boom() -> Any:
        raise OSError(f"/Users/{SECRET}")

    monkeypatch.setattr(world.compat, "locate_hermes_root", boom)
    assert callback() is False
    monkeypatch.setattr(world.compat, "locate_hermes_root", lambda: world.root)
    assert callback() is True
