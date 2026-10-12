"""Isolated pinned-parser source checks; no transport or runtime qualification.

This driver is deliberately separate from the pytest collector. Its inert
socket slot never replaces a module belonging to another collected test.
The selected CPython 3.14.6 source AST is not the host stdlib HTTP parser.
"""

import ast
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import sys
import types
import unittest
from pathlib import Path


class SourceFixtureLoader(importlib.machinery.SourceFileLoader):
    """Evaluate only hash-pinned source fixture definitions through a loader."""

    def __init__(self, name, path, digest, selection):
        super().__init__(name, str(path))
        self.digest = digest
        self.selection = selection

    def get_code(self, fullname):
        assert fullname == self.name
        raw = self.get_data(self.path)
        assert len(raw) <= 65536
        assert hashlib.sha256(raw).hexdigest() == self.digest
        tree = ast.parse(raw, filename=self.path)
        nodes = []
        for node in tree.body:
            if self.selection == "parser":
                if isinstance(node, ast.Import):
                    assert all(alias.name != "ssl" for alias in node.names)
                    if not any(alias.name == "socket" for alias in node.names):
                        nodes.append(node)
                elif isinstance(node, ast.ClassDef):
                    if node.name != "HTTPConnection":
                        nodes.append(node)
                elif isinstance(node, ast.FunctionDef):
                    if node.name in ("_read_headers", "_parse_header_lines", "parse_headers"):
                        nodes.append(node)
                elif isinstance(node, (ast.Assign, ast.Expr)):
                    nodes.append(node)
            elif isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                nodes.append(node)
        selected = ast.Module(body=nodes, type_ignores=[])
        return compile(selected, self.path, "exec")


def source_module(name, path, digest, selection, namespace):
    loader = SourceFixtureLoader(name, path, digest, selection)
    spec = importlib.util.spec_from_loader(name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    module.__dict__.update(namespace)
    # This loader compiles only selected pinned fixture AST, without a pyc path.
    # No module registry insertion or replacement is required for these classes.
    loader.exec_module(module)
    return module


def source_checks():
    assert "socket" not in sys.modules and "ssl" not in sys.modules
    sys.modules["socket"] = types.ModuleType("socket")
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    import native_media_rp03_bounded as bounded

    assert Path(bounded.__file__).resolve() == here / "native_media_rp03_bounded.py"
    fixtures = here / "tests" / "rp03_source_fixtures"
    assert (
        hashlib.sha256((fixtures / "LICENSE.cpython-3.14.6.txt").read_bytes()).hexdigest()
        == "b0e25a78cffb43f4d92de8b61ccfa1f1f98ecbc22330b54b5251e7b6ba010231"
    )
    parser = source_module(
        "_hmp_rp03_tagged_parser_source",
        fixtures / "cpython3146_http_client.source",
        "3fb2bf964bf8553a404bffdc47d2483832fb402128021bab650c452fc5b41bbb",
        "parser",
        {},
    )
    assert "HTTPConnection" not in vars(parser) and "HTTPSConnection" not in vars(parser)
    namespace = {
        "AdapterSocket": bounded.AdapterSocket,
        "BoundedFile": bounded.BoundedFile,
        "CLEAN_EOF": bounded.CLEAN_EOF,
        "Refused": bounded.Refused,
        "Strict": bounded.strict_response_type(parser),
        "http": parser,
        "unittest": unittest,
    }
    legacy = source_module(
        "_hmp_rp03_legacy_source_cases",
        fixtures / "legacy_cases.source",
        "bc356d97805c05dcf45dacd1e81681bf6354eb8948bca66f00f956e76bfb5749",
        "cases",
        namespace,
    )
    stream = io.StringIO()
    first = unittest.TextTestRunner(stream=stream, verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(legacy.Checks)
    )
    assert first.wasSuccessful(), stream.getvalue()
    assert first.testsRun == 42
    namespace.update(
        {
            "Port": legacy.Port,
            "Ledger": legacy.Ledger,
            "CAUSALS": [],
        }
    )
    authority = source_module(
        "_hmp_rp03_authority_source_cases",
        fixtures / "authority_cases.source",
        "dabceadc5e1610aa4ff57b9813d3d24bf700f896e666209576dabac82178f8fc",
        "cases",
        namespace,
    )
    stream = io.StringIO()
    second = unittest.TextTestRunner(stream=stream, verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(authority.AuthorityChecks)
    )
    assert second.wasSuccessful(), stream.getvalue()
    assert second.testsRun == 14 and len(authority.CAUSALS) == 206
    assert "ssl" not in sys.modules
    assert sys.modules["socket"].__spec__ is None
    return {
        "legacyMethods": first.testsRun,
        "authorityMethods": second.testsRun,
        "authorityCausalRows": len(authority.CAUSALS),
        "sourceOnly": True,
        "runtimeQualified": False,
        "parserTag": "CPython3.14.6 selected source AST",
        "hostParserEquivalent": False,
        "legacyReplayIsAuthorityEvidence": False,
    }


if __name__ == "__main__":
    print(json.dumps(source_checks(), sort_keys=True))
