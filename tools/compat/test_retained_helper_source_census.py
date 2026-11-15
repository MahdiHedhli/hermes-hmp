"""Offline census causals; no HMP imports or host/runtime access."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "retained_source_census", Path(__file__).with_name("retained_helper_source_census.py"))
census_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(census_module)


class SourceCensusTests(unittest.TestCase):
    def inventory(self, source, name="Owner.retained"):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "server" / "fixture.py"
            path.parent.mkdir()
            path.write_bytes(source.encode("utf-8"))
            with patch.object(census_module, "TARGETS", {"fixture.py": (name,)}):
                return census_module.census(root)

    def test_inspection_does_not_execute_top_level_or_function_body(self):
        source = ('raise RuntimeError("must never execute")\n'
                  'class Owner:\n'
                  '    def retained(self):\n'
                  '        raise RuntimeError("must never dispatch")\n')
        result = self.inventory(source)
        self.assertFalse(result["target_code_executed"])
        self.assertFalse(result["transitive_closure_proven"])
        self.assertEqual(result["modules"][0]["sha256"],
                         hashlib.sha256(source.encode()).hexdigest())

    def test_nested_comprehension_globals_and_local_import_are_distinct(self):
        result = self.inventory('class Owner:\n'
            '    def retained(self, rows):\n'
            '        from fixture_provider import Local\n'
            '        return [Remote.check(row) for row in rows if Local.accept(row)]\n')
        row = result["modules"][0]["functions"][0]
        self.assertIn("Remote", row["global_reads"])
        self.assertNotIn("rows", row["global_reads"])
        self.assertNotIn("row", row["global_reads"])
        self.assertNotIn("Local", row["global_reads"])
        self.assertEqual(row["local_imports"], ["from fixture_provider import Local"])
        self.assertIn("Local.accept", row["call_expressions"])

    def test_both_conditional_calls_and_nonlocal_stores_remain_visible(self):
        result = self.inventory('class Owner:\n'
            '    def retained(self, live):\n'
            '        self.state[0] = True\n'
            '        return current() if live else retained()\n')
        row = result["modules"][0]["functions"][0]
        self.assertEqual(row["call_expressions"], ["current", "retained"])
        self.assertEqual(row["nonlocal_store_expressions"], ["self.state[0]"])

    def test_missing_or_ambiguous_definition_refuses_instead_of_partial_report(self):
        for source in ('class Owner:\n    pass\n',
                       'class Owner:\n    def retained(self): pass\n'
                       '    def retained(self): pass\n'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.inventory(source)


if __name__ == "__main__":
    unittest.main()
