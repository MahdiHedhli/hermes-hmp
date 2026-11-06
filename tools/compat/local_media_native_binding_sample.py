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


def validate_mint_mode(case, selector, mint):
    validate_cost_mode(case, selector)
    require(type(mint) is bool and (not mint or case is not None))


def measure_mint(registry_module, candidate, bound, *, user, profile):
    """Trace a fresh modeled mint loop, retaining results before explicit cleanup.

    Native complete binding has already verified the candidate. Production
    registry/Binding/descriptor types are used, with shared field objects as in
    the synchronous emission loop. This does not execute S4 authorization or
    its event-loop route, and does not measure native C memory or RSS.
    Automatic garbage collection policy is unchanged.
    """
    import gc
    import tracemalloc
    from types import ModuleType

    from hmp_plugin.contract import WireMediaDescriptor

    require(type(registry_module) is ModuleType and not tracemalloc.is_tracing() and
            bound.sidecar is candidate and bound.ok and candidate.provenance_consistent and
            candidate.user_id == user and candidate.profile == profile and
            len(bound.accepted) in SELECTORS)
    device, instance = "synthetic-c6b-mint-device", "synthetic-c6b-mint-instance"
    session, tip = bound.session_id, bound.tip
    kind = registry_module.SessionKind(bound.kind.value)
    digests = {item.tool_row_id: item.raw_digest for item in candidate.candidates}
    require(set(bound.accepted) == set(digests))
    gc.collect()
    require(not tracemalloc.is_tracing())
    tracemalloc.start()
    try:
        baseline, _ = tracemalloc.get_traced_memory()
        registry = registry_module.LocalMediaRegistry()
        descriptors = tuple(WireMediaDescriptor(kind="image", ref=registry.mint(
            registry_module.Binding(device_id=device, user_id=user, instance_id=instance,
                profile=profile, kind=kind, session_id=session, tip=tip,
                tool_row_id=row_id, raw_digest=digests[row_id]))) for row_id in bound.accepted)
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    # Validation follows the trace. It cannot inflate the reported mint peak.
    require(peak >= current >= baseline and len(descriptors) == len(bound.accepted) and
            len({item.ref for item in descriptors}) == len(descriptors))
    caller = registry_module.Caller(device_id=device, user_id=user, instance_id=instance,
                                    profile=profile)
    for row_id, descriptor in zip(bound.accepted, descriptors, strict=True):
        entry = registry.lookup(descriptor.ref, caller)
        require(entry is not None)
        value = entry.binding
        require(value.device_id is device and value.user_id is user and
                value.instance_id is instance and value.profile is profile and
                value.kind is kind and value.session_id is session and value.tip is tip and
                value.tool_row_id == row_id and value.raw_digest is digests[row_id])
    require(len(registry._entries) == len(descriptors))
    return {"count": len(descriptors), "peak_traced_bytes": peak - baseline,
            "current_traced_bytes": current - baseline, "refs_verified": len(descriptors),
            "shared_fields_verified": True, "before_explicit_gc": True}


def validate_mint_report(report, case, selector):
    validate_mint_mode(case, selector, True)
    require(type(report) is dict and set(report) == {"case", "kind", "lineage_count",
        "prompt_chars", "selectors", "modeled_loop", "binding_measured", "rss_measured",
        "writer_cases_run"})
    kind, (lineage, prompt) = KINDS[case // len(SHAPES)], SHAPES[case % len(SHAPES)]
    require(type(report["case"]) is int and report["case"] == case and
            type(report["kind"]) is str and report["kind"] == kind and
            type(report["lineage_count"]) is int and report["lineage_count"] == lineage and
            type(report["prompt_chars"]) is int and report["prompt_chars"] == prompt and
            report["modeled_loop"] is True and report["binding_measured"] is False and
            report["rss_measured"] is False and type(report["writer_cases_run"]) is int and
            report["writer_cases_run"] == 0 and type(report["selectors"]) is list and
            len(report["selectors"]) == 1)
    row = report["selectors"][0]
    require(type(row) is dict and set(row) == {"count", "peak_traced_bytes",
        "current_traced_bytes", "refs_verified", "shared_fields_verified", "before_explicit_gc"} and
        type(row["count"]) is int and type(row["refs_verified"]) is int and
        row["count"] == row["refs_verified"] == selector and
        row["shared_fields_verified"] is True and row["before_explicit_gc"] is True and
        type(row["peak_traced_bytes"]) is int and type(row["current_traced_bytes"]) is int and
        row["peak_traced_bytes"] >= row["current_traced_bytes"] >= 0)


def validate_sample_mode(case, selector, mint, rss):
    validate_mint_mode(case, selector, mint)
    require(type(rss) is bool and not (mint and rss) and (not rss or case is not None))


def rss_values(before_current, before_max, after_current, after_max):
    """Darwin byte witnesses; cumulative peaks include earlier preparation."""
    require(all(type(value) is int and value > 0 for value in (
        before_current, before_max, after_current, after_max)) and
        before_max >= before_current and after_max >= max(before_max, after_current))
    return {"before_current": before_current, "before_max": before_max,
            "after_current": after_current, "after_max": after_max,
            "current_delta": after_current - before_current,
            "peak_growth": after_max - before_max,
            "peak_above_current_baseline": max(0, after_max - before_current)}


def measure_binding_rss(bind, check):
    """Observe self-process RSS around one warm binding, without tracing.

    Darwin ru_maxrss is cumulative and includes prior fixture/native activity.
    Its upper difference is not an isolated binding/native-C allocation bound.
    Validation is outside the interval; result remains held at observation.
    """
    import sys
    import tracemalloc

    require(sys.platform == "darwin" and not tracemalloc.is_tracing() and
            callable(bind) and callable(check))
    import gc
    import os
    import resource

    import psutil

    process = psutil.Process(os.getpid())
    gc.collect()
    before_current = process.memory_info().rss
    before_max = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result = bind()
    after_current = process.memory_info().rss
    after_max = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    check(result)
    values = rss_values(before_current, before_max, after_current, after_max)
    del result
    return values


def validate_rss_report(report, case, selector):
    validate_sample_mode(case, selector, False, True)
    require(type(report) is dict and set(report) == {"case", "kind", "lineage_count",
        "prompt_chars", "selectors", "platform", "rss_unit", "includes_prior_peak",
        "isolated_native_allocation_bound", "tracing_enabled", "mint_measured", "writer_cases_run"})
    kind, (lineage, prompt) = KINDS[case // len(SHAPES)], SHAPES[case % len(SHAPES)]
    require(type(report["case"]) is int and report["case"] == case and
            type(report["kind"]) is str and report["kind"] == kind and
            type(report["lineage_count"]) is int and report["lineage_count"] == lineage and
            type(report["prompt_chars"]) is int and report["prompt_chars"] == prompt and
            report["platform"] == "darwin" and report["rss_unit"] == "bytes" and
            report["includes_prior_peak"] is True and
            report["isolated_native_allocation_bound"] is False and
            report["tracing_enabled"] is report["mint_measured"] is False and
            type(report["writer_cases_run"]) is int and report["writer_cases_run"] == 0 and
            type(report["selectors"]) is list and len(report["selectors"]) == 1)
    row = report["selectors"][0]
    require(type(row) is dict and set(row) == {"count", "before_current", "before_max",
        "after_current", "after_max", "current_delta", "peak_growth", "peak_above_current_baseline"}
        and type(row["count"]) is int and row["count"] == selector)
    expected = rss_values(*(row[key] for key in (
        "before_current", "before_max", "after_current", "after_max")))
    require(all(type(row[key]) is int and row[key] == value for key, value in expected.items()))

def run_preparation(fx, open_cell, *, user, profile, chat, cost_case=None,
                    cost_selector=None, cost_results=None, mint=False, rss=False,
                    writer_module=None, writer_name=None, writer_owners=None, hook_owners=None,
                    writer_ports=None):
    """Verify the full matrix, or both contexts of one explicitly selected cost shape.

    Each lineage/prompt shape owns a fresh native DB with BOTH proof sources:
    canonical Bot Chat identity is never renamed/cleared, and the Phone case
    cannot avoid a full contrary Bot Chat proof by omitting the canonical chat.
    Synthetic routing-store changes stay inside this fixture.
    No current default model/provider/grant is changed.
    """
    from hmp_plugin.contract import ConversationRef

    validate_sample_mode(cost_case, cost_selector, mint, rss)
    if writer_name is not None:
        require(writer_module is not None and not mint and not rss and
                type(writer_owners) is list and type(hook_owners) is list and
                type(writer_ports) is tuple and len(writer_ports) == 2 and
                all(callable(port) for port in writer_ports))
        writer_module.validate_request(cost_case, cost_selector, writer_name)
    require((cost_case is None and cost_results is None) or
            (cost_case is not None and type(cost_results) is list and not cost_results))
    cost_rows = []
    writer_evidence = None
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
                            if writer_name is not None:
                                writer_evidence = (candidate, result, selected, shape)
                            elif mint:
                                cost_rows.append(measure_mint(fx.rig.ctx.media_registry_module,
                                    candidate, result, user=user, profile=profile))
                            elif rss:
                                cost_rows.append({"count": count, **measure_binding_rss(
                                    lambda candidate=candidate:
                                        fx.native.bridge.bind_media_batch(candidate), check)})
                            else:
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
                if writer_name is not None:
                    require(writer_evidence is not None)
                    candidate, reference, selected, shape = writer_evidence
                    cost_rows.append(writer_module.run_scenario(
                        fx, db, candidate, reference, selected, shape, extra,
                        case=cost_case, request=writer_name, user=user, profile=profile, chat=chat,
                        owners=writer_owners, hooks=hook_owners,
                        acquire_native=writer_ports[0], release_native=writer_ports[1]))
            finally:
                if writer_name is None or writer_module.barrier(writer_owners, hook_owners):
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
        if writer_name is not None:
            require(len(cost_rows) == 1)
            cost = cost_rows[0]
            writer_module.validate_report(cost, cost_case, cost_selector, writer_name)
        elif mint:
            cost = {"case": cost_case, "kind": kind, "lineage_count": lineage,
                    "prompt_chars": prompt, "selectors": cost_rows, "modeled_loop": True,
                    "binding_measured": False, "rss_measured": False, "writer_cases_run": 0}
            validate_mint_report(cost, cost_case, cost_selector)
        elif rss:
            cost = {"case": cost_case, "kind": kind, "lineage_count": lineage,
                    "prompt_chars": prompt, "selectors": cost_rows, "platform": "darwin",
                    "rss_unit": "bytes", "includes_prior_peak": True,
                    "isolated_native_allocation_bound": False, "tracing_enabled": False,
                    "mint_measured": False, "writer_cases_run": 0}
            validate_rss_report(cost, cost_case, cost_selector)
        else:
            validate_cost_report(cost, cost_case, cost_selector)
        cost_results.append(cost)
    return report
