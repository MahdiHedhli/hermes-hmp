"""Test-only inverse of pinned presentation/readiness/media composition.

Keep earlier source guards and their unchanged baseline hashes. Exact blocks
remove only these committed deltas from the source supplied to older witnesses;
other bytes survive. This projection is not standalone validation or runtime
qualification. Owning new-route and lifecycle tests run against unchanged code.
"""
from __future__ import annotations

ADAPTER_11A70F01 = (
    (
        (
            '        self._start_cleanup_task: asyncio.Task[None] | None = No'
            'ne\n        self._failed_start_server: server.HmpServer | None = '
            'None\n        self._dependency_closers: set[asyncio.Task[None]] ='
            ' set()\n        self._readiness_dependency_closers: set[asyncio.T'
            'ask[None]] = set()\n        self._dependency_close_unknown: serve'
            'r.HmpServer | None = None\n        self._record: Path | None = No'
            "ne\n        # Live-bug fix: the nonce this incarnation's record w"
            'as written with (SR-7 -- a fresh\n'
        ),
        (
            '        self._start_cleanup_task: asyncio.Task[None] | None = No'
            'ne\n        self._failed_start_server: server.HmpServer | None = '
            'None\n        self._dependency_closers: set[asyncio.Task[None]] ='
            ' set()\n        self._dependency_close_unknown: server.HmpServer '
            '| None = None\n        self._record: Path | None = None\n        #'
            " Live-bug fix: the nonce this incarnation's record was written w"
            'ith (SR-7 -- a fresh\n'
        ),
    ),
    (
        (
            '        if self._server is not None:\n            return (self._s'
            'erver._stop_owner is None and self._server._stopping is None\n   '
            '                 and not self._server.closed.is_set())\n        i'
            'f self._readiness_dependency_closers:\n            return False\n '
            '       if self._dependency_close_unknown is not None or any(\n   '
            '         task.done() and (task.cancelled() or task.exception() i'
            's not None)\n            for task in self._dependency_closers\n'
        ),
        (
            '        if self._server is not None:\n            return (self._s'
            'erver._stop_owner is None and self._server._stopping is None\n   '
            '                 and not self._server.closed.is_set())\n        i'
            'f self._dependency_close_unknown is not None or any(\n           '
            ' task.done() and (task.cancelled() or task.exception() is not No'
            'ne)\n            for task in self._dependency_closers\n'
        ),
    ),
    (
        (
            '            task.cancel()  # fire-and-forget: this callback itse'
            'lf is synchronous (server.py)\n        self._drop_record()\n      '
            '  try:\n            if (srv.operator_worker_debt or srv.presentat'
            'ion_worker_debt\n                    or getattr(srv, "readiness_w'
            'orker_debt", 0)):\n                self._defer_dependency_close(s'
            'rv)\n            else:\n                self._close_dependencies(s'
            'rv)\n'
        ),
        (
            '            task.cancel()  # fire-and-forget: this callback itse'
            'lf is synchronous (server.py)\n        self._drop_record()\n      '
            '  try:\n            if srv.operator_worker_debt or srv.presentati'
            'on_worker_debt:\n                self._defer_dependency_close(srv'
            ')\n            else:\n                self._close_dependencies(srv'
            ')\n'
        ),
    ),
    (
        (
            '                self._server = None\n            self._drop_recor'
            'd()\n            self._mark_disconnected()\n            if (srv.op'
            'erator_worker_debt or srv.presentation_worker_debt\n             '
            '       or getattr(srv, "readiness_worker_debt", 0)):\n           '
            '     self._defer_dependency_close(srv)\n            else:\n       '
            '         self._close_dependencies(srv)\n'
        ),
        (
            '                self._server = None\n            self._drop_recor'
            'd()\n            self._mark_disconnected()\n            if srv.ope'
            'rator_worker_debt or srv.presentation_worker_debt:\n             '
            '   self._defer_dependency_close(srv)\n            else:\n         '
            '       self._close_dependencies(srv)\n'
        ),
    ),
    (
        (
            '            self._mark_disconnected()\n\n    async def _close_afte'
            'r_operator_drain(self, srv: server.HmpServer) -> None:\n        i'
            'f getattr(srv, "readiness_worker_debt", 0):\n            await sr'
            'v.wait_readiness_drain()\n        await srv.wait_operator_drain()'
            '\n        await srv.wait_presentation_drain()\n        self._close'
            '_dependencies(srv)\n'
        ),
        (
            '            self._mark_disconnected()\n\n    async def _close_afte'
            'r_operator_drain(self, srv: server.HmpServer) -> None:\n        a'
            'wait srv.wait_operator_drain()\n        await srv.wait_presentati'
            'on_drain()\n        self._close_dependencies(srv)\n'
        ),
    ),
    (
        (
            '    def _close_dependencies(self, srv: server.HmpServer) -> None'
            ':\n        if srv._dependencies_closed:\n            return\n      '
            '  readiness_owner = getattr(srv.ctx, "readiness_reads", None)\n  '
            '      if readiness_owner is not None and not readiness_owner.dra'
            'ined:\n            raise RuntimeError("readiness dependency drain'
            ' unavailable")\n        if self._dependency_close_unknown is not '
            'None or srv._dependencies_close_unknown:\n            raise Runti'
            "meError('dependency cleanup unavailable')\n        self._dependen"
            'cy_close_unknown = srv  # retain before first possible partial e'
            'ffect\n'
        ),
        (
            '    def _close_dependencies(self, srv: server.HmpServer) -> None'
            ':\n        if srv._dependencies_closed:\n            return\n      '
            '  if self._dependency_close_unknown is not None or srv._dependen'
            "cies_close_unknown:\n            raise RuntimeError('dependency c"
            "leanup unavailable')\n        self._dependency_close_unknown = sr"
            'v  # retain before first possible partial effect\n'
        ),
    ),
    (
        (
            '        task = asyncio.get_running_loop().create_task(self._clos'
            'e_after_operator_drain(srv))\n        srv._dependency_close_task '
            '= task\n        self._dependency_closers.add(task)\n        if get'
            'attr(srv, "readiness_worker_debt", 0):\n            self._readine'
            'ss_dependency_closers.add(task)\n        # Keep failed/cancelled '
            'owners too: their outcome is not a dependency\n        # close pr'
            'oof, and no automatic replay is safe after an uncertain close.\n '
            '       task.add_done_callback(self._dependency_close_finished)\n'
        ),
        (
            '        task = asyncio.get_running_loop().create_task(self._clos'
            'e_after_operator_drain(srv))\n        srv._dependency_close_task '
            '= task\n        self._dependency_closers.add(task)\n        # Keep'
            ' failed/cancelled owners too: their outcome is not a dependency\n'
            '        # close proof, and no automatic replay is safe after an '
            'uncertain close.\n        task.add_done_callback(self._dependency'
            '_close_finished)\n'
        ),
    ),
    (
        (
            '    def _dependency_close_finished(self, task: asyncio.Task[None'
            ']) -> None:\n        if not task.cancelled() and task.exception()'
            ' is None:\n            self._dependency_closers.discard(task)\n   '
            '         self._readiness_dependency_closers.discard(task)\n\n    a'
            'sync def _cleanup_failed_start(self, srv: server.HmpServer) -> N'
            'one:\n        await self._cancel_profile_refresh()\n'
        ),
        (
            '    def _dependency_close_finished(self, task: asyncio.Task[None'
            ']) -> None:\n        if not task.cancelled() and task.exception()'
            ' is None:\n            self._dependency_closers.discard(task)\n\n  '
            '  async def _cleanup_failed_start(self, srv: server.HmpServer) -'
            '> None:\n        await self._cancel_profile_refresh()\n'
        ),
    ),
    (
        (
            '            self._server = None\n        self._drop_record()\n    '
            '    self._mark_disconnected()\n        if (srv.operator_worker_de'
            'bt or srv.presentation_worker_debt\n                    or getatt'
            'r(srv, "readiness_worker_debt", 0)):\n            self._defer_dep'
            'endency_close(srv)\n        else:\n            self._close_depende'
            'ncies(srv)\n'
        ),
        (
            '            self._server = None\n        self._drop_record()\n    '
            '    self._mark_disconnected()\n        if srv.operator_worker_deb'
            't or srv.presentation_worker_debt:\n            self._defer_depen'
            'dency_close(srv)\n        else:\n            self._close_dependenc'
            'ies(srv)\n'
        ),
    ),
)

ADAPTER_7C528066 = (
    (
        (
            '    def __init__(self, config: Any) -> None:\n        super().__i'
            'nit__(config=config, platform=Platform(PLATFORM_NAME))\n        s'
            'elf._server: server.HmpServer | None = None\n        self._connec'
            't_lock = asyncio.Lock()\n        self._presentation_owner = serve'
            'r.presentation_native_service.NativePresentationOwner()\n        '
            'self._start_cleanup_task: asyncio.Task[None] | None = None\n     '
            '   self._failed_start_server: server.HmpServer | None = None\n   '
            '     self._dependency_closers: set[asyncio.Task[None]] = set()\n '
            '       self._dependency_close_unknown: server.HmpServer | None ='
            ' None\n        self._record: Path | None = None\n        # Live-bu'
            "g fix: the nonce this incarnation's record was written with (SR-"
            '7 -- a fresh\n        # value per listener START, not per record '
            'write) and the last `profiles` this adapter\n'
        ),
        (
            '    def __init__(self, config: Any) -> None:\n        super().__i'
            'nit__(config=config, platform=Platform(PLATFORM_NAME))\n        s'
            'elf._server: server.HmpServer | None = None\n        self._record'
            ': Path | None = None\n        # Live-bug fix: the nonce this inca'
            "rnation's record was written with (SR-7 -- a fresh\n        # val"
            'ue per listener START, not per record write) and the last `profi'
            'les` this adapter\n'
        ),
    ),
    (
        (
            '        return tuple(rows)\n\n    async def connect(self, *, is_re'
            'connect: bool = False) -> bool:\n        async with self._connect'
            '_lock:\n            return await self._connect_once(is_reconnect='
            'is_reconnect)\n\n    async def _connect_once(self, *, is_reconnect'
            ': bool = False) -> bool:\n        """Run the compat gate, then st'
            'art the TLS listener (server-modules.md "Startup order")."""\n   '
            '     if self._server is not None:\n            return (self._serv'
            'er._stop_owner is None and self._server._stopping is None\n      '
            '              and not self._server.closed.is_set())\n        if s'
            'elf._dependency_close_unknown is not None or any(\n            ta'
            'sk.done() and (task.cancelled() or task.exception() is not None)'
            '\n            for task in self._dependency_closers\n        ):\n   '
            '         return False\n        cleanup = self._start_cleanup_task'
            '\n        if self._failed_start_server is not None:\n            i'
            'f cleanup is None or not cleanup.done() or cleanup.cancelled():\n'
            '                return False\n            if cleanup.exception() '
            'is not None:\n                return False  # retain failed teard'
            'own; never close underneath unknown work\n            self._faile'
            'd_start_server = self._start_cleanup_task = None\n        try:\n  '
            '          settings = server.listener_settings(getattr(self.confi'
            'g, "extra", None))\n        except server.ListenerConfigError:\n'
        ),
        (
            '        return tuple(rows)\n\n    async def connect(self, *, is_re'
            'connect: bool = False) -> bool:\n        """Run the compat gate, '
            'then start the TLS listener (server-modules.md "Startup order").'
            '"""\n        if self._server is not None:\n            return True'
            '\n        try:\n            settings = server.listener_settings(ge'
            'tattr(self.config, "extra", None))\n        except server.Listene'
            'rConfigError:\n'
        ),
    ),
    (
        (
            '        srv = server.HmpServer(\n            ctx,\n            set'
            'tings,\n            on_closed=lambda: self._listener_closed(srv),'
            '\n            push_relay_factory=lambda: RelayClient(ctx.identity'
            '),\n            approval_test_owners=(_AT1_PLUGIN_MODULE, _AT1_AD'
            'APTER_MODULE),\n            presentation_owner=self._presentation'
            '_owner,\n        )\n        try:\n            await srv.start()\n   '
            '         self._require_start_current(srv)\n            return awa'
            'it self._finish_connect(srv, ctx)\n        except BaseException a'
            's exc:\n            # Adopt the actual failed listener before sta'
            'rting cleanup. Caller\n            # cancellation does not releas'
            'e its dependencies or permit a reset.\n            self._failed_s'
            'tart_server = srv\n            cleanup = asyncio.get_running_loop'
            '().create_task(self._cleanup_failed_start(srv))\n            self'
            '._start_cleanup_task = cleanup\n            try:\n                '
            'await asyncio.shield(cleanup)\n            except asyncio.Cancell'
            'edError:\n                raise\n            except Exception:\n   '
            "             log_event('adapter_cleanup', outcome='unavailable')"
            '\n            if isinstance(exc, asyncio.CancelledError):\n       '
            '         raise\n            if not isinstance(exc, Exception):\n  '
            '              raise\n            log_event("adapter_connect", out'
            'come="listener_failed")\n            raise ConnectionError("HMP l'
            'istener did not start") from exc\n\n    async def _finish_connect('
            'self, srv: server.HmpServer, ctx: server.ServerContext) -> bool:'
            '\n        self._server = srv\n        self._require_start_current('
            'srv, published=True)\n        anchor = ctx.identity.custody.ancho'
            'r_dir  # type: ignore[attr-defined]\n        self._record = liste'
            'ner_record_path(anchor)\n        # SR-7: one nonce for this liste'
            'ner incarnation, generated once here and reused by every\n'
        ),
        (
            '        srv = server.HmpServer(\n            ctx,\n            set'
            'tings,\n            on_closed=self._listener_closed,\n            '
            'push_relay_factory=lambda: RelayClient(ctx.identity),\n          '
            '  approval_test_owners=(_AT1_PLUGIN_MODULE, _AT1_ADAPTER_MODULE)'
            ',\n        )\n        try:\n            await srv.start()\n        e'
            'xcept Exception as exc:\n            self._close_generation(ctx)\n'
            '            ctx.store.close()\n            log_event("adapter_con'
            'nect", outcome="listener_failed")\n            raise ConnectionEr'
            'ror("HMP listener did not start") from exc\n        self._server '
            '= srv\n        anchor = ctx.identity.custody.anchor_dir  # type: '
            'ignore[attr-defined]\n        self._record = listener_record_path'
            '(anchor)\n        # SR-7: one nonce for this listener incarnation'
            ', generated once here and reused by every\n'
        ),
    ),
    (
        (
            '            await srv.start_operator_read(anchor, self._nonce)\n '
            '       except Exception:\n            log_event("operator_read_st'
            'art", outcome="unavailable")\n        self._require_start_current'
            '(srv, published=True)\n        if srv.bound is not None:\n        '
            "    # OD-F8 (2026-09-27): the served profiles, so `pair offer`'s"
            ' one-command flow can\n            # list bots by name without im'
            'porting Hermes (S1). Best-effort only -- the bridge is\n'
        ),
        (
            '            await srv.start_operator_read(anchor, self._nonce)\n '
            '       except Exception:\n            log_event("operator_read_st'
            'art", outcome="unavailable")\n        if srv.bound is not None:\n '
            '           # OD-F8 (2026-09-27): the served profiles, so `pair o'
            "ffer`'s one-command flow can\n            # list bots by name wit"
            'hout importing Hermes (S1). Best-effort only -- the bridge is\n'
        ),
    ),
    (
        (
            '            else:\n                self._known_profiles = tuple(p'
            'rofiles) if profiles is not None else None\n                await'
            ' srv.start_approval_test(self._record, self._nonce)\n            '
            '    self._require_start_current(srv, published=True)\n           '
            ' if ctx.bridge is not None:\n                # Live-bug fix: the '
            'multiplexer brings secondary profiles online strictly AFTER\n    '
            '            # this `connect()` returns, so the record just writt'
            'en above can already be stale\n'
        ),
        (
            '            else:\n                self._known_profiles = tuple(p'
            'rofiles) if profiles is not None else None\n                await'
            ' srv.start_approval_test(self._record, self._nonce)\n            '
            'if ctx.bridge is not None:\n                # Live-bug fix: the m'
            'ultiplexer brings secondary profiles online strictly AFTER\n     '
            '           # this `connect()` returns, so the record just writte'
            'n above can already be stale\n'
        ),
    ),
    (
        (
            '                self._profile_refresh_task = asyncio.get_running'
            '_loop().create_task(\n                    self._periodic_profile_'
            'refresh()\n                )\n        self._require_start_current('
            'srv, published=True)\n        self._mark_connected()\n        retu'
            'rn True\n\n    def _require_start_current(self, srv: server.HmpSer'
            'ver, *, published: bool = False) -> None:\n        try:\n         '
            '   current = (\n                srv._runner is not None and srv._'
            'stop_owner is None and srv._stopping is None\n                and'
            ' not srv.closed.is_set() and srv.ctx.identity.still_current() is'
            ' True\n                and (not published or self._server is srv)'
            '\n            )\n        except Exception:\n            current = F'
            "alse\n        if not current:\n            raise ConnectionError('"
            "listener stopped during startup')\n\n    # -----------------------"
            '----------------------------------------------------------------'
            "---\n    # Live-bug fix: keep the listener record's `profiles` cu"
            'rrent while the listener runs.\n'
        ),
        (
            '                self._profile_refresh_task = asyncio.get_running'
            '_loop().create_task(\n                    self._periodic_profile_'
            'refresh()\n                )\n        self._mark_connected()\n     '
            '   return True\n\n    # ------------------------------------------'
            '------------------------------------------------\n    # Live-bug '
            "fix: keep the listener record's `profiles` current while the lis"
            'tener runs.\n'
        ),
    ),
    (
        (
            '            if record is not None:\n                cli.remove_li'
            'stener_record(record)\n\n    def _listener_closed(self, expected: '
            'server.HmpServer | None = None) -> None:\n        if expected is '
            'not None and self._server is not expected:\n            return  #'
            ' unpublished startup/deferred old owner cannot retire another li'
            'stener\n        srv, self._server = self._server, None\n        if'
            ' srv is None:\n            return\n'
        ),
        (
            '            if record is not None:\n                cli.remove_li'
            'stener_record(record)\n\n    def _listener_closed(self) -> None:\n '
            '       srv, self._server = self._server, None\n        if srv is '
            'None:\n            return\n'
        ),
    ),
    (
        (
            '        if task is not None:\n            task.cancel()  # fire-a'
            'nd-forget: this callback itself is synchronous (server.py)\n     '
            '   self._drop_record()\n        try:\n            if srv.operator_'
            'worker_debt or srv.presentation_worker_debt:\n                sel'
            'f._defer_dependency_close(srv)\n            else:\n               '
            ' self._close_dependencies(srv)\n        except Exception:\n       '
            "     log_event('adapter_cleanup', outcome='unavailable')\n       "
            ' # PR7-6 step 3: stay closed until the gateway restarts (a later'
            ' `connect` would load the\n        # new key and start a new list'
            'ener; nothing here restarts it).\n        self._set_fatal_error(I'
            'DENTITY_CHANGED_CODE, IDENTITY_CHANGED_MESSAGE, retryable=False)'
            '\n\n    async def disconnect(self) -> None:\n        async with sel'
            'f._connect_lock:\n            if self._failed_start_server is not'
            ' None:\n                cleanup = self._start_cleanup_task\n      '
            '          if cleanup is None:\n                    raise RuntimeE'
            "rror('listener cleanup unavailable')\n                await async"
            'io.shield(cleanup)\n            await self._disconnect_once()\n\n  '
            '  async def _disconnect_once(self) -> None:\n        await self._'
            'cancel_profile_refresh()\n        srv = self._server\n        if s'
            'rv is not None:\n'
        ),
        (
            '        if task is not None:\n            task.cancel()  # fire-a'
            'nd-forget: this callback itself is synchronous (server.py)\n     '
            '   self._drop_record()\n        if srv.operator_worker_debt:\n    '
            '        asyncio.get_running_loop().create_task(self._close_after'
            '_operator_drain(srv))\n        else:\n            self._close_gene'
            'ration(srv.ctx)\n            srv.ctx.store.close()\n        # PR7-'
            '6 step 3: stay closed until the gateway restarts (a later `conne'
            'ct` would load the\n        # new key and start a new listener; n'
            'othing here restarts it).\n        self._set_fatal_error(IDENTITY'
            '_CHANGED_CODE, IDENTITY_CHANGED_MESSAGE, retryable=False)\n\n    a'
            'sync def disconnect(self) -> None:\n        await self._cancel_pr'
            'ofile_refresh()\n        srv = self._server\n        if srv is not'
            ' None:\n'
        ),
    ),
    (
        (
            '            if self._server is srv:\n                self._server'
            ' = None\n            self._drop_record()\n            self._mark_d'
            'isconnected()\n            if srv.operator_worker_debt or srv.pre'
            'sentation_worker_debt:\n                self._defer_dependency_cl'
            'ose(srv)\n            else:\n                self._close_dependenc'
            'ies(srv)\n        else:\n            self._drop_record()\n         '
            '   self._mark_disconnected()\n\n    async def _close_after_operato'
            'r_drain(self, srv: server.HmpServer) -> None:\n        await srv.'
            'wait_operator_drain()\n        await srv.wait_presentation_drain('
            ')\n        self._close_dependencies(srv)\n\n    def _close_dependen'
            'cies(self, srv: server.HmpServer) -> None:\n        if srv._depen'
            'dencies_closed:\n            return\n        if self._dependency_c'
            'lose_unknown is not None or srv._dependencies_close_unknown:\n   '
            "         raise RuntimeError('dependency cleanup unavailable')\n  "
            '      self._dependency_close_unknown = srv  # retain before firs'
            't possible partial effect\n        srv._dependencies_close_unknow'
            'n = True\n        self._close_generation(srv.ctx)\n        srv.ctx'
            '.store.close()\n        srv._dependencies_closed = True\n        s'
            'rv._dependencies_close_unknown = False\n        self._dependency_'
            'close_unknown = None\n\n    def _defer_dependency_close(self, srv:'
            ' server.HmpServer) -> None:\n        if srv._dependencies_closed '
            'or srv._dependency_close_task is not None:\n            return\n  '
            '      if self._dependency_close_unknown is not None:\n           '
            " raise RuntimeError('dependency cleanup unavailable')\n        se"
            'lf._dependency_close_unknown = srv  # adopt before any task/star'
            't/registration effect\n        task = asyncio.get_running_loop().'
            'create_task(self._close_after_operator_drain(srv))\n        srv._'
            'dependency_close_task = task\n        self._dependency_closers.ad'
            'd(task)\n        # Keep failed/cancelled owners too: their outcom'
            'e is not a dependency\n        # close proof, and no automatic re'
            'play is safe after an uncertain close.\n        task.add_done_cal'
            'lback(self._dependency_close_finished)\n        self._dependency_'
            'close_unknown = None\n\n    def _dependency_close_finished(self, t'
            'ask: asyncio.Task[None]) -> None:\n        if not task.cancelled('
            ') and task.exception() is None:\n            self._dependency_clo'
            'sers.discard(task)\n\n    async def _cleanup_failed_start(self, sr'
            'v: server.HmpServer) -> None:\n        await self._cancel_profile'
            '_refresh()\n        await srv.stop(notify=False)\n        if self.'
            '_server is srv:\n            self._server = None\n        self._dr'
            'op_record()\n        self._mark_disconnected()\n        if srv.ope'
            'rator_worker_debt or srv.presentation_worker_debt:\n            s'
            'elf._defer_dependency_close(srv)\n        else:\n            self.'
            '_close_dependencies(srv)\n\n    '
            '@'
            'staticmethod\n    def _close_gener'
            'ation(ctx: server.ServerContext) -> None:\n'
        ),
        (
            '            if self._server is srv:\n                self._server'
            ' = None\n            self._drop_record()\n            if srv.opera'
            'tor_worker_debt:\n                asyncio.get_running_loop().crea'
            'te_task(self._close_after_operator_drain(srv))\n            else:'
            '\n                self._close_generation(srv.ctx)\n               '
            ' srv.ctx.store.close()\n        else:\n            self._drop_reco'
            'rd()\n        self._mark_disconnected()\n\n    async def _close_aft'
            'er_operator_drain(self, srv: server.HmpServer) -> None:\n        '
            'await srv.wait_operator_drain()\n        self._close_generation(s'
            'rv.ctx)\n        srv.ctx.store.close()\n\n    '
            '@'
            'staticmethod\n    def'
            ' _close_generation(ctx: server.ServerContext) -> None:\n'
        ),
    ),
)

SERVER_30DEDF99 = (
    (
        (
            '   includes the peer address and that same raw text via `exc_inf'
            'o` — never reaches the log either;\n   it always emits exactly `e'
            'vent=http_parse_error outcome=bad_request`.\n5. `compat` (ERR-2a)'
            ': on an unsupported build every path except `/hmp/v1/ready` and '
            'the\n   authenticated readiness capability path or exact own-Cont'
            'rols GET answers `503 other {why}`.\n   These additive reads neve'
            'r call native feature APIs or widen feature-operation gates.\n\nRa'
            'te limits (TR-6) are applied inside the P2, P4 and P5 handlers, '
            'because the contract orders\nthem against the body checks and key'
            's two of them on body fields.\n'
        ),
        (
            '   includes the peer address and that same raw text via `exc_inf'
            'o` — never reaches the log either;\n   it always emits exactly `e'
            'vent=http_parse_error outcome=bad_request`.\n5. `compat` (ERR-2a)'
            ': on an unsupported build every path except `/hmp/v1/ready` and '
            'the\n   authenticated readiness capability path answers `503 othe'
            'r {why}`. The capability handler\n   returns only its fixed compa'
            'tibility projection and does not call the bridge.\n\nRate limits ('
            'TR-6) are applied inside the P2, P4 and P5 handlers, because the'
            ' contract orders\nthem against the body checks and keys two of th'
            'em on body fields.\n'
        ),
    ),
    (
        (
            '    parse_peer_ip,\n    peer_key,  # noqa: F401\n    read_json_bod'
            'y,\n    single_header,\n)\nfrom .request_ctx import (\n    ReadWorke'
            'rBudget as ReadWorkerBudget,\n'
        ),
        (
            '    parse_peer_ip,\n    peer_key,  # noqa: F401\n    read_json_bod'
            'y,\n)\nfrom .request_ctx import (\n    ReadWorkerBudget as ReadWork'
            'erBudget,\n'
        ),
    ),
    (
        (
            'F1_ROUTES: tuple[tuple[str, str, str], ...] = (\n    ("GET", "/re'
            'ady", "PR0-1"),\n    ("GET", "/readiness/capabilities", "AR1"),\n '
            '   ("GET", "/devices/self/controls-readiness", "AR1-P1"),\n    ("'
            'GET", "/bots/{p}/readiness", "AR1"),\n    ("GET", "/bots/{p}/medi'
            'a-readiness", "LM-ENT1"),\n    ("GET", "/media-readiness/capabili'
            'ties", "LM-ENT1"),\n'
        ),
        (
            'F1_ROUTES: tuple[tuple[str, str, str], ...] = (\n    ("GET", "/re'
            'ady", "PR0-1"),\n    ("GET", "/readiness/capabilities", "AR1"),\n '
            '   ("GET", "/bots/{p}/readiness", "AR1"),\n    ("GET", "/bots/{p}'
            '/media-readiness", "LM-ENT1"),\n    ("GET", "/media-readiness/cap'
            'abilities", "LM-ENT1"),\n'
        ),
    ),
    (
        (
            '\n'
            '@'
            'web.middleware\nasync def compat_middleware(request: web.Reques'
            't, handler: Handler) -> web.StreamResponse:\n    """ERR-2a: retai'
            'n existing exceptions plus the exact authenticated self-read GET'
            '."""\n    ctx = context(request)\n    self_controls_read = (\n     '
            '   request.method == "GET"\n        and request.path == PATH_PREF'
            'IX + "/devices/self/controls-readiness"\n    )\n    if (not ctx.co'
            'mpat.supported\n            and request.path not in READ_COMPAT_E'
            'XEMPT_PATHS and not self_controls_read):\n        why = ctx.compa'
            't.why or OtherWhy.HERMES_BUILD_UNSUPPORTED\n        refusal = REA'
            'D_COMPAT_REFUSALS.get(why)\n        if refusal is None:  # never '
            'expected; fail closed on the build-unsupported refusal\n'
        ),
        (
            '\n'
            '@'
            'web.middleware\nasync def compat_middleware(request: web.Reques'
            't, handler: Handler) -> web.StreamResponse:\n    """ERR-2a: readi'
            'ness capabilities is the one authenticated additive exception (A'
            'R1)."""\n    ctx = context(request)\n    if not ctx.compat.support'
            'ed and request.path not in READ_COMPAT_EXEMPT_PATHS:\n        why'
            ' = ctx.compat.why or OtherWhy.HERMES_BUILD_UNSUPPORTED\n        r'
            'efusal = READ_COMPAT_REFUSALS.get(why)\n        if refusal is Non'
            'e:  # never expected; fail closed on the build-unsupported refus'
            'al\n'
        ),
    ),
    (
        (
            '        if exc.code in {\n            ErrorCode.UNAUTHENTICATED, '
            'ErrorCode.REVOKED, ErrorCode.WRONG_INSTANCE,\n        }:\n        '
            '    raise\n        raise HmpError(ErrorCode.READINESS_UNAVAILABLE'
            ') from None\n    except Exception:\n        raise HmpError(ErrorCo'
            'de.READINESS_UNAVAILABLE) from None\n\n\nasync def handle_self_cont'
            'rols_readiness(request: web.Request) -> web.Response:\n    """AR1'
            '-P1: own Controls observation, never a feature/API authorization'
            ' grant."""\n    _readiness_empty_get(request)\n    ctx = context(r'
            'equest)\n    origin = (ctx.identity, ctx.store, ctx.bridge)\n    i'
            'id = ctx.iid\n    generation = ctx.readiness_generation\n    deadl'
            'ine = time.monotonic() + _READINESS_DEADLINE_S\n    authorization'
            ' = single_header(request, "Authorization")\n    instance = single'
            '_header(request, "HMP-Instance")\n    lane = ctx.readiness_reads\n'
            '\n    def current() -> None:\n        # Only exact origin fields/t'
            'ime here: no Store or source callback on the loop.\n        if (c'
            'tx.identity is not origin[0] or ctx.store is not origin[1]\n     '
            '           or ctx.bridge is not origin[2] or ctx.iid != iid\n    '
            '            or ctx.readiness_generation != generation\n          '
            '      or type(generation) is not str\n                or readines'
            's.GENERATION_RE.fullmatch(generation) is None\n                or'
            ' time.monotonic() >= deadline):\n            raise readiness.Read'
            'inessUnavailableError()\n\n    def authenticate(expected: Any = No'
            'ne) -> Any:\n        current()\n        if ctx.identity.still_curr'
            'ent() is not True:\n            raise readiness.ReadinessUnavaila'
            'bleError()\n        who = Authenticator(origin[1], iid, ctx.now).'
            'authenticate(authorization, instance)\n        current()\n        '
            'if ctx.identity.still_current() is not True:\n            raise r'
            'eadiness.ReadinessUnavailableError()\n        if expected is not '
            'None and who != expected:\n            raise readiness.ReadinessU'
            'navailableError()\n        return who\n\n    def admission() -> tup'
            'le[Any, int]:\n        who = authenticate()\n        now = _readin'
            'ess_now(ctx)\n        current()\n        return who, now\n\n    def '
            'observe(expected: Any) -> dict[str, object]:\n        authenticat'
            'e(expected)\n        entitlement = _readiness_controls(ctx, expec'
            'ted.device_id)\n        authenticate(expected)\n        if _readin'
            'ess_controls(ctx, expected.device_id) != entitlement:\n          '
            '  raise readiness.ReadinessUnavailableError()\n        # Re-authe'
            'nticate AFTER both reads: revocation is definitive even if bytes'
            ' match.\n        authenticate(expected)\n        _readiness_now(ct'
            'x)\n        current()\n        return {"protocol": 1, "generation"'
            ': generation, "entitlement": entitlement,\n                "scope'
            '": ["jobs", "model"], "api_reachability": "not_probed"}\n\n    try'
            ':\n        if not isinstance(lane, ReadinessReadService):\n       '
            '     raise readiness.ReadinessUnavailableError()\n        async w'
            'ith lane.activity(admission, deadline=deadline) as (who, now):\n '
            '           current()\n            if context(request) is not ctx:'
            '\n                raise readiness.ReadinessUnavailableError()\n   '
            '         ctx.limiter.check("readiness", who.device_id, 30, now)\n'
            '        async with lane.activity(partial(observe, who), deadline'
            '=deadline) as payload:\n            current()\n            if cont'
            'ext(request) is not ctx:\n                raise readiness.Readine'
            'ssUnavailableError()\n            body = wire.dump_json(payload)\n'
            '            if len(body) > 512:\n                raise readiness.'
            'ReadinessUnavailableError()\n            return web.Response(body'
            '=body, content_type="application/json",\n                        '
            '        headers={"Cache-Control": "no-store"})\n    except HmpErr'
            'or as exc:\n        if exc.code in {ErrorCode.UNAUTHENTICATED, Er'
            'rorCode.REVOKED,\n                        ErrorCode.WRONG_INSTANC'
            'E, ErrorCode.RATE_LIMITED}:\n            raise\n        raise HmpE'
            'rror(ErrorCode.READINESS_UNAVAILABLE) from None\n    except Excep'
            'tion:\n'
        ),
        (
            '        if exc.code in {\n            ErrorCode.UNAUTHENTICATED, '
            'ErrorCode.REVOKED, ErrorCode.WRONG_INSTANCE,\n        }:\n        '
            '    raise\n        raise HmpError(ErrorCode.READINESS_UNAVAILABLE'
            ') from None\n    except Exception:\n'
        ),
    ),
    (
        (
            '    handlers: dict[str, Handler] = {\n        "/ready": handle_re'
            'ady,\n        "/readiness/capabilities": handle_readiness_capabil'
            'ities,\n        "/devices/self/controls-readiness": handle_self_c'
            'ontrols_readiness,\n        "/bots/{p}/readiness": handle_readine'
            'ss,\n        "/bots/{p}/media-readiness": handle_media_readiness,'
            '\n        "/media-readiness/capabilities": handle_media_readiness'
            '_capabilities,\n'
        ),
        (
            '    handlers: dict[str, Handler] = {\n        "/ready": handle_re'
            'ady,\n        "/readiness/capabilities": handle_readiness_capabil'
            'ities,\n        "/bots/{p}/readiness": handle_readiness,\n        '
            '"/bots/{p}/media-readiness": handle_media_readiness,\n        "/m'
            'edia-readiness/capabilities": handle_media_readiness_capabilitie'
            's,\n'
        ),
    ),
)

SERVER_11A70F01 = (
    (
        (
            ')\nfrom .pairing import handle_pair_complete, handle_pair_request'
            '\nfrom .push_dispatch import PushDispatcher, RelayPort\nfrom .read'
            'iness_work import ReadActivityUnavailableError, ReadinessReadSer'
            'vice\nfrom .reads import require_bot_authorized\n\n# `request_ctx` '
            'is the leaf module `ServerContext`/`CTX_KEY`/`context()`/the bod'
            'y and bearer\n'
        ),
        (
            ')\nfrom .pairing import handle_pair_complete, handle_pair_request'
            '\nfrom .push_dispatch import PushDispatcher, RelayPort\nfrom .read'
            's import require_bot_authorized\n\n# `request_ctx` is the leaf mod'
            'ule `ServerContext`/`CTX_KEY`/`context()`/the body and bearer\n'
        ),
    ),
    (
        (
            '        raise HmpError(ErrorCode.READINESS_UNAVAILABLE)\n    auth'
            'orization = request.headers.get("Authorization")\n    instance = '
            'request.headers.get("HMP-Instance")\n    lane = ctx.readiness_rea'
            'ds\n    if not isinstance(lane, ReadinessReadService):\n        ra'
            'ise HmpError(ErrorCode.READINESS_UNAVAILABLE)\n    deadline = tim'
            'e.monotonic() + _READINESS_DEADLINE_S\n    collect = partial(\n   '
            '     _collect_media_readiness if media else _collect_readiness,\n'
            '        ctx, authorization=authorization, instance=instance, exp'
            'ected=who,\n        profile=profile, device_id=who.device_id, dea'
            'dline=deadline, generation=generation,\n    )\n    try:\n        as'
            'ync with lane.activity(collect, deadline=deadline) as payload:\n '
            '           if media:\n                if not media_context_curren'
            't():\n                    raise HmpError(ErrorCode.READINESS_UNAV'
            'AILABLE)\n                # Final synchronous authority/readback '
            'fence after the worker await. Never await\n                # betw'
            'een this comparison and response construction. These authority r'
            'eaders can\n                # perform SQLite/native config I/O; t'
            'his is not a nonblocking performance claim.\n                try:'
            '\n                    current = _collect_media_readiness(\n       '
            '                 ctx, authorization=authorization, instance=inst'
            'ance, expected=who,\n                        profile=profile, dev'
            'ice_id=who.device_id, deadline=deadline,\n                       '
            ' generation=generation,\n                    )\n                  '
            '  if (not media_context_current()\n                            or'
            ' current["media"] != payload["media"]\n                          '
            '  or current["_authority"] != payload["_authority"]):\n          '
            '              raise readiness.ReadinessUnavailableError()\n      '
            '          except HmpError:\n                    raise\n           '
            '     except Exception:\n                    raise HmpError(ErrorC'
            'ode.READINESS_UNAVAILABLE) from None\n                payload.pop'
            '("_authority")  # internal snapshot never enters the wire DTO\n  '
            '          try:\n                body = wire.dump_json(payload)\n  '
            '          except Exception:\n                raise HmpError(Error'
            'Code.READINESS_UNAVAILABLE) from None\n            if len(body) >'
            ' readiness.MAX_RESPONSE_BYTES:\n                raise HmpError(Er'
            'rorCode.READINESS_UNAVAILABLE)\n            return web.Response(\n'
            '                body=body,\n                content_type="applica'
            'tion/json",\n                headers={"Cache-Control": "no-store"'
            '},\n            )\n    except (TimeoutError, readiness.ReadinessUn'
            'availableError, ReadActivityUnavailableError):\n        raise Hmp'
            'Error(ErrorCode.READINESS_UNAVAILABLE) from None\n    except HmpE'
            'rror:\n        raise\n    except Exception as exc:\n        log_han'
            'dler_exception(exc)\n        raise HmpError(ErrorCode.READINESS_U'
            'NAVAILABLE) from None\n\n\ndef _query_int(request: web.Request, nam'
            'e: str, *, default: int | None, lo: int, hi: int) -> int:\n'
        ),
        (
            '        raise HmpError(ErrorCode.READINESS_UNAVAILABLE)\n    auth'
            'orization = request.headers.get("Authorization")\n    instance = '
            'request.headers.get("HMP-Instance")\n    if not ctx.read_worker_b'
            'udget.reserve(operator=False):\n        raise HmpError(ErrorCode.'
            'READINESS_UNAVAILABLE)\n    deadline = time.monotonic() + _READIN'
            'ESS_DEADLINE_S\n    try:\n        work = asyncio.create_task(async'
            'io.to_thread(\n            _collect_media_readiness if media else'
            ' _collect_readiness,\n            ctx,\n            authorization='
            'authorization,\n            instance=instance,\n            expect'
            'ed=who,\n            profile=profile,\n            device_id=who.d'
            'evice_id,\n            deadline=deadline,\n            generation='
            'generation,\n        ))\n    except Exception:\n        ctx.read_wo'
            'rker_budget.release(operator=False)\n        raise HmpError(Error'
            'Code.READINESS_UNAVAILABLE) from None\n\n    def release_worker(do'
            'ne: asyncio.Task[Any]) -> None:\n        with contextlib.suppress'
            '(asyncio.CancelledError):\n            done.exception()\n        c'
            'tx.read_worker_budget.release(operator=False)\n\n    work.add_done'
            '_callback(release_worker)\n    try:\n        payload = await async'
            'io.wait_for(asyncio.shield(work), timeout=_READINESS_DEADLINE_S)'
            '\n    except TimeoutError:\n        raise HmpError(ErrorCode.READI'
            'NESS_UNAVAILABLE) from None\n    except readiness.ReadinessUnavai'
            'lableError:\n        raise HmpError(ErrorCode.READINESS_UNAVAILAB'
            'LE) from None\n    except HmpError as exc:\n        if exc.code is'
            ' ErrorCode.READINESS_UNAVAILABLE:\n            raise HmpError(Err'
            'orCode.READINESS_UNAVAILABLE) from None\n        raise\n    except'
            ' Exception as exc:\n        log_handler_exception(exc)\n        ra'
            'ise HmpError(ErrorCode.READINESS_UNAVAILABLE) from None\n    if m'
            'edia:\n        if not media_context_current():\n            raise '
            'HmpError(ErrorCode.READINESS_UNAVAILABLE)\n        # Final synchr'
            'onous authority/readback fence after the worker await. Never awa'
            'it\n        # between this comparison and response construction. '
            'These authority readers can\n        # perform SQLite/native conf'
            'ig I/O; this is not a nonblocking performance claim.\n        try'
            ':\n            current = _collect_media_readiness(\n              '
            '  ctx, authorization=authorization, instance=instance, expected='
            'who,\n                profile=profile, device_id=who.device_id, d'
            'eadline=deadline,\n                generation=generation,\n       '
            '     )\n            if (not media_context_current()\n             '
            '       or current["media"] != payload["media"]\n                 '
            '   or current["_authority"] != payload["_authority"]):\n         '
            '       raise readiness.ReadinessUnavailableError()\n        excep'
            't HmpError:\n            raise\n        except Exception:\n        '
            '    raise HmpError(ErrorCode.READINESS_UNAVAILABLE) from None\n  '
            '      payload.pop("_authority")  # internal snapshot never enter'
            's the wire DTO\n    try:\n        body = wire.dump_json(payload)\n '
            '   except Exception:\n        raise HmpError(ErrorCode.READINESS_'
            'UNAVAILABLE) from None\n    if len(body) > readiness.MAX_RESPONSE'
            '_BYTES:\n        raise HmpError(ErrorCode.READINESS_UNAVAILABLE)\n'
            '    return web.Response(\n        body=body,\n        content_type'
            '="application/json",\n        headers={"Cache-Control": "no-store'
            '"},\n    )\n\n\ndef _query_int(request: web.Request, name: str, *, d'
            'efault: int | None, lo: int, hi: int) -> int:\n'
        ),
    ),
    (
        (
            "    docstring). Importing them at this module's own top level bi"
            "nds this app's route table to the\n    same load as everything el"
            'se it uses.\n    """\n    if ctx.readiness_reads is None:\n        '
            'ctx.readiness_reads = ReadinessReadService(ctx)\n    elif (not is'
            'instance(ctx.readiness_reads, ReadinessReadService)\n          or'
            ' not ctx.readiness_reads.is_for(ctx)):\n        raise RuntimeErro'
            'r("readiness owner unavailable")\n    app = web.Application(\n    '
            '    middlewares=[\n            current_key_middleware,\n'
        ),
        (
            "    docstring). Importing them at this module's own top level bi"
            "nds this app's route table to the\n    same load as everything el"
            'se it uses.\n    """\n    app = web.Application(\n        middlewar'
            'es=[\n            current_key_middleware,\n'
        ),
    ),
    (
        (
            '        },\n    )\n    app[CTX_KEY] = ctx\n\n    async def stop_read'
            'iness(_app: web.Application) -> None:\n        ctx.readiness_read'
            's.stop()\n\n    app.on_cleanup.append(stop_readiness)\n    # S5: th'
            "is app's own fetch service (dedicated executor, permits); never "
            'module-global. Threads\n    # start lazily on the first submissio'
            'n, and cleanup closes admissions without waiting.\n    app[media_'
            'fetch.MEDIA_SERVICE_KEY] = media_fetch.MediaFetchService()\n'
        ),
        (
            "        },\n    )\n    app[CTX_KEY] = ctx\n    # S5: this app's own"
            ' fetch service (dedicated executor, permits); never module-globa'
            'l. Threads\n    # start lazily on the first submission, and clean'
            'up closes admissions without waiting.\n    app[media_fetch.MEDIA_'
            'SERVICE_KEY] = media_fetch.MediaFetchService()\n'
        ),
    ),
    (
        (
            '        self._operator_read: Any = None\n        self._operator_r'
            'ead_drained: Any = None\n        self.operator_worker_debt = 0\n  '
            '      self.readiness_worker_debt = 0\n        # The actual adapte'
            'r retains the owner across reconnects. A standalone\n        # se'
            'rver without that owner never silently creates a replacement poo'
            'l.\n        self._presentation_owner = presentation_owner\n'
        ),
        (
            '        self._operator_read: Any = None\n        self._operator_r'
            'ead_drained: Any = None\n        self.operator_worker_debt = 0\n  '
            '      # The actual adapter retains the owner across reconnects. '
            'A standalone\n        # server without that owner never silently '
            'creates a replacement pool.\n        self._presentation_owner = p'
            'resentation_owner\n'
        ),
    ),
    (
        (
            '            log_event("identity_changed", outcome="listener_clos'
            'ed")\n            self._stopping = asyncio.get_running_loop().cre'
            'ate_task(self.stop())\n\n    async def wait_readiness_drain(self) '
            '-> None:\n        service = self.ctx.readiness_reads\n        if s'
            'ervice is None:\n            if self.readiness_worker_debt:\n     '
            '           raise RuntimeError("readiness drain unavailable")\n   '
            '         return\n        await service.wait_drained()\n\n    async '
            'def wait_operator_drain(self) -> None:\n        service = self._o'
            'perator_read_drained\n        if service is not None:\n'
        ),
        (
            '            log_event("identity_changed", outcome="listener_clos'
            'ed")\n            self._stopping = asyncio.get_running_loop().cre'
            'ate_task(self.stop())\n\n    async def wait_operator_drain(self) -'
            '> None:\n        service = self._operator_read_drained\n        if'
            ' service is not None:\n'
        ),
    ),
    (
        (
            '                    raise\n            except Exception:\n        '
            "        log_event('listener_start', outcome='unavailable')\n     "
            '   if self.ctx.readiness_reads is not None:\n            self.rea'
            'diness_worker_debt = self.ctx.readiness_reads.stop()\n        pre'
            'sentation = self._presentation_service\n        if presentation i'
            's not None:\n            self.presentation_worker_debt = not awai'
            't presentation.close_and_join()\n'
        ),
        (
            '                    raise\n            except Exception:\n        '
            "        log_event('listener_start', outcome='unavailable')\n     "
            '   presentation = self._presentation_service\n        if presenta'
            'tion is not None:\n            self.presentation_worker_debt = no'
            't await presentation.close_and_join()\n'
        ),
    ),
)

SERVER_9AB26958 = (
    (
        (
            '    direct_send,\n    media_emission,\n    media_fetch,\n    media_'
            'readiness,\n    mobile_cron,\n    mobile_model,\n    presentation_n'
            'ative_service,\n'
        ),
        (
            '    direct_send,\n    media_emission,\n    media_fetch,\n    mobile'
            '_cron,\n    mobile_model,\n    presentation_native_service,\n'
        ),
    ),
    (
        (
            '    ("GET", "/ready", "PR0-1"),\n    ("GET", "/readiness/capabili'
            'ties", "AR1"),\n    ("GET", "/bots/{p}/readiness", "AR1"),\n    ("'
            'GET", "/bots/{p}/media-readiness", "LM-ENT1"),\n    ("GET", "/med'
            'ia-readiness/capabilities", "LM-ENT1"),\n    ("POST", "/pair/requ'
            'est", "PR2"),\n    ("POST", "/pair/complete", "PR4"),\n    ("POST"'
            ', "/auth/token", "PR5"),\n'
        ),
        (
            '    ("GET", "/ready", "PR0-1"),\n    ("GET", "/readiness/capabili'
            'ties", "AR1"),\n    ("GET", "/bots/{p}/readiness", "AR1"),\n    ("'
            'POST", "/pair/request", "PR2"),\n    ("POST", "/pair/complete", "'
            'PR4"),\n    ("POST", "/auth/token", "PR5"),\n'
        ),
    ),
    (
        (
            '    }\n\n\ndef _collect_media_readiness(ctx: ServerContext, **scope'
            ": Any) -> dict[str, object]:\n    # Reuse AR1's authorization/dea"
            'dline fence, never its jobs/model entitlement.\n    authority = {'
            'key: scope[key] for key in (\n        "authorization", "instance"'
            ', "expected", "profile", "generation", "deadline",\n    )}\n    de'
            'f checkpoint() -> None:\n        _readiness_authority_check(ctx, '
            '**authority)\n    original_iid = ctx.iid\n    checkpoint()\n    dec'
            'ision = ctx.store.media_read_decision(ctx.iid, scope["device_id"'
            '])\n    if decision is None:\n        raise readiness.ReadinessUna'
            'vailableError()\n    decision.validate()\n    permission = ctx.med'
            'ia_read_permission(scope["device_id"])\n    expected_allowed = de'
            'cision.allowed is True\n    if decision.allowed is None:\n        '
            'owners = ctx.owner_device_ids()\n        if type(owners) is not f'
            'rozenset or any(type(item) is not str for item in owners):\n     '
            '       raise readiness.ReadinessUnavailableError()\n        expec'
            'ted_allowed = decision.fallback_controls is not False and scope['
            '"device_id"] in owners\n    # An operational reader failure is no'
            't evidence that an operator omitted rights.\n    if (permission i'
            's not None) is not expected_allowed:\n        raise readiness.Rea'
            'dinessUnavailableError()\n    entitlement = "granted" if expected'
            '_allowed else "missing"\n    if ctx.readiness_settings is None:\n '
            '       raise readiness.ReadinessUnavailableError()\n    setting ='
            ' media_readiness.host_setting(ctx.readiness_settings())\n    boun'
            'd = ctx.media_snapshot()\n    api = "available" if bound is not N'
            'one else "unavailable"\n    checkpoint()\n    # Refuse superseded '
            'per-device rights and host settings, including changes during ca'
            'llbacks.\n    if (ctx.store.media_read_decision(ctx.iid, scope["d'
            'evice_id"]) != decision\n            or ctx.media_read_permission'
            '(scope["device_id"]) != permission\n            or media_readines'
            's.host_setting(ctx.readiness_settings()) != setting):\n        ra'
            'ise readiness.ReadinessUnavailableError()\n    payload = media_re'
            'adiness.project(entitlement=entitlement, host=setting, api=api)\n'
            '    checked_at = _readiness_now(ctx)\n    checkpoint()\n    # The '
            'checkpoint invokes authorization callbacks. Sample its dependent'
            ' media\n    # state afterward; nothing authority-bearing may foll'
            'ow these comparisons.\n    if (ctx.store.media_read_decision(ctx.'
            'iid, scope["device_id"]) != decision\n            or ctx.media_re'
            'ad_permission(scope["device_id"]) != permission\n            or m'
            'edia_readiness.host_setting(ctx.readiness_settings()) != setting'
            '\n            or ctx.media_snapshot() != bound\n            or ctx'
            '.iid != original_iid\n            or ctx.readiness_generation != '
            'scope["generation"]):\n        raise readiness.ReadinessUnavailab'
            'leError()\n    return {"protocol": 1, "checked_at": checked_at,\n '
            '           "generation": scope["generation"], "media": payload,\n'
            '            "_authority": (decision, permission)}\n\n\nasync def ha'
            'ndle_media_readiness_capabilities(request: web.Request) -> web.R'
            'esponse:\n    _readiness_empty_get(request)\n    _readiness_bearer'
            '(request)\n    # Protocol support only: never an entitlement, hos'
            't opt-in, or file availability claim.\n    return web.Response(\n '
            '       body=wire.dump_json({"protocol": 1, "media_readiness": Tr'
            'ue,\n                             "remote_permission_write": Fals'
            'e}),\n        content_type="application/json", headers={"Cache-Co'
            'ntrol": "no-store"},\n    )\n\n\nasync def handle_media_readiness(re'
            'quest: web.Request) -> web.Response:\n    return await _handle_re'
            'adiness(request, media=True)\n\n\nasync def handle_readiness(reques'
            't: web.Request) -> web.Response:\n    return await _handle_readin'
            'ess(request, media=False)\n\n\nasync def _handle_readiness(request:'
            ' web.Request, *, media: bool) -> web.Response:\n    _readiness_em'
            'pty_get(request)\n    try:\n        ctx = context(request)\n    exc'
            'ept Exception:\n        raise HmpError(ErrorCode.READINESS_UNAVAI'
            'LABLE) from None\n    original_cohort = (ctx.identity, ctx.store,'
            ' ctx.bridge)\n    original_iid = ctx.iid\n    def media_context_cu'
            'rrent() -> bool:\n        return (context(request) is ctx\n       '
            '         and ctx.identity is original_cohort[0]\n                '
            'and ctx.store is original_cohort[1]\n                and ctx.brid'
            'ge is original_cohort[2]\n                and ctx.iid == original'
            '_iid\n                and ctx.readiness_generation == generation)'
            '\n    who = _readiness_bearer(request)\n    profile = request.matc'
            'h_info.get("p", "")\n    if _READINESS_PROFILE_RE.fullmatch(profi'
            'le) is None:\n'
        ),
        (
            '    }\n\n\nasync def handle_readiness(request: web.Request) -> web.'
            'Response:\n    _readiness_empty_get(request)\n    try:\n        ctx'
            ' = context(request)\n    except Exception:\n        raise HmpError'
            '(ErrorCode.READINESS_UNAVAILABLE) from None\n    who = _readiness'
            '_bearer(request)\n    profile = request.match_info.get("p", "")\n '
            '   if _READINESS_PROFILE_RE.fullmatch(profile) is None:\n'
        ),
    ),
    (
        (
            '    deadline = time.monotonic() + _READINESS_DEADLINE_S\n    try:'
            '\n        work = asyncio.create_task(asyncio.to_thread(\n         '
            '   _collect_media_readiness if media else _collect_readiness,\n  '
            '          ctx,\n            authorization=authorization,\n        '
            '    instance=instance,\n'
        ),
        (
            '    deadline = time.monotonic() + _READINESS_DEADLINE_S\n    try:'
            '\n        work = asyncio.create_task(asyncio.to_thread(\n         '
            '   _collect_readiness,\n            ctx,\n            authorizatio'
            'n=authorization,\n            instance=instance,\n'
        ),
    ),
    (
        (
            '    except Exception as exc:\n        log_handler_exception(exc)\n'
            '        raise HmpError(ErrorCode.READINESS_UNAVAILABLE) from Non'
            'e\n    if media:\n        if not media_context_current():\n        '
            '    raise HmpError(ErrorCode.READINESS_UNAVAILABLE)\n        # Fi'
            'nal synchronous authority/readback fence after the worker await.'
            ' Never await\n        # between this comparison and response cons'
            'truction. These authority readers can\n        # perform SQLite/n'
            'ative config I/O; this is not a nonblocking performance claim.\n '
            '       try:\n            current = _collect_media_readiness(\n    '
            '            ctx, authorization=authorization, instance=instance,'
            ' expected=who,\n                profile=profile, device_id=who.de'
            'vice_id, deadline=deadline,\n                generation=generatio'
            'n,\n            )\n            if (not media_context_current()\n   '
            '                 or current["media"] != payload["media"]\n       '
            '             or current["_authority"] != payload["_authority"]):'
            '\n                raise readiness.ReadinessUnavailableError()\n   '
            '     except HmpError:\n            raise\n        except Exception'
            ':\n            raise HmpError(ErrorCode.READINESS_UNAVAILABLE) fr'
            'om None\n        payload.pop("_authority")  # internal snapshot n'
            'ever enters the wire DTO\n    try:\n        body = wire.dump_json('
            'payload)\n    except Exception:\n'
        ),
        (
            '    except Exception as exc:\n        log_handler_exception(exc)\n'
            '        raise HmpError(ErrorCode.READINESS_UNAVAILABLE) from Non'
            'e\n    try:\n        body = wire.dump_json(payload)\n    except Exc'
            'eption:\n'
        ),
    ),
    (
        (
            '        "/ready": handle_ready,\n        "/readiness/capabilities'
            '": handle_readiness_capabilities,\n        "/bots/{p}/readiness":'
            ' handle_readiness,\n        "/bots/{p}/media-readiness": handle_m'
            'edia_readiness,\n        "/media-readiness/capabilities": handle_'
            'media_readiness_capabilities,\n        "/push/registration": push'
            '_registration.handle_push_get,\n        "/push/hints/resolve": pa'
            'rtial(\n            push_resolve.handle_push_resolve, require_gat'
            'e=_require_approvals_gate\n'
        ),
        (
            '        "/ready": handle_ready,\n        "/readiness/capabilities'
            '": handle_readiness_capabilities,\n        "/bots/{p}/readiness":'
            ' handle_readiness,\n        "/push/registration": push_registrati'
            'on.handle_push_get,\n        "/push/hints/resolve": partial(\n    '
            '        push_resolve.handle_push_resolve, require_gate=_require_'
            'approvals_gate\n'
        ),
    ),
)

def reverse_lifecycle_composition(source: str, name: str) -> str:
    """Preserve other bytes; refuse changed/duplicate selected blocks."""
    if name == 'adapter.py':
        stages = (ADAPTER_11A70F01, ADAPTER_7C528066,)
    elif name == 'server.py':
        stages = (SERVER_30DEDF99, SERVER_11A70F01, SERVER_9AB26958,)
    else:
        raise ValueError("unsupported composition source")
    for edits in stages:
        source = _reverse_exact_edits(source, edits)
    return source


def _reverse_exact_edits(source: str, edits: tuple[tuple[str, str], ...]) -> str:
    for accepted, previous in reversed(edits):
        assert source.count(accepted) == 1
        source = source.replace(accepted, previous, 1)
    return source
