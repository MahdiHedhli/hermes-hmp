"""Source-only RBH-03 inventory; never import or execute inspected HMP code.

This is review evidence, not a complete call graph, purity proof or runtime gate.
Both branches of conditional calls appear, including branches not taken by the
retained-only path. Attribute dispatch and exception constructors need review.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import symtable


TARGETS = {
    "hmp_plugin/presentation_gateway_package.py": (
        "GatewayPackageOwner._retained_binding", "_require", "PackageInventoryError.__init__"),
    "hmp_plugin/presentation_gateway_recipe.py": (
        "GatewayRecipeOwner._retained_binding", "_require", "_same_recipe_binding",
        "GatewayRecipeError.__init__"),
    "hmp_plugin/presentation_startup_selection.py": (
        "StartupSelectionOwner._retained_binding", "_approved_recipe",
        "_approval_binding", "_require", "SelectionLoadError.__init__"),
    "hmp_startup/gateway_approval.py": (
        "GatewayApprovalOwner._retained_binding", "GatewayApprovalOwner._seal",
        "GatewayApprovalOwner._closed_custody", "_api_state", "_same_entry", "_require",
        "GatewayApprovalError.__init__"),
    "hmp_startup/gateway_entry.py": (
        "GatewayEntryOwner._retained_binding", "_native_file_ledger_shape", "_require",
        "GatewayEntryError.__init__"),
    "hmp_plugin/presentation_gateway_activation.py": (
        "GatewayActivationOwner._retained_scope", "_require", "ActivationCaptureError.__init__"),
    "hmp_plugin/presentation_startup_artifacts.py": (
        "_expected", "_descriptor_closed_in_scope", "_native_descriptor_closed",
        "_native_descriptor_opened", "_native_file_allocation_original", "_require",
        "ArtifactObservationError.__init__"),
}


def _definition(tree, symbols, qualified):
    """Resolve exact lexical definitions without evaluating a module or class."""
    for name in qualified.split("."):
        nodes = [node for node in tree.body
                 if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                 and node.name == name]
        if len(nodes) != 1:
            raise ValueError(f"expected one definition: {qualified}")
        tree = nodes[0]
        children = [child for child in symbols.get_children()
                    if child.get_name() == name and child.get_lineno() == tree.lineno]
        if len(children) != 1:
            raise ValueError(f"expected one symbol table: {qualified}")
        symbols = children[0]
    if not isinstance(tree, (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise ValueError(f"expected a function: {qualified}")
    return tree, symbols


def _global_reads(table):
    reads = {symbol.get_name() for symbol in table.get_symbols()
             if symbol.is_global() and symbol.is_referenced()}
    for child in table.get_children():
        reads.update(_global_reads(child))
    return reads


def census(root):
    rows = []
    for relative, targets in TARGETS.items():
        path = root / "server" / relative
        raw = path.read_bytes()
        source = raw.decode("utf-8")
        tree = ast.parse(source, filename=relative)
        symbols = symtable.symtable(source, relative, "exec")
        functions = []
        for qualified in targets:
            node, table = _definition(tree, symbols, qualified)
            functions.append({
                "name": qualified, "line": node.lineno, "end_line": node.end_lineno,
                "global_reads": sorted(_global_reads(table)),
                "call_expressions": sorted({ast.unparse(part.func)
                                            for part in ast.walk(node)
                                            if isinstance(part, ast.Call)}),
                "local_imports": sorted({ast.unparse(part) for part in ast.walk(node)
                                         if isinstance(part, (ast.Import, ast.ImportFrom))}),
                "nonlocal_store_expressions": sorted({ast.unparse(part)
                    for part in ast.walk(node)
                    if isinstance(part, (ast.Attribute, ast.Subscript))
                    and isinstance(part.ctx, (ast.Store, ast.Del))}),
            })
        rows.append({"path": "server/" + relative,
                     "sha256": hashlib.sha256(raw).hexdigest(),
                     "functions": functions})
    return {"schema": 1, "kind": "source-only-review-inventory",
            "target_code_executed": False, "transitive_closure_proven": False,
            "runtime_provenance_proven": False, "modules": rows}


if __name__ == "__main__":
    print(json.dumps(census(Path(__file__).resolve().parents[2]), indent=2, sort_keys=True))
