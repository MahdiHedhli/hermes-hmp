"""Retained one-operation credential handshake; no production factory/admission.

This actor owns its original task/socket cursor and fixed four-record exchange.
Only a future independently admitted paired startup may construct it; key-file
readiness is not runtime qualification. Existing native phase/custody permissions
remain required. No generic signer or HBR1 operation is exposed here.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import secrets
import threading

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .presentation_broker_codec import BrokerBinding, _binding
from .presentation_broker_service import SocketChannel, StartupEnrollment
from .presentation_clock import ClockDomain, NativeClockOwner
from .presentation_credential_codec import decode_record, encode_record, payload_size, signing_bytes
from .presentation_credential_files import RoleKeySelection, StartupRoleKeyFiles, _HeldFile
from .presentation_credential_transcript import channel_digest, check_transcript
from .presentation_jobs import FrameError


_HANDSHAKE_IO_RELEASE = object()


class HandshakeAcquisitionError(FrameError):
    def __init__(self, owner):
        super().__init__("BI1_CREDENTIAL_HANDSHAKE_REFUSED")
        self.failed_owner = owner


def _require(value):
    if value is not True:
        raise FrameError("BI1_CREDENTIAL_HANDSHAKE_REFUSED")


def _typed_tuple(value, types):
    return (type(value) is tuple and len(value) == len(types)
            and all(type(item) is kind for item, kind in zip(value, types, strict=True)))


class CredentialHandshakeOwner:
    """Original actor retained even for partial/unknown writes; never retry."""
    @classmethod
    def retain(cls, channel, keys, binding, work_end_ns):
        _require(cls is CredentialHandshakeOwner and type(channel) is SocketChannel)
        _require(getattr(channel, "_credential_handshake", None) is None
                 and getattr(channel, "_credential_handshake_snapshot", None) is None)
        owner = cls.__new__(cls)
        owner._original_channel = channel
        channel._credential_handshake = channel._credential_handshake_snapshot = owner  # before initialization/effects
        try:
            owner.__init__(channel, keys, binding, work_end_ns)
        except BaseException:
            raise HandshakeAcquisitionError(owner) from None
        return owner

    def __init__(self, channel, keys, binding, work_end_ns):
        if type(self) is not CredentialHandshakeOwner or "_initialized" in vars(self):
            raise HandshakeAcquisitionError(self) from None
        self._initialized = False
        self._refused = False
        self._started = self._complete = self._io_unknown = False
        self._records = self._records_origin = []
        self._write_intents = self._write_intents_origin = []
        self._write_complete = self._write_complete_origin = []
        self._records_values = self._intents_values = self._complete_values = ()
        self._cursor = self._cursor_origin = bytearray()
        self._cursor_values = b""
        self._wire_bytes = self._wire_bytes_snapshot = 0
        self._release_fact = None
        self._channel = channel
        self._keys = keys
        self._binding = self._binding_snapshot = binding
        self._task = asyncio.current_task()
        self._loop = asyncio.get_running_loop()
        self._context = (os.getpid(), os.geteuid(), threading.get_ident())
        _require(type(channel) is SocketChannel and getattr(self, "_original_channel", None) is channel
                 and channel._credential_handshake is self
                 and channel._credential_handshake_snapshot is self
                 and type(keys) is StartupRoleKeyFiles and type(binding) is BrokerBinding)
        _binding(binding)
        self._binding_values = (binding.iid, binding.listener, binding.broker, binding.channel, binding.operation)
        self._socket = channel._socket_snapshot
        self._channel_values = channel._values_snapshot
        self._channel_identity = channel._identity_snapshot
        self._key = self._key_origin = keys._private_key
        self._selection = self._selection_origin = keys._selection
        _require(type(self._selection) is RoleKeySelection and keys._ready is True
                 and keys._refused is False and isinstance(self._key, Ed25519PrivateKey))
        self._selection_values = (self._selection.directory, self._selection.role,
            self._selection.generation, self._selection.own_public, self._selection.peer_public)
        self._boot = keys._boot
        self._clock = self._clock_origin = SocketChannel._qualified_clock(channel)
        _require(type(self._clock) is NativeClockOwner)
        self._domain = self._clock._domain_snapshot
        _require(type(self._domain) is ClockDomain)
        domain = self._domain
        self._domain_values = (domain.platform, domain.implementation, domain.boot, domain.namespace)
        now = NativeClockOwner.sample(self._clock)
        # Constructor is not initialized: validate primitives before equality.
        _require(type(self._selection) is RoleKeySelection and self._selection is self._selection_origin
                 and self._key is self._key_origin and type(domain) is ClockDomain
                 and self._domain is domain and type(self._clock) is NativeClockOwner
                 and self._clock is self._clock_origin
                 and type(self._domain_values) is tuple and len(self._domain_values) == 4
                 and _typed_tuple(self._domain_values[:3], (str, str, bytes))
                 and (self._domain_values[3] is None or _typed_tuple(self._domain_values[3], (int, int))))
        _require(all(type(item) is str for item in (self._selection.directory,
                     self._selection.role, self._selection.generation))
                 and type(self._selection.own_public) is bytes
                 and type(self._selection.peer_public) is bytes
                 and type(domain.platform) is str and type(domain.implementation) is str
                 and type(domain.boot) is bytes
                 and (domain.namespace is None or _typed_tuple(domain.namespace, (int, int))))
        _require(keys._ready is True and keys._refused is False
                 and keys._private_key is self._key and keys._selection is self._selection
                 and self._clock._domain_snapshot is self._domain
                 and (domain.platform, domain.implementation, domain.boot, domain.namespace) == self._domain_values)
        _require(type(now) is int and type(work_end_ns) is int and now < work_end_ns <= now + 2_000_000_000)
        self._end = work_end_ns
        self._accept_end = self._accept_end_snapshot = work_end_ns
        self._role = channel._role_snapshot
        domain = self._clock._domain_snapshot
        raw = json.dumps(dict(platform=domain.platform, implementation=domain.implementation,
            boot=domain.boot.decode("ascii"), namespace=domain.namespace),
            sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
        self._common = dict(iid=binding.iid, listener=binding.listener,
            generation=self._selection.generation, clock_domain=hashlib.sha256(raw).hexdigest(),
            operation_id=binding.operation, work_end_ns=work_end_ns)
        nonce = secrets.token_bytes(32)
        _require(type(nonce) is bytes and len(nonce) == 32)
        self._nonce = nonce.hex()
        _require(self._nonce != self._boot)
        self._common_snapshot = self._common
        self._common_values = tuple(sorted(self._common.items()))
        self._initialized = True
        self._guard()

    def __repr__(self):
        return "<CredentialHandshakeOwner credentials-and-payload-redacted>"

    def _local_seal(self):
        # Reject foreign local metadata before equality/sort/truthiness may call
        # methods. This is a post-native-boundary fence, not a memory sandbox.
        _require(type(self) is CredentialHandshakeOwner
                 and type(self._original_channel) is SocketChannel
                 and self._channel is self._original_channel)
        _require(type(self._context) is tuple and len(self._context) == 3
                 and all(type(item) is int for item in self._context))
        _require(type(self._common) is dict and self._common is self._common_snapshot
                 and len(self._common) == 6 and all(type(key) is str for key in self._common))
        _require(self._common.keys() == {"iid", "listener", "generation", "clock_domain", "operation_id", "work_end_ns"})
        _require(all(type(value) is (int if key == "work_end_ns" else str)
                     for key, value in self._common.items())
                 and 0 < self._common["work_end_ns"] < 1 << 63)
        _require(type(self._common_values) is tuple and len(self._common_values) == 6
                 and all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                         and type(row[1]) is (int if row[0] == "work_end_ns" else str)
                         for row in self._common_values))
        _require(type(self._selection) is RoleKeySelection and self._selection is self._selection_origin
                 and self._key is self._key_origin and self._clock is self._clock_origin
                 and type(self._domain) is ClockDomain)
        _require(_typed_tuple(self._selection_values, (str, str, str, bytes, bytes))
                 and _typed_tuple(self._binding_values, (str,) * 5)
                 and _typed_tuple(self._channel_values, (str, str, str, int, int, int, int, str, int))
                 and type(self._domain_values) is tuple and len(self._domain_values) == 4
                 and _typed_tuple(self._domain_values[:3], (str, str, bytes))
                 and (self._domain_values[3] is None or _typed_tuple(self._domain_values[3], (int, int)))
                 and type(self._cursor_values) is bytes and len(self._cursor_values) <= 2048)
        selected = self._selection
        _require(all(type(value) is str for value in (selected.directory, selected.role, selected.generation))
                 and type(selected.own_public) is bytes and type(selected.peer_public) is bytes)
        domain = self._domain
        _require(type(domain.platform) is str and type(domain.implementation) is str
                 and type(domain.boot) is bytes
                 and (domain.namespace is None or (type(domain.namespace) is tuple
                      and len(domain.namespace) == 2 and all(type(item) is int for item in domain.namespace))))
        _require(type(self._keys) is StartupRoleKeyFiles and type(self._keys._records) is list
                 and len(self._keys._records) <= 68
                 and all(type(record) is _HeldFile and record.closed is True
                         and record.close_attempted is True and record.unknown is False
                         for record in self._keys._records)
                 and type(self._keys._boot) is str and type(self._boot) is str
                 and type(self._keys._process) is tuple and len(self._keys._process) == 2
                 and all(type(item) is int for item in self._keys._process))
        _require(type(self._role) is str and type(self._original_channel._role_snapshot) is str
                 and type(self._binding) is BrokerBinding)
        _require(all(type(value) is str for value in (self._binding.iid, self._binding.listener,
                   self._binding.broker, self._binding.channel, self._binding.operation)))
        for values, limit in ((self._records, 4), (self._write_intents, 2), (self._write_complete, 2)):
            _require(type(values) is list and len(values) <= limit
                     and all(type(raw) is bytes and len(raw) <= 2048 for raw in values))
        for snapshot, limit in ((self._records_values, 4), (self._intents_values, 2), (self._complete_values, 2)):
            _require(type(snapshot) is tuple and len(snapshot) <= limit
                     and all(type(raw) is bytes and len(raw) <= 2048 for raw in snapshot))
        _require(self._initialized is True and self._refused is False and self._io_unknown is False)
        _require(self._context == (os.getpid(), os.geteuid(), threading.get_ident())
                 and asyncio.current_task() is self._task and type(self._task) is asyncio.Task
                 and self._task.cancelling() == 0
                 and asyncio.get_running_loop() is self._loop
                 and type(self._loop) is asyncio.SelectorEventLoop
                 and self._loop.get_task_factory() is None)
        channel, keys = self._channel, self._keys
        _require(type(channel) is SocketChannel and channel._credential_handshake is self
                 and channel._credential_handshake_snapshot is self
                 and channel._socket_snapshot is self._socket
                 and channel._values_snapshot is self._channel_values
                 and channel._identity_snapshot is self._channel_identity
                 and channel._role_snapshot == self._role
                 and channel._reading is False and channel._writing is False
                 and channel._terminal_owner is None
                 and channel._begin_write_intent is None)
        _require(type(keys) is StartupRoleKeyFiles and keys._ready is True
                 and keys._refused is False and keys._private_key is self._key
                 and keys._selection is self._selection and keys._boot == self._boot
                 and keys._process == self._context[:2]
                 and all(record.closed for record in keys._records))
        _require(type(self._selection) is RoleKeySelection
                 and type(self._clock) is NativeClockOwner
                 and self._clock._domain_snapshot is self._domain
                 and type(self._domain) is ClockDomain
                 and (self._domain.platform, self._domain.implementation,
                      self._domain.boot, self._domain.namespace) == self._domain_values)
        selected = self._selection
        _require((selected.directory, selected.role, selected.generation,
                  selected.own_public, selected.peer_public) == self._selection_values
                 and selected.role == self._role
                 and selected.generation == self._channel_values[7])
        _require(self._binding is self._binding_snapshot
                 and (self._binding.iid, self._binding.listener, self._binding.broker,
                      self._binding.channel, self._binding.operation) == self._binding_values
                 and self._common is self._common_snapshot
                 and tuple(sorted(self._common.items())) == self._common_values)
        _require(type(channel._enrollment) is StartupEnrollment
                 and channel._enrollment is channel._enrollment_snapshot)
        scope = channel._enrollment.scope
        _require(type(scope) is BrokerBinding
                 and all(type(item) is str for item in (scope.iid, scope.listener, scope.broker)))
        _require((self._binding.iid, self._binding.listener, self._binding.broker)
                 == (scope.iid, scope.listener, scope.broker))
        _require(self._records is self._records_origin and type(self._records) is list
                 and self._write_intents is self._write_intents_origin
                 and type(self._write_intents) is list
                 and self._write_complete is self._write_complete_origin
                 and type(self._write_complete) is list
                 and len(self._records) <= 4 and len(self._write_intents) <= 2
                 and len(self._write_complete) <= 2
                 and tuple(self._records) == self._records_values
                 and tuple(self._write_intents) == self._intents_values
                 and tuple(self._write_complete) == self._complete_values
                 and self._cursor is self._cursor_origin and type(self._cursor) is bytearray
                 and len(self._cursor) <= 2048 and bytes(self._cursor) == self._cursor_values
                 and type(self._wire_bytes) is int and self._wire_bytes is self._wire_bytes_snapshot
                 and 0 <= self._wire_bytes <= 8192
                 and type(self._accept_end) is int and self._accept_end is self._accept_end_snapshot
                 and type(self._end) is int
                 and self._end == min(self._accept_end, self._common["work_end_ns"]))

    def _guard(self):
        self._local_seal()
        SocketChannel._check(self._channel)
        _require(SocketChannel._qualified_clock(self._channel) is self._clock)
        now = NativeClockOwner.sample(self._clock)
        self._local_seal()  # no final native clock callback may bypass retirement/cursor fences
        _require(type(now) is int and now < self._end)

    def _released(self, channel):
        # Historical local IO closure only, not permission for any HBR1 phase.
        _require(type(self) is CredentialHandshakeOwner and type(channel) is SocketChannel
                 and self._original_channel is channel and self._channel is channel
                 and channel._credential_handshake is self
                 and channel._credential_handshake_snapshot is self
                 and type(self._records) is list and self._records is self._records_origin
                 and len(self._records) == 4
                 and all(type(raw) is bytes and len(raw) <= 2048 for raw in self._records)
                 and type(self._write_complete) is list and self._write_complete is self._write_complete_origin
                 and len(self._write_complete) == 2
                 and type(self._write_intents) is list and self._write_intents is self._write_intents_origin
                 and len(self._write_intents) == 2
                 and all(type(raw) is bytes and len(raw) <= 2048
                         for raw in (*self._write_complete, *self._write_intents))
                 and type(self._cursor) is bytearray and self._cursor is self._cursor_origin
                 and self._complete is True and self._io_unknown is False
                 and self._release_fact is _HANDSHAKE_IO_RELEASE
                 and len(self._write_complete) == 2
                 and self._write_complete == self._write_intents
                 and len(self._records) == 4 and not self._cursor)

    async def _send(self):
        self._guard()
        _require(self._started is True and self._complete is False)
        index = len(self._records)
        if self._role == "gateway" and index == 0:
            phase = "HELLO"
            extra = dict(gateway_boot=self._boot, gateway_nonce=self._nonce)
        elif self._role == "broker" and index == 1:
            phase = "CHALLENGE"
            hello = json.loads(decode_record(self._records[0]).canonical_json)
            _require(len({hello["gateway_boot"], hello["gateway_nonce"], self._boot, self._nonce}) == 4)
            extra = dict(gateway_boot=hello["gateway_boot"], gateway_nonce=hello["gateway_nonce"],
                         broker_boot=self._boot, broker_nonce=self._nonce,
                         hello_sha256=hashlib.sha256(self._records[0]).hexdigest())
        elif self._role == "gateway" and index == 2:
            phase = "FINISH"
            challenge = json.loads(decode_record(self._records[1]).canonical_json)
            _require(len({self._boot, self._nonce, challenge["broker_boot"], challenge["broker_nonce"]}) == 4)
            extra = dict(gateway_boot=self._boot, broker_boot=challenge["broker_boot"],
                         channel=channel_digest(*self._records),
                         hello_sha256=hashlib.sha256(self._records[0]).hexdigest(),
                         challenge_sha256=hashlib.sha256(self._records[1]).hexdigest())
        elif self._role == "broker" and index == 3:
            phase = "ACCEPT"
            hello = json.loads(decode_record(self._records[0]).canonical_json)
            finish = json.loads(decode_record(self._records[2]).canonical_json)
            extra = dict(gateway_boot=hello["gateway_boot"], broker_boot=self._boot,
                         channel=finish["channel"], finish_sha256=hashlib.sha256(self._records[2]).hexdigest())
        else:
            _require(False)
        _require(len(self._write_intents) < 2)
        selected = self._selection
        value = dict(self._common, v=1, family="handshake", alg="Ed25519", phase=phase,
            role=self._role, direction="g2b" if self._role == "gateway" else "b2g",
            key_id=hashlib.sha256(selected.own_public).hexdigest(),
            peer_key_id=hashlib.sha256(selected.peer_public).hexdigest(), **extra)
        raw = encode_record(value, self._key.sign(signing_bytes(value)))
        self._guard()
        self._write_intents.append(raw)  # before possibly partial write
        self._intents_values = tuple(self._write_intents)
        self._wire_bytes = self._wire_bytes_snapshot = self._wire_bytes + len(raw)
        _require(self._wire_bytes <= 8192)
        async with asyncio.timeout_at(self._end / 1e9):
            self._guard()
            await self._loop.sock_sendall(self._socket, raw)
        self._guard()
        self._write_complete.append(raw)
        self._complete_values = tuple(self._write_complete)
        self._records.append(raw)
        self._records_values = tuple(self._records)
        return value

    async def _receive(self, phase):
        self._guard()
        expected = {("broker", 0): "HELLO", ("gateway", 1): "CHALLENGE",
                    ("broker", 2): "FINISH", ("gateway", 3): "ACCEPT"}
        _require(self._started is True and self._complete is False
                 and phase == expected.get((self._role, len(self._records))) and not self._cursor)
        async def exact(count):
            while len(self._cursor) < count:
                self._guard()
                async with asyncio.timeout_at(self._end / 1e9):
                    self._guard()
                    data = await self._loop.sock_recv(self._socket, count - len(self._cursor))
                self._guard()
                _require(type(data) is bytes and 0 < len(data) <= count - len(self._cursor))
                self._cursor.extend(data)
                self._cursor_values = bytes(self._cursor)
                self._wire_bytes = self._wire_bytes_snapshot = self._wire_bytes + len(data)
                _require(self._wire_bytes <= 8192)
        await exact(8)
        size = payload_size(bytes(self._cursor))
        await exact(8 + size)
        raw = bytes(self._cursor)
        parsed = decode_record(raw)
        value = json.loads(parsed.canonical_json)
        peer = "broker" if self._role == "gateway" else "gateway"
        fixed = self._common
        if self._role == "broker" and phase == "HELLO":
            # Signed operation/deadline are staged metadata, not native input or
            # registry admission. Original accept end can only become earlier.
            fixed = {key: item for key, item in fixed.items()
                     if key not in ("operation_id", "work_end_ns")}
        _require(value["family"] == "handshake" and value["phase"] == phase and value["role"] == peer
                 and all(value[name] == item for name, item in fixed.items()))
        selected = self._selection
        _require(value["key_id"] == hashlib.sha256(selected.peer_public).hexdigest()
                 and value["peer_key_id"] == hashlib.sha256(selected.own_public).hexdigest())
        try:
            Ed25519PublicKey.from_public_bytes(selected.peer_public).verify(parsed.signature, parsed.signing_data)
        except (InvalidSignature, ValueError):
            _require(False)
        self._guard()
        if self._role == "broker" and phase == "HELLO":
            now = NativeClockOwner.sample(self._clock)
            self._local_seal()
            _require(type(now) is int and now < value["work_end_ns"] <= now + 2_000_000_000)
            self._end = min(self._accept_end, value["work_end_ns"])
            self._common = dict(self._common, operation_id=value["operation_id"],
                                work_end_ns=value["work_end_ns"])
            self._common_snapshot = self._common
            self._common_values = tuple(sorted(self._common.items()))
            self._guard()
        self._cursor.clear()
        self._cursor_values = b""
        self._records.append(raw)
        self._records_values = tuple(self._records)
        return value

    async def run(self):
        """Exactly one fixed bilateral exchange; success grants no BEGIN/GO."""
        try:
            self._guard()
            _require(self._started is False and not self._records)
            self._started = True
            if self._role == "gateway":
                await self._send()
                challenge = await self._receive("CHALLENGE")
                _require(challenge["gateway_boot"] == self._boot and challenge["gateway_nonce"] == self._nonce
                         and challenge["hello_sha256"] == hashlib.sha256(self._records[0]).hexdigest())
                await self._send()
                await self._receive("ACCEPT")
            else:
                hello = await self._receive("HELLO")
                await self._send()
                finish = await self._receive("FINISH")
                # Validate FINISH links before signing ACCEPT, not only at end.
                _require(finish["gateway_boot"] == hello["gateway_boot"] and finish["broker_boot"] == self._boot
                         and finish["channel"] == channel_digest(*self._records[:2])
                         and finish["hello_sha256"] == hashlib.sha256(self._records[0]).hexdigest()
                         and finish["challenge_sha256"] == hashlib.sha256(self._records[1]).hexdigest())
                await self._send()
            self._guard()
            selected = self._selection
            public = dict(gateway=selected.own_public if self._role == "gateway" else selected.peer_public,
                          broker=selected.peer_public if self._role == "gateway" else selected.own_public)
            result = check_transcript(tuple(self._records), gateway_public=public["gateway"],
                                      broker_public=public["broker"], expected_context=self._common)
            _require(len(self._write_complete) == 2 and self._write_complete == self._write_intents)
            self._guard()
            self._complete = True
            self._release_fact = _HANDSHAKE_IO_RELEASE
            return result
        except BaseException:
            self._refused = self._io_unknown = True
            original = self._original_channel
            if (type(original) is SocketChannel
                    and original._credential_handshake is self
                    and original._credential_handshake_snapshot is self):
                original._refused = True
            raise
