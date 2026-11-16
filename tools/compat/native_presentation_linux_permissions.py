"""Harden only fresh provenance-verified fixture software, never live/reused homes.

Caller owns the fresh root exclusively from empty creation through preparation,
all installers are joined, no software runs concurrently, and native admission
has not begun. This is preparation, not permission issuance or a runtime bypass.
A partial/unknown outcome quarantines the root permanently; never resume it.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path


class SoftwarePermissionError(RuntimeError):
    """Fixed public text; private context is encrypted by the CI wrapper."""

    def __init__(self, reason, relative=""):
        super().__init__("fixture_software_permission_refused")
        self.fixture_context = {"reason": reason, "relative": relative}


def require(value, reason, relative=""):
    if value is not True:
        raise SoftwarePermissionError(reason, relative)


def write_receipt(path, document):
    temporary = path.with_name(path.name + ".pending")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as output:
        json.dump(document, output, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(parent)
        require(
            stat.S_ISDIR(info.st_mode)
            and info.st_uid == os.geteuid()
            and stat.S_IMODE(info.st_mode) == 0o700,
            "receipt-parent",
        )
        os.fsync(parent)
    finally:
        os.close(parent)


def fd_hash(fd):
    digest, offset = hashlib.sha256(), 0
    while block := os.pread(fd, 1024 * 1024, offset):
        offset += len(block)
        require(offset <= 256 * 1024**2, "file-size-bound")
        digest.update(block)
    return digest.hexdigest()


def identity(info):
    return (info.st_dev, info.st_ino, info.st_uid, stat.S_IFMT(info.st_mode), info.st_nlink)


def opened(path, expected, directory):
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    if directory:
        flags |= os.O_DIRECTORY
    fd = os.open(path, flags)
    try:
        observed = os.fstat(fd)
        require(identity(observed) == identity(expected), "opened-identity", str(path.name))
        require(
            stat.S_IMODE(observed.st_mode) == stat.S_IMODE(expected.st_mode),
            "opened-mode",
            str(path.name),
        )
        return fd
    except BaseException:
        os.close(fd)
        raise


def harden(root, prefix, venv):
    require(
        type(root) is type(Path()) and root.is_absolute() and root.resolve(strict=True) == root,
        "root",
    )
    info = root.lstat()
    require(
        stat.S_ISDIR(info.st_mode)
        and info.st_uid == os.geteuid()
        and stat.S_IMODE(info.st_mode) == 0o700,
        "root-owner-mode",
    )
    require(
        prefix == root / "python-package/python" and venv == root / "venv",
        "fixed-fresh-software-paths",
    )
    destination = root / "permission-normalization.json"
    require(
        not destination.exists()
        and not destination.is_symlink()
        and not destination.with_name(destination.name + ".pending").exists(),
        "normalization-replay",
    )
    receipt = {
        "stage": "inventory",
        "offenders": [],
        "changes": [],
        "retryAllowed": False,
        "nativeAdmission": False,
        "completeOffenderInventory": False,
    }
    write_receipt(destination, receipt)
    targets = []
    try:
        count = 0
        for label, base in (("prefix", prefix), ("venv", venv)):
            require(base.resolve(strict=True) == base and base.is_dir(), "software-root", label)
            for path in [base, *sorted(base.rglob("*"))]:
                count += 1
                relative = label + "/" + path.relative_to(base).as_posix()
                require(count <= 100000, "inventory-size", relative)
                observed = path.lstat()
                require(observed.st_uid == os.geteuid(), "owner", relative)
                if stat.S_ISLNK(observed.st_mode):
                    resolved = path.resolve(strict=True)
                    require(
                        resolved.is_relative_to(prefix) or resolved.is_relative_to(venv),
                        "outside-link",
                        relative,
                    )
                    continue  # Never follow/chmod a symlink, including Linux0777 links.
                directory = stat.S_ISDIR(observed.st_mode)
                require(directory or stat.S_ISREG(observed.st_mode), "special-file", relative)
                require(not observed.st_mode & 0o7000, "setid-or-sticky", relative)
                require(directory or observed.st_nlink == 1, "hardlink", relative)
                old_mode = stat.S_IMODE(observed.st_mode)
                if not old_mode & 0o022:
                    continue
                item = {
                    "relative": relative,
                    "device": observed.st_dev,
                    "inode": observed.st_ino,
                    "uid": observed.st_uid,
                    "type": "directory" if directory else "file",
                    "beforeMode": old_mode,
                    "afterMode": old_mode & ~0o022,
                }
                fd = opened(path, observed, directory)
                try:
                    if not directory:
                        item["sha256"] = fd_hash(fd)
                        require(
                            os.fstat(fd).st_size == observed.st_size,
                            "inventory-size-change",
                            relative,
                        )
                finally:
                    os.close(fd)
                receipt["offenders"].append(item)
                targets.append((path, observed, directory, item))
        # No permission effect before the COMPLETE offender inventory is durable.
        receipt.update(
            stage="inventory-complete", completeOffenderInventory=True, inspectedEntries=count
        )
        write_receipt(destination, receipt)
        for path, before, directory, item in targets:
            receipt.update(stage="hardening", pendingRelative=item["relative"])
            write_receipt(destination, receipt)
            fd = opened(path, before, directory)
            try:
                if not directory:
                    require(fd_hash(fd) == item["sha256"], "before-byte-change", item["relative"])
                os.fchmod(fd, item["afterMode"])
                after = os.fstat(fd)
                require(identity(after) == identity(before), "after-identity", item["relative"])
                require(
                    stat.S_IMODE(after.st_mode) == item["afterMode"], "after-mode", item["relative"]
                )
                if not directory:
                    require(
                        fd_hash(fd) == item["sha256"] and after.st_size == before.st_size,
                        "after-byte-change",
                        item["relative"],
                    )
            finally:
                os.close(fd)
            changed = dict(item)
            if not directory:
                changed["unchangedBytes"] = True
            receipt["changes"].append(changed)
            receipt.pop("pendingRelative", None)
            write_receipt(destination, receipt)
        receipt.update(stage="complete", inspectedEntries=count)
        write_receipt(destination, receipt)
        return receipt
    except BaseException as exc:
        receipt.update(stage="quarantined", failureType=type(exc).__name__, retryAllowed=False)
        try:
            write_receipt(destination, receipt)
        except OSError:
            receipt["diagnosticWriteFailed"] = True
        raise
