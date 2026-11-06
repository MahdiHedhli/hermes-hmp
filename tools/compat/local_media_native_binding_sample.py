"""C6b native fixture preparation; inert import, no provider or live-home discovery.

Only an explicitly supplied scratch SessionDB is mutated. Generated image paths
are synthetic tool-result fields, never opened or materialized by this module.
This preparation alone is not a timing, allocation or concurrent-writer result.
"""

PROMPT_CHARS = 262144
HISTORY_PAIRS = 128
SHAPES = ((2, 0), (2, PROMPT_CHARS), (98, 0), (98, PROMPT_CHARS))
KINDS = ("bot_chat", "phone")
SELECTORS = (1, 16, 128)


def require(ok):
    if not ok:
        raise RuntimeError("native_media_binding_sample_refused")


def validate_shape(kind, lineage_count, prompt_chars, home):
    require(type(kind) is str and kind in KINDS and
            type(lineage_count) is int and type(prompt_chars) is int and
            (lineage_count, prompt_chars) in SHAPES)
    require(type(home) is str and 1 < len(home) <= 3800 and home.startswith("/") and
            not home.endswith("/") and "\0" not in home and "//" not in home and
            all(part not in (".", "..") for part in home.split("/")))


def select_tool_ids(tool_ids, count):
    require(type(count) is int and count in SELECTORS and type(tool_ids) is tuple and
            len(tool_ids) == HISTORY_PAIRS and
            all(type(value) is int and value > 0 for value in tool_ids) and
            tuple(sorted(set(tool_ids))) == tool_ids)
    return tuple(reversed(tool_ids[-count:]))


def bound_modules(bound):
    """Use the listener's actual `(bridge cache, reads cache)` snapshot shape."""
    from types import ModuleType

    require(type(bound) is tuple and len(bound) == 2)
    chain, reads = bound
    require(type(chain) is tuple and len(chain) == 7 and type(reads) is tuple and len(reads) == 1
            and all(type(member) is ModuleType for member in (*chain, *reads))
            and reads[0] is chain[0])
    return chain[0], chain[6]


def seed_native_shape(db, *, home, kind, lineage_count, prompt_chars):
    """Use public native APIs and verify real prompt/lineage/history fields.

    Caller owns a disposable DB/profile and its lifecycle. Every fixed session id
    must be absent before the first write; no existing session is overwritten.
    All sizes/shapes are refused before the first native call.
    """
    import hashlib
    import json

    validate_shape(kind, lineage_count, prompt_chars, home)
    prefix = f"synthetic-c6b-{kind}-{lineage_count}-{prompt_chars}"
    ids = tuple(f"{prefix}-{index:03}" for index in range(lineage_count))
    require(all(db.get_session(sid) is None for sid in ids))
    expected_prompts = {}
    for index, sid in enumerate(ids):
        prompt = None
        if prompt_chars:
            marker = f"SYNTHETIC_BINDING_COST_PROMPT_ONLY:{sid}:"
            prompt = marker + "p" * (prompt_chars - len(marker))
            expected_prompts[sid] = hashlib.sha256(prompt.encode("ascii")).hexdigest()
        if index:
            db.end_session(ids[index - 1], "compression")
        require(db.create_session(sid, "api_server", parent_session_id=ids[index - 1] if index
                                 else None, system_prompt=prompt) == sid)
    if kind == "bot_chat":
        require(db.set_session_hidden(ids[0], True) is True)
        require(db.set_session_title(ids[-1], "Bot Chat") is True)

    require(tuple(db.get_compression_lineage(ids[0])) == ids and
            db.resolve_resume_session_id(ids[0]) == ids[-1])
    verified_prompts = []
    for index, sid in enumerate(ids):
        row = db.get_session(sid)
        require(type(row) is dict and row.get("id") == sid and
                row.get("parent_session_id") == (ids[index - 1] if index else None))
        prompt = row.get("system_prompt")
        if prompt_chars:
            require(type(prompt) is str and len(prompt) == prompt_chars)
            digest = hashlib.sha256(prompt.encode("ascii")).hexdigest()
            require(digest == expected_prompts[sid])
            verified_prompts.append(digest)
        else:
            require(prompt is None or prompt == "")
    require(len(set(verified_prompts)) == (lineage_count if prompt_chars else 0))

    tip = ids[-1]
    db.append_message(tip, "user", content="SYNTHETIC_BINDING_COST_HISTORY_ONLY")
    tool_ids = []
    for index in range(HISTORY_PAIRS):
        call_id = f"synthetic-c6b-image-{index:03}"
        db.append_message(tip, "assistant", tool_calls=[{"id": call_id, "type": "function",
            "function": {"name": "image_generate", "arguments": "{}"}}])
        layout = "cache/images" if index % 2 == 0 else "cache/generated/images"
        path = f"{home}/{layout}/synthetic-c6b-{index:03}.png"
        row_id = db.append_message(tip, "tool", tool_name="image_generate", tool_call_id=call_id,
            content=json.dumps({"success": True, "image": path}, separators=(",", ":")))
        require(type(row_id) is int and row_id > 0)
        tool_ids.append(row_id)
    db.append_message(tip, "assistant", content="SYNTHETIC_BINDING_COST_END_ONLY")
    require(db.resolve_resume_session_id(ids[0]) == tip)
    rows = db.get_messages(tip, limit=1000)
    require(type(rows) is list and len(rows) == 2 * HISTORY_PAIRS + 2 and
            tuple(row["id"] for row in rows if row.get("role") == "tool") == tuple(tool_ids))
    require(len(set(tool_ids)) == HISTORY_PAIRS and tool_ids == sorted(tool_ids))
    return {"kind": kind, "lineage_count": lineage_count, "prompt_chars": prompt_chars,
        "verified_prompt_count": len(verified_prompts), "root": ids[0], "tip": tip,
        "tool_ids": tuple(tool_ids), "history_rows": len(rows),
        "legacy_rows": HISTORY_PAIRS // 2, "generated_rows": HISTORY_PAIRS // 2}


def validate_preparation_report(report, cost_case=None):
    validate_cost_case(cost_case)
    shapes = SHAPES if cost_case is None else (SHAPES[cost_case % len(SHAPES)],)
    require(type(report) is dict and set(report) == {"cells", "timing_measured",
        "allocation_measured", "writer_cases_run", "databases_closed"} and
        type(report["databases_closed"]) is int and report["databases_closed"] == len(shapes) and
        report["timing_measured"] is False and
        report["allocation_measured"] is False and type(report["writer_cases_run"]) is int and
        report["writer_cases_run"] == 0 and type(report["cells"]) is list and
        len(report["cells"]) == len(KINDS) * len(shapes))
    expected = [(kind, lineage, prompt) for kind in KINDS for lineage, prompt in shapes]
    for cell, shape in zip(report["cells"], expected, strict=True):
        require(type(cell) is dict and set(cell) == {"kind", "lineage_count", "prompt_chars",
            "verified_prompt_count", "history_rows", "legacy_rows", "generated_rows",
            "selector_counts", "accepted_counts", "proof_contexts",
            "verified_database_prompt_count", "verified_unprompted_extras"})
        require(type(cell["kind"]) is str and
                all(type(cell[key]) is int for key in ("lineage_count", "prompt_chars",
                    "verified_prompt_count", "history_rows", "legacy_rows", "generated_rows",
                    "proof_contexts", "verified_database_prompt_count",
                    "verified_unprompted_extras")))
        require((cell["kind"], cell["lineage_count"], cell["prompt_chars"]) == shape and
                cell["verified_prompt_count"] == (shape[1] if shape[2] else 0) and
                cell["history_rows"] == 258 and cell["legacy_rows"] == cell["generated_rows"] == 64
                and cell["proof_contexts"] == 2 and cell["verified_unprompted_extras"] == 1 and
                cell["verified_database_prompt_count"] == (2 * shape[1] if shape[2] else 0))
        for key in ("selector_counts", "accepted_counts"):
            require(type(cell[key]) is list and all(type(value) is int for value in cell[key])
                    and cell[key] == list(SELECTORS))



def validate_cost_case(case):
    require(case is None or (type(case) is int and 0 <= case < len(KINDS) * len(SHAPES)))


def validate_cost_mode(case, selector):
    validate_cost_case(case)
    require((case is None and selector is None) or
            (case is not None and type(selector) is int and selector in SELECTORS))


def measure_binding(bind, check):
    """One warmup, three untraced timings, then one separate Python trace.

    Only the complete binding call is timed/traced. Candidate construction and
    result validation are outside that interval. This excludes native C memory,
    RSS, mint cost and concurrent writers; no latency admission threshold follows.
    An existing trace is refused, never reset or stopped by this helper.
    """
    import gc
    import time
    import tracemalloc

    require(callable(bind) and callable(check) and not tracemalloc.is_tracing())
    check(bind())
    durations = []
    for _ in range(3):
        start = time.perf_counter_ns()
        result = bind()
        duration = time.perf_counter_ns() - start
        check(result)
        require(type(duration) is int and duration >= 0)
        durations.append(duration)
        del result
    gc.collect()
    require(not tracemalloc.is_tracing())
    tracemalloc.start()
    try:
        baseline, _ = tracemalloc.get_traced_memory()
        result = bind()
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    check(result)
    del result
    require(peak >= current >= baseline)
    return {"durations_ns": durations, "peak_traced_bytes": peak - baseline,
            "current_traced_bytes": current - baseline}


def validate_cost_report(report, case, selector):
    validate_cost_mode(case, selector)
    require(case is not None and type(report) is dict and set(report) == {
        "case", "kind", "lineage_count", "prompt_chars", "selectors", "warmups_per_selector",
        "traces_per_selector", "rss_measured", "mint_measured", "writer_cases_run"})
    kind, (lineage, prompt) = KINDS[case // len(SHAPES)], SHAPES[case % len(SHAPES)]
    require(type(report["case"]) is int and report["case"] == case and
            report["kind"] == kind and type(report["lineage_count"]) is int and
            report["lineage_count"] == lineage and type(report["prompt_chars"]) is int and
            report["prompt_chars"] == prompt and
            type(report["warmups_per_selector"]) is int and report["warmups_per_selector"] == 1 and
            type(report["traces_per_selector"]) is int and report["traces_per_selector"] == 1 and
            report["rss_measured"] is False and report["mint_measured"] is False and
            type(report["writer_cases_run"]) is int and report["writer_cases_run"] == 0 and
            type(report["selectors"]) is list and len(report["selectors"]) == 1)
    for row, count in zip(report["selectors"], (selector,), strict=True):
        require(type(row) is dict and set(row) == {"count", "durations_ns",
            "peak_traced_bytes", "current_traced_bytes"} and type(row["count"]) is int and
            row["count"] == count and type(row["durations_ns"]) is list and
            len(row["durations_ns"]) == 3 and
            all(type(value) is int and value >= 0 for value in row["durations_ns"]) and
            type(row["peak_traced_bytes"]) is int and type(row["current_traced_bytes"]) is int and
            row["peak_traced_bytes"] >= row["current_traced_bytes"] >= 0)

def run_preparation(fx, open_cell, *, user, profile, chat, cost_case=None,
                    cost_selector=None, cost_results=None):
    """Verify the full matrix, or both contexts of one explicitly selected cost shape.

    Each lineage/prompt shape owns a fresh native DB with BOTH proof sources:
    canonical Bot Chat identity is never renamed/cleared, and the Phone case
    cannot avoid a full contrary Bot Chat proof by omitting the canonical chat.
    Synthetic routing-store changes stay inside this fixture.
    No current default model/provider/grant is changed.
    """
    from hmp_plugin.contract import ConversationRef

    validate_cost_mode(cost_case, cost_selector)
    require((cost_case is None and cost_results is None) or
            (cost_case is not None and type(cost_results) is list and not cost_results))
    cost_rows = []
    sidecar, binding = bound_modules(fx.rig.ctx.media_modules)
    cells = {}
    selected_shapes = [(index, shape) for index, shape in enumerate(SHAPES)
                       if cost_case is None or index == cost_case % len(SHAPES)]
    for index, (lineage, prompt) in selected_shapes:
        with open_cell(index) as db:
            shapes = {kind: seed_native_shape(db, home=str(fx.native.home_path), kind=kind,
                      lineage_count=lineage, prompt_chars=prompt) for kind in KINDS}
            extra = f"synthetic-c6b-unprompted-extra-{lineage}-{prompt}"
            require(db.get_session(extra) is None and
                    db.create_session(extra, "api_server") == extra)
            extra_row = db.get_session(extra)
            require(type(extra_row) is dict and extra_row.get("id") == extra and
                    extra_row.get("system_prompt") in (None, ""))
            try:
                fx.native.world.start_conversation(profile, chat, shapes["phone"]["root"])
                for kind in KINDS:
                    shape = shapes[kind]
                    ref = ConversationRef(user_id=user, profile=profile, session_id=shape["root"])
                    rows = fx.native.bridge.latest_with_media(ref, 500)
                    info = fx.native.bridge.lineage(ref)
                    require(type(rows) is sidecar.BridgeMediaRows and len(rows.rows) == 258 and
                            rows.query.query_tip == shape["tip"] == info.lineage_tip and
                            {item.tool_row_id for item in rows.candidates} ==
                            set(shape["tool_ids"]))
                    accepted = []
                    for count in SELECTORS:
                        selected = select_tool_ids(shape["tool_ids"], count)
                        wanted = frozenset(selected)
                        candidate = sidecar.MediaSidecar(status=sidecar.SidecarStatus.CANDIDATES,
                            origin=sidecar.MediaOrigin.OWN_CONVERSATION if kind == "phone"
                            else sidecar.MediaOrigin.BROWSED_SESSION, user_id=user, profile=profile,
                            session_id=shape["root"], query_tip=rows.query.query_tip,
                            lineage_tip=info.lineage_tip,
                            candidates=tuple(item for item in rows.candidates
                                             if item.tool_row_id in wanted))
                        def check(result, kind=kind, selected=selected):
                            require(type(result) is binding.MediaBatchBinding and
                                    result.reason == "ok" and result.kind is not None and
                                    result.kind.value == kind and result.accepted == selected)

                        result = fx.native.bridge.bind_media_batch(candidate)
                        check(result)
                        accepted.append(len(result.accepted))
                        if (cost_case == KINDS.index(kind) * len(SHAPES) + index and
                                cost_selector == count):
                            cost_rows.append({"count": count, **measure_binding(
                                lambda candidate=candidate:
                                    fx.native.bridge.bind_media_batch(candidate), check)})
                    cells[(kind, lineage, prompt)] = {key: shape[key] for key in (
                        "kind", "lineage_count", "prompt_chars", "verified_prompt_count",
                        "history_rows", "legacy_rows", "generated_rows")} | {
                        "selector_counts": list(SELECTORS), "accepted_counts": accepted,
                        "proof_contexts": 2, "verified_database_prompt_count": sum(
                            item["verified_prompt_count"] for item in shapes.values()),
                        "verified_unprompted_extras": 1}
            finally:
                fx.native.world.start_conversation(profile, chat, "p1")
        require(db._conn is None)
    ordered = [cells[(kind, lineage, prompt)] for kind in KINDS
               for _, (lineage, prompt) in selected_shapes]
    report = {"cells": ordered, "timing_measured": False,
              "allocation_measured": False, "writer_cases_run": 0,
              "databases_closed": len(selected_shapes)}
    validate_preparation_report(report, cost_case)
    if cost_case is not None:
        kind, (lineage, prompt) = KINDS[cost_case // len(SHAPES)], SHAPES[cost_case % len(SHAPES)]
        cost = {"case": cost_case, "kind": kind, "lineage_count": lineage,
                "prompt_chars": prompt, "selectors": cost_rows, "warmups_per_selector": 1,
                "traces_per_selector": 1, "rss_measured": False, "mint_measured": False,
                "writer_cases_run": 0}
        validate_cost_report(cost, cost_case, cost_selector)
        cost_results.append(cost)
    return report
