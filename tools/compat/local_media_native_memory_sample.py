"""Optional native scratch-serving memory sample; no imports or IO at import time.

Streaming clients share the measured process. Their bounded buffers count toward
the unchanged server ceilings: this is a conservative combined-process sample,
not an isolated native-allocation bound or a production activation check. Each
case has a separate trace session with no reset within that case; RSS high-water
is cumulative and can conservatively include earlier preparation/case peaks.
"""

MIB = 1024 * 1024
IMAGE_BYTES = 8 * MIB
TRACE_LIMIT = 96 * MIB
RSS_LIMIT = 128 * MIB


def require(ok):
    if not ok:
        raise RuntimeError("native_media_memory_sample_refused")


def maximum_png(png):
    """Add one CRC-correct ancillary chunk to a known synthetic static PNG."""
    import struct
    import zlib

    require(type(png) is bytes and png[:8] == b"\x89PNG\r\n\x1a\n" and
            png[-12:] == b"\x00\x00\x00\x00IEND\xaeB`\x82")
    padding = IMAGE_BYTES - len(png) - 12
    require(padding > 0)
    body = b"\0" * padding
    crc = zlib.crc32(body, zlib.crc32(b"npAD")) & 0xffffffff
    result = b"".join((png[:-12], struct.pack(">I", padding), b"npAD", body,
                       struct.pack(">I", crc), png[-12:]))
    require(len(result) == IMAGE_BYTES)
    return result


_FIELDS = frozenset(("baseline_rss", "baseline_max_rss", "max_rss", "rss_increment",
    "peak_traced", "settled_traced", "buffers_held", "workers_held", "fifth_status",
    "p1_started", "max_client_chunk", "responses", "body_bytes", "cancelled_handlers"))


def validate_memory_report(report):
    require(type(report) is dict and set(report) == {"active", "cancelled"})
    for name, values in report.items():
        require(type(values) is dict and set(values) == _FIELDS and
                all(type(value) is int and value >= 0 for value in values.values()))
        require(values["baseline_rss"] > 0 and
                values["baseline_max_rss"] >= values["baseline_rss"] and
                values["max_rss"] >= values["baseline_max_rss"] and
                values["rss_increment"] == max(0, values["max_rss"] - values["baseline_rss"]) and
                4 * IMAGE_BYTES <= values["peak_traced"] <= TRACE_LIMIT and
                values["rss_increment"] <= RSS_LIMIT and
                values["settled_traced"] <= values["peak_traced"] and
                values["buffers_held"] == values["workers_held"] == 4 and
                values["fifth_status"] == 429 and values["p1_started"] == 4)
        if name == "active":
            require(values["responses"] == 4 and values["body_bytes"] == 4 * IMAGE_BYTES and
                    0 < values["max_client_chunk"] <= 65536 and values["cancelled_handlers"] == 0)
        else:
            require(values["responses"] == values["body_bytes"] == values["max_client_chunk"] == 0
                    and values["cancelled_handlers"] == 4)


async def run_memory_sample(fx, client, seed_image, handler_tasks, png):
    import asyncio
    import gc
    import hashlib
    import os
    import resource
    import sys
    import threading
    import time
    import tracemalloc

    import psutil
    from aiohttp import ServerDisconnectedError

    # ru_maxrss uses bytes on Darwin. Other platforms need their own reviewed
    # unit/metadata contract and must not inherit this platform measurement.
    require(sys.platform == "darwin" and not tracemalloc.is_tracing())
    image = maximum_png(png)
    expected_digest = hashlib.sha256(image).hexdigest()
    ids = [seed_image(number, image) for number in (10, 12, 14, 16)]
    del image
    devices = [await fx.rig.pair(client) for _ in range(3)]
    references = [await fx.mint(client, device) for device in devices]
    require(all(set(ids) <= set(refs) for refs in references))
    process = psutil.Process(os.getpid())
    report = {}

    async def until(predicate):
        deadline = time.monotonic() + 8
        while not predicate():
            require(time.monotonic() < deadline)
            await asyncio.sleep(0.005)

    for cancelled in (False, True):
        gate = threading.Event()
        entered = [0]
        enter_lock = threading.Lock()
        clients, owned_handlers = [], []
        response_count, body_bytes, max_chunk = [0], [0], [0]

        def hold_after_native_read(gate=gate, entered=entered, enter_lock=enter_lock):
            with enter_lock:
                entered[0] += 1
            require(gate.wait(15))

        if cancelled:
            fx.after_p1.append(hold_after_native_read)
        else:
            fx.p2_gate = gate
        require(fx.service.stats() == (0, 0, 0))
        starts_before, handlers_before, p1_before = len(fx.starts), len(handler_tasks), fx.p1_in
        p2_before = fx.p2_in

        async def streaming_get(index, *, cancelled=cancelled, max_chunk=max_chunk,
                                response_count=response_count, body_bytes=body_bytes):
            device_index = index // 2
            device = devices[device_index]
            ref = references[device_index][ids[index]]
            path = "/hmp/v1/bots/alpha/media/" + ref
            try:
                async with client.get(path, headers=fx.rig.env.headers(device)) as response:
                    require(not cancelled and response.status == 200 and
                            response.headers.get("Content-Length") == str(IMAGE_BYTES) and
                            response.headers.get("Content-Type") == "image/png")
                    digest, received = hashlib.sha256(), 0
                    async for chunk in response.content.iter_chunked(65536):
                        require(0 < len(chunk) <= 65536)
                        max_chunk[0] = max(max_chunk[0], len(chunk))
                        received += len(chunk)
                        require(received <= IMAGE_BYTES)
                        digest.update(chunk)
                    require(received == IMAGE_BYTES and digest.hexdigest() == expected_digest)
                    response_count[0] += 1
                    body_bytes[0] += received
            except ServerDisconnectedError:
                require(cancelled)

        gc.collect()
        baseline_rss = process.memory_info().rss
        baseline_max = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        tracemalloc.start()
        try:
            clients = [asyncio.create_task(streaming_get(index)) for index in range(4)]
            await until(lambda entered=entered, cancelled=cancelled, p2_before=p2_before:
                        entered[0] == 4 if cancelled else fx.p2_in - p2_before == 4)
            require(fx.service.stats() == (4, 4, 2) and fx.p1_in - p1_before == 4)
            await until(lambda handlers_before=handlers_before:
                        len(handler_tasks) - handlers_before == 4)
            owned_handlers = handler_tasks[handlers_before:]
            require(len(owned_handlers) == 4 and len(set(owned_handlers)) == 4)
            futures = [future for _, status, future in fx.starts[starts_before:]
                       if status == "started"]
            if cancelled:
                require(len(futures) == 4 and all(future.running() for future in futures))
                for task in owned_handlers:
                    task.cancel()
                await asyncio.gather(*owned_handlers, return_exceptions=True)
                require(all(task.cancelled() for task in owned_handlers) and
                        fx.service.stats() == (4, 4, 2) and
                        all(future.running() and not future.cancelled() for future in futures))
            status, _, _ = await fx.get(client, references[2][ids[0]], dev=devices[2])
            require(status == 429 and fx.p1_in - p1_before == 4 and
                    fx.service.stats() == (4, 4, 2))
            # All four actual buffers remain held here, including after handler
            # cancellation. No high-water reset or exclusion of client allocations.
            require(tracemalloc.get_traced_memory()[0] >= 4 * IMAGE_BYTES)
            gate.set()
            await asyncio.gather(*clients)
            await until(lambda: fx.service.stats() == (0, 0, 0))
            require(all(future.done() and not future.cancelled() for future in futures))
            require(all(lease._payload is None and lease._finished and lease._released
                        for lease, status, _ in fx.starts[starts_before:] if status == "started"))
            if cancelled:
                require(all(future.result() is False for future in futures))
            gc.collect()
            settled, peak = tracemalloc.get_traced_memory()
            maximum_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            values = {"baseline_rss": baseline_rss, "baseline_max_rss": baseline_max,
                "max_rss": maximum_rss, "rss_increment": max(0, maximum_rss - baseline_rss),
                "peak_traced": peak, "settled_traced": settled,
                "buffers_held": 4, "workers_held": 4,
                "fifth_status": status, "p1_started": fx.p1_in - p1_before,
                "max_client_chunk": max_chunk[0], "responses": response_count[0],
                "body_bytes": body_bytes[0], "cancelled_handlers": 4 if cancelled else 0}
            report["cancelled" if cancelled else "active"] = values
        finally:
            # Retain every original client/handler until settlement. Gate release
            # makes failure cleanup possible, never turns failure into a pass.
            gate.set()
            if clients:
                await asyncio.gather(*clients, return_exceptions=True)
            if owned_handlers:
                await asyncio.gather(*owned_handlers, return_exceptions=True)
            tracemalloc.stop()
            fx.p2_gate = None
            if cancelled:
                fx.after_p1.remove(hold_after_native_read)
    validate_memory_report(report)
    return report
