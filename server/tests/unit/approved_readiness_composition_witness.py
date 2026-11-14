"""Exact readiness inverse for composition; parent witnesses still check unrelated bytes."""

EDITS = (
    (
        (
            'IDENTITY_CHANGED_MESSAGE = "HMP instance key changed; restart the'
            ' gateway to serve the new key"\n\n\ndef _readiness_owner_device_ids_'
            'from_adapter(adapter: Any) -> frozenset[str]:\n    """Strict, read'
            'iness-only projection of the loaded legacy adapter controls."""\n '
            '   live_config = getattr(adapter, "config", None)\n    if live_con'
            'fig is None:\n        raise ValueError("readiness config unavailab'
            'le")\n    live_extra = getattr(live_config, "extra", None)\n    if '
            'not isinstance(live_extra, Mapping):\n        raise ValueError("re'
            'adiness config malformed")\n    if "owner_device_ids" not in live_'
            'extra:\n        return frozenset()\n    ids = live_extra["owner_dev'
            'ice_ids"]\n    if not isinstance(ids, list) or not all(isinstance('
            'item, str) for item in ids):\n        raise ValueError("readiness '
            'controls malformed")\n    return frozenset(ids)\n\n\ndef _readiness_s'
            'ettings_from_adapter(adapter: Any) -> object:\n    """Return only '
            "the loaded adapter's settings mapping for the readiness projectio"
            'n."""\n    live_config = getattr(adapter, "config", None)\n    if l'
            'ive_config is None:\n        raise ValueError("readiness config un'
            'available")\n    live_extra = getattr(live_config, "extra", None)\n'
            '    if not isinstance(live_extra, Mapping):\n        raise ValueEr'
            'ror("readiness config malformed")\n    return live_extra\n\n'
        ),
        (
            'IDENTITY_CHANGED_MESSAGE = "HMP instance key changed; restart the'
            ' gateway to serve the new key"\n'
        ),
    ),
    (
        (
            '    session_browsing = extra.get("session_browsing", True) if isi'
            'nstance(extra, Mapping) else True\n    # Canonical local configura'
            'tion: platforms.hmp.extra.controls_requests.enabled. The route\n  '
            '  # family is registered only on this listener start when the val'
            'ue is the literal bool True.\n    # Changing the host config requi'
            'res a listener restart; requests cannot toggle registration.\n    '
            'controls_block = extra.get("controls_requests") if isinstance(ext'
            'ra, Mapping) else None\n    controls_requests_enabled = (\n        '
            'isinstance(controls_block, Mapping) and controls_block.get("enabl'
            'ed") is True\n    )\n'
        ),
        (
            '    session_browsing = extra.get("session_browsing", True) if isi'
            'nstance(extra, Mapping) else True\n'
        ),
    ),
    (
        (
            '\n    def _readiness_owner_device_ids() -> frozenset[str]:\n       '
            ' return _readiness_owner_device_ids_from_adapter(adapter)\n\n    de'
            'f _readiness_settings() -> object:\n        return _readiness_sett'
            'ings_from_adapter(adapter)\n\n'
        ),
        (
            '\n'
        ),
    ),
    (
        (
            '        session_browsing_enabled=session_browsing is not False,\n '
            '       controls_requests_enabled=controls_requests_enabled,\n     '
            '   read_worker_budget=(getattr(adapter, "_read_worker_budget", No'
            'ne)\n                            or server.ReadWorkerBudget()),\n'
        ),
        (
            '        session_browsing_enabled=session_browsing is not False,\n'
        ),
    ),
    (
        (
            '        owner_device_ids=_read_owner_device_ids,\n        readines'
            's_owner_device_ids=_readiness_owner_device_ids,\n        readiness'
            '_settings=_readiness_settings,\n'
        ),
        (
            '        owner_device_ids=_read_owner_device_ids,\n'
        ),
    ),
    (
        (
            '        self._record_lock = threading.Lock()\n        self._read_w'
            'orker_budget = server.ReadWorkerBudget()\n'
        ),
        (
            '        self._record_lock = threading.Lock()\n'
        ),
    ),
    (
        (
            '        self._nonce = secrets.token_hex(16)\n        try:\n        '
            '    await srv.start_operator_read(anchor, self._nonce)\n        ex'
            'cept Exception:\n            log_event("operator_read_start", outc'
            'ome="unavailable")\n'
        ),
        (
            '        self._nonce = secrets.token_hex(16)\n'
        ),
    ),
    (
        (
            '        self._drop_record()\n        if srv.operator_worker_debt:\n'
            '            asyncio.get_running_loop().create_task(self._close_af'
            'ter_operator_drain(srv))\n        else:\n            self._close_ge'
            'neration(srv.ctx)\n            srv.ctx.store.close()\n'
        ),
        (
            '        self._drop_record()\n        self._close_generation(srv.ct'
            'x)\n        srv.ctx.store.close()\n'
        ),
    ),
    (
        (
            '            self._drop_record()\n            if srv.operator_worke'
            'r_debt:\n                asyncio.get_running_loop().create_task(se'
            'lf._close_after_operator_drain(srv))\n            else:\n          '
            '      self._close_generation(srv.ctx)\n                srv.ctx.sto'
            're.close()\n'
        ),
        (
            '            self._drop_record()\n            self._close_generatio'
            'n(srv.ctx)\n            srv.ctx.store.close()\n'
        ),
    ),
    (
        (
            '        self._mark_disconnected()\n\n    async def _close_after_ope'
            'rator_drain(self, srv: server.HmpServer) -> None:\n        await s'
            'rv.wait_operator_drain()\n        self._close_generation(srv.ctx)\n'
            '        srv.ctx.store.close()\n'
        ),
        (
            '        self._mark_disconnected()\n'
        ),
    ),
)

def reverse_readiness_adapter(text: str) -> str:
    for accepted, previous in reversed(EDITS):
        assert text.count(accepted) == 1
        text = text.replace(accepted, previous, 1)
    return text
