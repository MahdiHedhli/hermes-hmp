"""Prepare only fresh synthetic Linux native-journey software inputs.

No Hermes CLI/provider/native entry runs here. Hash-pinned trusted software is
installed into an exclusive root; no shared tool, host home or configuration is
updated. Run only on the owned disposable Linux CI runner after review.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
import tarfile
import urllib.parse
import urllib.request
from pathlib import Path

_PINS = {
    "python": {
        "version": "3.14.9+20261021",
        "sha256": "dfa4c5a40c47f338f41658017be550c72247c391e6bfb1fa4da03ebc8451abdf",
        "url": "https://github.com/astral-sh/python-build-standalone/releases/download/20261021/cpython-3.14.9+20261021-x86_64-unknown-linux-gnu-install_only.tar.gz",
    },
    "uv": {
        "version": "0.13.5",
        "sha256": "f68d291c75783122dad58ab77def0e13f3233f358731db5d6d7e8715603b928f",
        "url": "https://github.com/astral-sh/uv/releases/download/0.13.5/uv-x86_64-unknown-linux-gnu.tar.gz",
    },
}
_REQ_SHA = "9edcfc564b10ad1ffca7a3d7a02d1a855a5d203cb807d566b85ce5598eb9df94"


class LinuxPreparationError(RuntimeError):
    """Fixed refusal; partial roots are quarantined, never reused."""


def require(value):
    if value is not True:
        raise LinuxPreparationError("native_linux_preparation_refused")


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def release_url(value):
    parsed = urllib.parse.urlsplit(value)
    require(
        parsed.scheme == "https"
        and parsed.hostname
        in {"github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}
    )
    require(parsed.port in (None, 443) and parsed.username is None and parsed.password is None)
    return value


class HTTPSReleaseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        release_url(newurl)
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def download(pin, target):
    require(not target.exists() and not target.is_symlink())
    release_url(pin["url"])
    # No inherited proxies or authorization, and redirects remain HTTPS release hosts.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), HTTPSReleaseRedirect())
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    total = 0
    with os.fdopen(fd, "wb") as output, opener.open(pin["url"], timeout=30) as response:
        release_url(response.geturl())
        require(response.status == 200)
        while block := response.read(1024 * 1024):
            total += len(block)
            require(total <= 128 * 1024**2)
            output.write(block)
    require(total > 0 and digest(target) == pin["sha256"])
    return total


def member_size_allowed(name, size, archive_sha256):
    # Measured official native-lock artifact, not a general raised extraction cap.
    if archive_sha256 == _PINS["python"]["sha256"] and name == "python/lib/libpython3.14.so.1.0":
        return type(size) is int and size == 136993528
    return type(size) is int and 0 <= size <= 128 * 1024**2


def extract_software(archive, destination, top, expected):
    """Extract an already hash-pinned upstream software archive with data_filter.

    Not an arbitrary-upload archive parser. Caller owns the fresh destination and
    archive exclusively. Reject special/sparse/hardlink members and outside links;
    retain only normal archive executable bits, never ownership/setuid metadata.
    """
    require(digest(archive) == expected and not destination.exists())
    destination.mkdir(mode=0o700)
    require(hasattr(tarfile, "data_filter"))
    with tarfile.open(archive, "r:gz") as stream:
        members = stream.getmembers()
        require(0 < len(members) <= 30000)
        total = 0
        seen = set()
        for item in members:
            parts = Path(item.name)
            require(not parts.is_absolute() and ".." not in parts.parts and parts.parts[0] == top)
            require("\\" not in item.name and len(item.name) <= 1024 and item.name not in seen)
            seen.add(item.name)
            require((item.isfile() or item.isdir() or item.issym()) and not item.issparse())
            require(member_size_allowed(item.name, item.size, expected))
            total += item.size
            require(total <= 1024**3)
            tarfile.data_filter(item, destination)
        # Built-in data filter is applied again at extraction, including realpath
        # link checks as earlier members materialize. No fully_trusted fallback.
        stream.extractall(destination, members=members, filter="data")
    for path in destination.rglob("*"):
        info = path.lstat()
        require(info.st_uid == os.geteuid())
        if path.is_symlink():
            require(path.resolve(strict=True).is_relative_to(destination))
        else:
            require(stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode))
            require(not info.st_mode & 0o7022)
    return destination / top


def expected_packages(requirements):
    rows = re.findall(r"^([A-Za-z0-9_.-]+)==([^\s;]+)", requirements, re.MULTILINE)
    result = {re.sub(r"[-_.]+", "-", name).lower(): version for name, version in rows}
    require(len(rows) == len(result) == 77)
    return result


def wheel_sync_arguments(uv, python, requirements):
    # uv0.13.5 makes --only-binary and --no-build mutually exclusive. The former
    # alone explicitly forbids source builds and is the stricter wheel-only contract.
    return [
        str(uv),
        "--no-config",
        "--no-python-downloads",
        "pip",
        "sync",
        "--python",
        str(python),
        "--require-hashes",
        "--only-binary",
        ":all:",
        "--link-mode",
        "copy",
        "--default-index",
        "https://pypi.org/simple",
        str(requirements),
    ]


def require_case_sensitive(root):
    """Observe actual fresh-root name/inode behavior for this Linux software bundle."""
    require(not any(root.iterdir()))
    owned = []
    try:
        for name, payload in ((".hmp-case-probe-a", b"a"), (".HMP-CASE-PROBE-A", b"b")):
            path = root / name
            try:
                fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            except FileExistsError:
                raise LinuxPreparationError("native_linux_preparation_refused") from None
            owned.append((path, fd))
            os.write(fd, payload)
        require(os.fstat(owned[0][1]).st_ino != os.fstat(owned[1][1]).st_ino)
        require(os.pread(owned[0][1], 1, 0) == b"a" and os.pread(owned[1][1], 1, 0) == b"b")
    finally:
        for path, fd in owned:
            os.close(fd)
            path.unlink()  # Only our exact fresh O_EXCL files under exclusive root custody.
    return True


def prepare(root, native_repository, hmp_repository):
    require(sys.platform == "linux" and os.uname().machine == "x86_64")
    require(sys.flags.isolated == 1 and sys.dont_write_bytecode and sys.flags.optimize == 0)
    require(os.geteuid() > 0 and root.is_absolute() and root.resolve(strict=True) == root)
    require(stat.S_IMODE(root.stat().st_mode) == 0o700 and root.stat().st_uid == os.geteuid())
    require(not any(root.iterdir()))
    os.umask(0o077)
    require_case_sensitive(root)
    controller = module("_linux_preparation_controller", "native_presentation_linux_controller.py")
    stage = module("_linux_preparation_sources", "native_presentation_source_stage.py")
    sources = root / "sources"
    sources.mkdir(mode=0o700)
    stage.stage_sources(sources, native_repository, hmp_repository)
    require(controller.verify_sources(sources) == 13201)
    lock = json.loads((sources / "native/pm/lock.json").read_text())["packages"]
    for name, pin in _PINS.items():
        require(lock[name]["version"] == pin["version"])
        require(lock[name]["artifacts"]["linux-x64"] == {k: pin[k] for k in ("sha256", "url")})
    receipt = {
        "stage": "sources-verified",
        "artifacts": _PINS,
        "nativeExecuted": False,
        "filesystemCaseSensitiveObserved": True,
        "providerSetupPerformed": False,
        "sharedToolsModified": False,
    }
    controller.save(root / "preparation-receipt.json", receipt)
    for name, pin in _PINS.items():
        receipt[name + "DownloadBytes"] = download(pin, root / (name + ".tar.gz"))
        controller.save(root / "preparation-receipt.json", receipt)
    prefix = extract_software(
        root / "python.tar.gz", root / "python-package", "python", _PINS["python"]["sha256"]
    )
    uvroot = extract_software(
        root / "uv.tar.gz",
        root / "uv-package",
        "uv-x86_64-unknown-linux-gnu",
        _PINS["uv"]["sha256"],
    )
    commands = stage._driver().commands  # Existing pre-owned, joining generic CLI helper only.
    command_root = root / "preparation-commands"
    command_root.mkdir(mode=0o700)
    cache = root / "uv-cache"
    cache.mkdir(mode=0o700)
    home = root / "tool-home"
    home.mkdir(mode=0o700)
    command_receipt = {"commands": []}
    clean = [
        "/usr/bin/env",
        "-i",
        "PATH=/usr/bin:/bin",
        "LANG=C.UTF-8",
        "LC_ALL=C.UTF-8",
        "HOME=" + str(home),
        "UV_CACHE_DIR=" + str(cache),
    ]

    def owned(arguments, role, timeout=12):
        return commands._owned(
            clean + arguments,
            command_root,
            role,
            command_receipt,
            stdout_limit=4 * 1024**2,
            wait_timeout=timeout,
        )

    python = prefix / "bin/python3.14"
    uv = uvroot / "uv"
    require(
        owned(
            [
                str(python),
                "-I",
                "-B",
                "-S",
                "-c",
                "import sys;print('.'.join(map(str,sys.version_info[:3])))",
            ],
            "python-version",
        ).strip()
        == b"3.14.9"
    )
    require(owned([str(uv), "--version"], "uv-version").startswith(b"uv 0.13.5 "))
    venv = root / "venv"
    owned(
        [
            str(uv),
            "--no-config",
            "--no-python-downloads",
            "venv",
            "--no-project",
            "--python",
            str(python),
            str(venv),
        ],
        "create-venv",
        60,
    )
    requirements = Path(__file__).with_name("native_presentation_linux.requirements.txt")
    require(digest(requirements) == _REQ_SHA)
    expected = expected_packages(requirements.read_text())
    owned(wheel_sync_arguments(uv, venv / "bin/python", requirements), "hash-only-wheels", 600)
    site = venv / "lib/python3.14/site-packages"
    query = (
        "import sys,os,json,importlib.metadata as m;print(json.dumps({"
        "'version':list(sys.version_info[:3]),'prefix':sys.prefix,'base':sys.base_prefix,"
        "'machine':os.uname().machine,'packages':[(d.metadata['Name'],d.version) "
        "for d in m.distributions(path=[sys.argv[1]])]}))"
    )
    raw = owned(
        [str(venv / "bin/python"), "-I", "-B", "-S", "-c", query, str(site)], "runtime-metadata"
    )
    observation = json.loads(raw)
    require(observation["version"] == [3, 14, 9] and observation["machine"] == "x86_64")
    require(observation["prefix"] == str(venv) and observation["base"] == str(prefix))
    packages = {
        re.sub(r"[-_.]+", "-", name).lower(): version for name, version in observation["packages"]
    }
    require(len(observation["packages"]) == 77 and packages == expected)
    permissions = module(
        "_linux_fresh_software_permissions", "native_presentation_linux_permissions.py"
    )
    permissions.harden(root, prefix, venv)
    runtime = {
        "schema": 2,
        "pythonVersion": observation["version"],
        "requirementsSHA256": _REQ_SHA,
        "prefix": str(prefix),
        "venv": str(venv),
        "files": controller.runtime_inventory(prefix, venv),
    }
    manifest = root / "runtime-manifest.json"
    controller.save(manifest, runtime)
    expected_hash = digest(manifest)
    controller.verify_runtime(prefix, venv, manifest, expected_hash)
    require(controller.verify_sources(sources) == 13201)
    output = root / "run"
    output.mkdir(mode=0o700)
    result = {
        "source": str(sources),
        "prefix": str(prefix),
        "venv": str(venv),
        "root": str(output),
        "runtimeManifest": str(manifest),
        "runtimeSHA256": expected_hash,
    }
    controller.save(root / "prepared.json", result)
    receipt.update(
        stage="prepared",
        runtimeManifestSHA256=expected_hash,
        packages=packages,
        interpreterSHA256=digest(python.resolve()),
        uvSHA256=digest(uv),
        explicitMetadataQueryUsesNoSite=True,
        nativeJourneyExecuted=False,
    )
    controller.save(root / "preparation-receipt.json", receipt)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ("root", "native-repository", "hmp-repository"):
        parser.add_argument("--" + argument, type=Path, required=True)
    args = parser.parse_args()
    prepare(args.root, args.native_repository, args.hmp_repository)
    print(
        json.dumps(
            {"stage": "prepared", "nativeJourneyExecuted": False, "sharedToolsModified": False}
        )
    )
