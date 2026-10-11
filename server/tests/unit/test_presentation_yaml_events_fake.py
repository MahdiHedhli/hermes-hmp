"""In-memory event causals; no YAML provider or profile file is imported."""

from __future__ import annotations

import unittest

from hmp_plugin import presentation_yaml as reducer


def event(kind, value=None, style=None, **kwargs):
    return reducer.YamlEvent(kind, value, style, **kwargs)


def document(body):
    return [
        event("stream_start"),
        event("document_start"),
        event("mapping_start"),
        *body,
        event("mapping_end"),
        event("document_end"),
        event("stream_end"),
    ]


def scalar(value, style="plain"):
    return event("scalar", value, style)


def fields_body():
    return [
        scalar("display_name"),
        scalar("Ada"),
        scalar("ui_meta"),
        event("mapping_start"),
        scalar("hermes-bots"),
        event("mapping_start"),
        scalar("title"),
        scalar("River"),
        scalar("shape"),
        scalar("squircle"),
        scalar("color"),
        scalar("#8b5cf6"),
        scalar("custom"),
        scalar("true"),
        event("mapping_end"),
        event("mapping_end"),
    ]


class PresentationYamlEventTests(unittest.TestCase):
    def reduce(self, events, raw=b"synthetic: bounded\n", clock=lambda: 1.0):
        return reducer.reduce_presentation_events(raw, events, clock=clock, deadline=3.0)

    def refused(self, events, label, raw=b"synthetic: bounded\n", clock=lambda: 1.0):
        with self.assertRaises(reducer.PresentationYamlError) as caught:
            self.reduce(events, raw, clock)
        self.assertEqual(caught.exception.label, label)
        self.assertNotIn("synthetic", str(caught.exception))

    def test_closed_projection_and_quoted_boolean(self):
        row = self.reduce(document(fields_body()))
        self.assertEqual(
            row,
            reducer.RawPresentationFields("Ada", "River", "squircle", "#8b5cf6", True),
        )
        body = fields_body()
        body[-3] = scalar("false", "double")
        self.refused(document(body), "SELECTED_TYPE")

    def test_unknown_private_branch_is_validated_but_not_returned(self):
        body = [
            *fields_body(),
            scalar("private_prompt"),
            event("sequence_start"),
            scalar("never send"),
            event("sequence_end"),
        ]
        row = self.reduce(document(body))
        self.assertEqual(row.title, "River")
        self.assertNotIn("never send", repr(row))

    def test_absent_and_null_custom(self):
        row = self.reduce(document([scalar("display_name"), scalar("Ada")]))
        self.assertIsNone(row.custom)
        body = fields_body()
        body[-3] = scalar("null")
        self.assertIsNone(self.reduce(document(body)).custom)

    def test_duplicate_selected_and_unknown_keys(self):
        for key in ("display_name", "private_prompt"):
            body = [scalar(key), scalar("first"), scalar(key), scalar("second")]
            with self.subTest(key=key):
                self.refused(document(body), "MAPPING_KEY")

    def test_alias_anchor_tag_and_directive_are_closed(self):
        for modified in (
            event("alias"),
            event("scalar", "Ada", "plain", anchor="a"),
            event("scalar", "Ada", "plain", tag="!private"),
            event("document_start", directives=("%TAG",)),
        ):
            with self.subTest(modified=modified):
                if modified.kind == "document_start":
                    source = document([])
                    source[1] = modified
                else:
                    source = document([scalar("display_name"), modified])
                self.refused(
                    source,
                    "DOCUMENT_GRAMMAR" if modified.kind == "alias" else "YAML_FEATURE",
                )

    def test_merge_and_complex_mapping_keys_refuse(self):
        self.refused(document([scalar("<<"), scalar("private")]), "MAPPING_KEY")
        self.refused(document([event("sequence_start")]), "MAPPING_GRAMMAR")

    def test_selected_parent_and_leaf_types_are_closed(self):
        self.refused(document([scalar("ui_meta"), scalar("text")]), "SELECTED_TYPE")
        self.refused(
            document([scalar("display_name"), event("mapping_start"), event("mapping_end")]),
            "SELECTED_TYPE",
        )
        self.refused(document([scalar("display_name"), scalar("yes")]), "SELECTED_TYPE")
        self.refused(document([scalar("display_name"), scalar("01")]), "SELECTED_TYPE")
        self.refused(document([scalar("display_name"), scalar("2026-10-11")]), "SELECTED_TYPE")

    def test_yaml_1_1_plain_date_time_and_timezone_forms_refuse(self):
        for value in (
            "2001-12-15",
            "2001-12-15T02:59:43.1Z",
            "2001-12-14t21:59:43.10-05:00",
            "2001-12-14 21:59:43.10 -5",
            "2001-12-15 2:59:43.10",
            "2001-12-15t02:59:43Z",
            "2001-12-15 02:59:43",
            "2001-12-15T02:59:43+05:30",
            "2001-12-15T02:59:43-5",
            "2001-1-5T2:59:43Z",
        ):
            with self.subTest(value=value):
                self.refused(
                    document([scalar("display_name"), scalar(value)]),
                    "SELECTED_TYPE",
                )
        quoted = "2001-12-15T02:59:43.1Z"
        self.assertEqual(
            self.reduce(document([scalar("display_name"), scalar(quoted, "double")])).display_name,
            quoted,
        )
        self.assertIsNone(
            self.reduce(document([scalar("private_timestamp"), scalar(quoted)])).display_name
        )

    def test_document_and_container_grammar(self):
        self.refused(document([])[:-1], "DOCUMENT_INCOMPLETE")
        self.refused([*document([]), event("stream_start")], "DOCUMENT_GRAMMAR")
        self.refused(document([event("sequence_end")]), "CONTAINER_GRAMMAR")
        self.refused(
            [event("stream_start"), event("document_start"), event("sequence_start")],
            "ROOT_SCHEMA",
        )
        self.refused(document([scalar("display_name")]), "MAPPING_GRAMMAR")

    def test_raw_size_utf8_bom_and_nul(self):
        good = document([])
        for raw, label in (
            (b"", "RAW_SIZE"),
            (b"x" * (reducer.RAW_LIMIT + 1), "RAW_SIZE"),
            (b"\xff", "RAW_UTF8"),
            (b"a\x00b", "RAW_UTF8"),
            (b"\xef\xbb\xbf\xef\xbb\xbfX", "RAW_UTF8"),
        ):
            with self.subTest(raw=raw[:8]):
                self.refused(good, label, raw)
        self.assertIsNone(self.reduce(good, b"\xef\xbb\xbfX").display_name)

    def test_scalar_nodes_depth_events_and_deadline(self):
        self.refused(document([scalar("x"), scalar("a" * 1025)]), "SCALAR_LIMIT")
        many = [scalar(str(i), "double") for i in range(129)]
        self.refused(document([*many, *many]), "NODE_LIMIT")
        nested = [scalar("x"), *[event("sequence_start") for _ in range(8)]]
        self.refused(document(nested), "STRUCTURE_LIMIT")
        self.refused(document([]), "DEADLINE", clock=lambda: 4.0)

    def test_bounded_iterator_failure_and_extra_stream(self):
        def bad_iterator():
            yield event("stream_start")
            raise OSError("private payload")

        self.refused(bad_iterator(), "EVENT_ADVANCE")
        self.refused([event("stream_start")] * (reducer.EVENT_LIMIT + 1), "DOCUMENT_GRAMMAR")

    def test_event_schema_unicode_byte_bound_and_clock_error(self):
        self.refused([event("x" * 33)], "EVENT_SCHEMA")
        self.refused(
            document([scalar("display_name"), scalar("é" * 600)]),
            "SCALAR_LIMIT",
        )

        def bad_clock():
            raise OSError("private clock payload")

        self.refused(document([]), "CLOCK", clock=bad_clock)


if __name__ == "__main__":
    unittest.main()
