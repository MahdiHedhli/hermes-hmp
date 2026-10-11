"""Private RP03 plaintext reader for an already owned TLS connection.

No connection, TLS context, credential or listener authority is created here.
The injected port is unbound in product code.  This module is source-only until
the selected Linux runtime, ownership bridge and process custody are reviewed.
"""

from __future__ import annotations

import math
import re
from functools import wraps


class RefusedError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


Refused = RefusedError


class _CleanEOF:
    pass


CLEAN_EOF = _CleanEOF()
_FIELD_NAME = re.compile(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")


def require(ok, code):
    if not ok:
        raise Refused(code)


def _reader_flight(method):
    @wraps(method)
    def checked(self, *args, **kwargs):
        self.assert_live()
        if self.operation is not None:
            error = Refused("REENTRANT_FLIGHT")
            self.poison("KNOWN_REFUSAL", error)
            raise error
        token = object()
        self.operation = token
        try:
            result = method(self, *args, **kwargs)
            self.assert_live()
            require(self.operation is token, "OPERATION_REPLACED")
            return result
        except BaseException as error:
            self.poison("KNOWN_REFUSAL", error)
            raise
        finally:
            self.operation = None

    return checked


class UnboundAuthority:
    """Default real authority binding: unavailable until separately qualified.

    A runtime binding must implement the root-reviewed coherent checkpoint
    contract. Protocol shape is not evidence of authority. No runtime binding
    or sequential owner/clock fallback is provided by this source packet.
    """

    def checkpoint(self, deadline):
        raise Refused("AUTHORITY_UNBOUND")


class BoundedFile:
    """Exact-fill reads over a preowned decrypted port; no hidden readahead."""

    def __init__(self, port, ledger, *, deadline, body_limit, authority=None):
        require(
            callable(getattr(port, "recv", None)) and callable(getattr(port, "close", None)),
            "PORT_UNBOUND",
        )
        require(callable(getattr(ledger, "reserve_read", None)), "LEDGER_UNBOUND")
        authority = UnboundAuthority() if authority is None else authority
        require(callable(getattr(authority, "checkpoint", None)), "AUTHORITY_UNBOUND")
        require(
            type(deadline) in (int, float) and math.isfinite(deadline) and deadline > 0, "DEADLINE"
        )
        require(type(body_limit) is int and 0 <= body_limit <= 65536, "BODY_LIMIT")
        self.port, self.ledger, self.authority = port, ledger, authority
        self.deadline = deadline
        self.last_now = None
        self.body_limit = body_limit
        self.framing_limit = 8192
        self.mode = "framing"
        self.line_kind = "status"
        self.received = self.framing = self.body = self.calls = self.capacity = 0
        self.closed = self.close_unknown = self.read_unknown = self.clean_eof = False
        self.first_failure = None
        self.failure_kind = None
        self.in_callback = False
        self.operation = None
        self.response_operation = None

    def poison(self, kind, error):
        if self.first_failure is None:
            self.first_failure = error
            self.failure_kind = kind

    def assert_live(self):
        require(self.first_failure is None, "FLIGHT_TERMINAL")

    def _private_entry(self):
        self.assert_live()
        if self.operation is None or self.in_callback:
            error = Refused("REENTRANT_FLIGHT")
            self.poison("KNOWN_REFUSAL", error)
            raise error

    def _callback(self, fn, *args):
        self._private_entry()
        tokens = (self.operation, self.response_operation)
        self.in_callback = True
        try:
            value = fn(*args)
        finally:
            self.in_callback = False
        self.assert_live()
        if self.operation is not tokens[0] or self.response_operation is not tokens[1]:
            error = Refused("OPERATION_REPLACED")
            self.poison("KNOWN_REFUSAL", error)
            raise error
        return value

    def _checkpoint(self):
        # This check deliberately works after a known local close. It is a
        # point-in-time authority observation, not a lease over later IO.
        self.assert_live()
        if (self.operation is None and self.response_operation is None) or self.in_callback:
            error = Refused("REENTRANT_FLIGHT")
            self.poison("KNOWN_REFUSAL", error)
            raise error
        tokens = (self.operation, self.response_operation)
        self.in_callback = True
        try:
            now = self.authority.checkpoint(self.deadline)
        finally:
            self.in_callback = False
        self.assert_live()
        require(
            self.operation is tokens[0] and self.response_operation is tokens[1],
            "OPERATION_REPLACED",
        )
        require(
            type(now) in (int, float) and math.isfinite(now) and 0 <= now < self.deadline,
            "DEADLINE",
        )
        require(self.last_now is None or now >= self.last_now, "CLOCK_REGRESSION")
        self.last_now = now
        return now

    def _fence(self):
        self._private_entry()
        require(not self.closed and not self.close_unknown and not self.read_unknown, "CLOSED")
        return self._checkpoint()

    @_reader_flight
    def set_mode(self, mode):
        require(mode in ("framing", "body"), "MODE")
        self._fence()
        self.mode = mode

    def _receive(self, want, *, eof_probe=False):
        self._private_entry()
        now = self._fence()
        # A previously accepted clean EOF is a terminal transport fact.
        # Reuse it without reserving capacity or invoking the port again.
        if self.clean_eof:
            return b""
        require(type(want) is int and 1 <= want <= 4096, "READ_SIZE")
        remain = (
            self.framing_limit - self.framing
            if self.mode == "framing"
            else self.body_limit - self.body
        )
        if remain <= 0:
            require(eof_probe and self.mode == "body", "READ_CREDIT")
            count = 1
        else:
            count = min(want, remain, 4096)
        # reserve_read charges caller capacity and one IO call before blocking;
        # short reads do not refund either reservation.
        self._callback(self.ledger.reserve_read, count)
        self.calls += 1
        self.capacity += count
        # Reservation may change authority or consume the remaining deadline.
        # Its already charged debt is retained if this checkpoint refuses.
        now = self._fence()
        try:
            value = self._callback(self.port.recv, count, min(self.deadline - now, 15.0))
        except BaseException as error:
            # The callback may have consumed bytes; no refund or second read.
            self.read_unknown = True
            self.poison("UNCERTAIN_IO", error)
            raise
        try:
            self._fence()
            if value is CLEAN_EOF:
                self.clean_eof = True
                return b""
            require(type(value) is bytes and 0 < len(value) <= count, "UNCLEAN_OR_INVALID_READ")
            self.received += len(value)
            require(self.received <= self.body_limit + self.framing_limit, "PLAINTEXT_CAP")
            if eof_probe:
                raise Refused("BODY_CAP_NO_EOF")
            if self.mode == "framing":
                self.framing += len(value)
                require(self.framing <= self.framing_limit, "FRAMING_CAP")
            else:
                self.body += len(value)
                require(self.body <= self.body_limit, "BODY_CAP")
            return value
        except BaseException as error:
            # A returned callback still has an uncertain post-read acceptance.
            if not (isinstance(error, Refused) and error.code == "BODY_CAP_NO_EOF"):
                self.read_unknown = True
                self.poison("UNCERTAIN_IO", error)
            else:
                self.poison("KNOWN_REFUSAL", error)
            raise

    @_reader_flight
    def readline(self, limit):
        # CPython 3.14.6 HTTPResponse uses _MAXLINE+1, exactly 65537.
        require(type(limit) is int and 1 <= limit <= 65537, "LINE_LIMIT")
        require(self.mode == "framing", "LINE_MODE")
        out = bytearray()
        while len(out) < limit:
            require(self.framing < self.framing_limit, "FRAMING_CAP")
            part = self._receive(1)
            if not part:
                raise Refused("FRAMING_EOF")
            out.extend(part)
            if len(out) == 1:
                require(part not in (b" ", b"\t"), "FOLDED_LINE")
            if part == b"\n":
                require(len(out) >= 2 and out[-2:] == b"\r\n", "LINE_CRLF")
                line = bytes(out)
                if self.line_kind in ("headers", "trailer"):
                    if line == b"\r\n":
                        self.line_kind = "status"
                    else:
                        name, colon, value = line[:-2].partition(b":")
                        require(
                            colon == b":"
                            and _FIELD_NAME.fullmatch(name) is not None
                            and all(
                                byte == 9 or 32 <= byte <= 126 or 128 <= byte <= 255
                                for byte in value
                            ),
                            "HEADER_LINE",
                        )
                elif self.line_kind == "status":
                    require(line.startswith(b"HTTP/"), "STATUS_LINE")
                    self.line_kind = "headers"
                self._checkpoint()
                return line
        raise Refused("LINE_UNTERMINATED")

    @_reader_flight
    def read(self, amount):
        return self._read_core(amount)

    def _read_core(self, amount):
        self._private_entry()
        require(type(amount) is int and 0 <= amount <= 4096, "READ_SIZE")
        self._fence()
        out = bytearray()
        while len(out) < amount:
            part = self._receive(
                amount - len(out), eof_probe=self.mode == "body" and self.body == self.body_limit
            )
            if not part:
                break
            out.extend(part)
        self._checkpoint()
        return bytes(out)

    @_reader_flight
    def readinto(self, buffer):
        require(
            type(buffer) in (bytearray, memoryview) and 0 <= len(buffer) <= 4096, "READINTO_SIZE"
        )
        require(type(buffer) is bytearray or not buffer.readonly, "READINTO_READONLY")
        if type(buffer) is memoryview:
            require(
                buffer.ndim == 1
                and buffer.itemsize == 1
                and buffer.format in ("B", "b")
                and buffer.c_contiguous,
                "READINTO_LAYOUT",
            )
        value = self._read_core(len(buffer))
        buffer[: len(value)] = value
        return len(value)

    def close(self):
        # This is the public cleanup entry. Parser cleanup uses _parser_close
        # while its response operation is still owned. A callback cannot close
        # underneath a read and let that read debit or receive again.
        if self.operation is not None or self.response_operation is not None or self.in_callback:
            error = Refused("REENTRANT_FLIGHT")
            self.poison("KNOWN_REFUSAL", error)
            raise error
        token = object()
        self.operation = token
        try:
            self._close_core()
        except BaseException as error:
            self.poison("KNOWN_REFUSAL", error)
            raise
        finally:
            self.operation = None

    def _parser_close(self, token):
        if self.response_operation is not token or self.operation is not None or self.in_callback:
            error = Refused("REENTRANT_FLIGHT")
            self.poison("KNOWN_REFUSAL", error)
            raise error
        self._close_core()

    def _close_core(self):
        require(not self.close_unknown, "CLOSE_UNKNOWN")
        if self.closed:
            return
        previous = self.first_failure
        tokens = (self.operation, self.response_operation)
        self.closed = True  # clear ownership before the one close attempt
        self.in_callback = True
        try:
            self.port.close()
        except BaseException as error:
            self.close_unknown = True
            self.poison("UNCERTAIN_CLOSE", error)
            raise
        finally:
            self.in_callback = False
        require(
            self.operation is tokens[0] and self.response_operation is tokens[1],
            "OPERATION_REPLACED",
        )
        if previous is None:
            self.assert_live()
            self._checkpoint()

    def flush(self):
        # HTTPResponse.close calls IOBase.close -> flush. This is a read-only
        # facade; no transport write or implicit close occurs here.
        return None


class AdapterSocket:
    """One-use makefile facade for the exact already established TLS object."""

    def __init__(self, bounded_file):
        require(type(bounded_file) is BoundedFile, "FILE_BINDING")
        self.file = bounded_file
        self.used = False

    def makefile(self, mode):
        require(mode == "rb" and not self.used, "MAKEFILE_REUSE")
        self.used = True
        return self.file


def strict_response_type(http):
    """Source-pinned CPython 3.14.6 parser hooks, injected for inert tests."""
    require(
        getattr(http, "_MAXLINE", None) == 65536
        and getattr(http, "HTTPResponse", None) is not None,
        "HTTP_PARSER_UNBOUND",
    )

    def assert_response_private(response):
        bounded = response.bounded
        if bounded.response_operation is None or bounded.in_callback:
            error = Refused("REENTRANT_RESPONSE_PRIVATE")
            bounded.poison("KNOWN_REFUSAL", error)
            response.completion = None
            raise error
        bounded.assert_live()

    def response_flight(method):
        @wraps(method)
        def checked(self, *args, **kwargs):
            assert_response_private(self)
            try:
                result = method(self, *args, **kwargs)
                self.bounded.assert_live()
                return result
            except BaseException as error:
                self.bounded.poison("KNOWN_SEMANTIC", error)
                self.completion = None
                raise

        return checked

    def response_public(method, *, cleanup=False):
        @wraps(method)
        def checked(self, *args, **kwargs):
            bounded = self.bounded
            if bounded.response_operation is not None or bounded.in_callback:
                error = Refused("REENTRANT_RESPONSE")
                bounded.poison("KNOWN_REFUSAL", error)
                self.completion = None
                raise error
            token = object()
            bounded.response_operation = token
            try:
                if not cleanup:
                    bounded._checkpoint()
                result = method(self, *args, **kwargs)
                require(bounded.response_operation is token, "RESPONSE_OPERATION_REPLACED")
                if not cleanup:
                    bounded.assert_live()
                return result
            except BaseException as error:
                bounded.poison("KNOWN_SEMANTIC", error)
                self.completion = None
                raise
            finally:
                bounded.response_operation = None

        return checked

    def response_cleanup(method):
        return response_public(method, cleanup=True)

    class StrictResponse(http.HTTPResponse):
        @property
        def completion(self):
            # A reader-side refusal also invalidates any earlier completion.
            return None if self.bounded.first_failure is not None else self._completion

        @completion.setter
        def completion(self, value):
            self._completion = value

        def __init__(self, sock, *, body_limit, method="GET"):
            require(type(sock) is AdapterSocket and method == "GET", "RESPONSE_BINDING")
            self.bounded = sock.file
            self.body_limit = body_limit
            self.completion = None
            self.framing_kind = None
            self.expected_length = None
            self.final_chunk_seen = False
            self.trailer_complete = False
            super().__init__(sock, method=method)

        @response_flight
        def _read_status(self):
            self.bounded.set_mode("framing")
            version, status, reason = super()._read_status()
            reason = reason.rstrip("\r\n")
            require(
                version in ("HTTP/1.0", "HTTP/1.1")
                and type(status) is int
                and 100 <= status <= 599
                and not any(ord(char) < 32 or ord(char) == 127 for char in reason),
                "STATUS",
            )
            require(status == 100 or status >= 200, "INTERIM_STATUS")
            return version, status, reason

        @response_public
        def begin(self):
            require(self.headers is None, "RESPONSE_REUSE")
            super().begin()  # tagged parser reads only status/headers here
            require(self.status != 101, "SWITCHING_PROTOCOL")
            headers = self.headers
            lengths = headers.get_all("content-length", [])
            transfers = headers.get_all("transfer-encoding", [])
            require(
                len(lengths) <= 1 and len(transfers) <= 1 and not (lengths and transfers),
                "AMBIGUOUS_FRAMING",
            )
            if lengths:
                raw = lengths[0]
                require(
                    type(raw) is str and 1 <= len(raw) <= 5 and raw.isascii() and raw.isdecimal(),
                    "CONTENT_LENGTH",
                )
                require(raw == str(int(raw)) and int(raw) <= self.body_limit, "CONTENT_LENGTH")
                require(self.status not in (204, 304) or int(raw) == 0, "NO_BODY_LENGTH")
                self.length = int(raw)
                self.expected_length = self.length
                self.chunked = False
                self.framing_kind = "content-length"
            elif transfers:
                require(self.status not in (204, 304), "NO_BODY_TRANSFER")
                require(transfers[0].lower() == "chunked", "TRANSFER_ENCODING")
                self.chunked = True
                self.chunk_left = None
                self.length = None
                self.framing_kind = "chunked"
            else:
                require(self.will_close or self.length == 0, "CLOSE_DELIMITED_REQUIRED")
                self.framing_kind = "no-body" if self.length == 0 else "transport-eof"
            self.bounded.set_mode("body")
            if self.length == 0:
                self._close_conn()
                self._mark_completion()
            else:
                self.bounded._checkpoint()

        def _mark_completion(self):
            assert_response_private(self)
            # Tagged sized reads return a nonempty partial body without closing.
            # An accepted EOF already proves close-delimited completion.
            if (
                self.framing_kind == "transport-eof"
                and self.bounded.clean_eof
                and self.fp is not None
            ):
                self._close_conn()
            if self.fp is None:
                if self.framing_kind == "transport-eof":
                    require(self.bounded.clean_eof, "UNCLEAN_EOF")
                elif self.framing_kind == "content-length":
                    require(
                        self.expected_length is not None
                        and self.length == 0
                        and self.bounded.body == self.expected_length,
                        "INCOMPLETE_LENGTH",
                    )
                elif self.framing_kind == "chunked":
                    require(self.final_chunk_seen and self.trailer_complete, "INCOMPLETE_CHUNK")
                else:
                    require(
                        self.framing_kind == "no-body"
                        and self.length == 0
                        and self.bounded.body == 0,
                        "INCOMPLETE_NO_BODY",
                    )
            # Last foreign callback before body, buffer or completion commit.
            self.bounded._checkpoint()
            if self.fp is None:
                self.completion = self.framing_kind

        def _close_conn(self):
            # The tagged parser calls this after clearing its file pointer.
            # Keep its owned response operation through the exact close attempt.
            token = self.bounded.response_operation
            if token is None or self.fp is not self.bounded or self.bounded.in_callback:
                error = Refused("REENTRANT_RESPONSE_PRIVATE")
                self.bounded.poison("KNOWN_REFUSAL", error)
                self.completion = None
                raise error
            self.fp = None
            self.bounded._parser_close(token)

        @response_cleanup
        def close(self):
            super().close()
            if not self.bounded.closed:
                self.bounded._parser_close(self.bounded.response_operation)

        @response_flight
        def _read_next_chunk_size(self):
            self.bounded.set_mode("framing")
            self.bounded.line_kind = "chunk"
            line = self.fp.readline(http._MAXLINE + 1)
            require(line.endswith(b"\r\n"), "CHUNK_LINE")
            size_field, marker, extension = line[:-2].partition(b";")
            require(not marker or all(32 <= byte <= 126 for byte in extension), "CHUNK_EXTENSION")
            raw = size_field
            require(
                1 <= len(raw) <= 8 and all(char in b"0123456789abcdefABCDEF" for char in raw),
                "CHUNK_SIZE",
            )
            size = int(raw, 16)
            require(size <= self.body_limit - self.bounded.body, "CHUNK_BODY_CAP")
            return size

        @response_flight
        def _read_and_discard_trailer(self):
            self.bounded.set_mode("framing")
            self.bounded.line_kind = "trailer"
            while True:
                line = self.fp.readline(http._MAXLINE + 1)
                require(line.endswith(b"\r\n"), "TRAILER_TERMINATOR")
                if line == b"\r\n":
                    self.trailer_complete = True
                    return
                require(line[:1] not in (b" ", b"\t") and b":" in line, "TRAILER_FIELD")

        @response_flight
        def _get_chunk_left(self):
            left = self.chunk_left
            if left == 0:
                self.bounded.set_mode("framing")
                require(self.fp.read(2) == b"\r\n", "CHUNK_CRLF")
            if left is None or left == 0:
                left = self._read_next_chunk_size()
                if left == 0:
                    self.final_chunk_seen = True
                    self._read_and_discard_trailer()
                    self._close_conn()
                    self.chunk_left = None
                    return None
                self.chunk_left = left
            self.bounded.set_mode("body")
            return left

        @response_public
        def read(self, amount=None):
            require(type(amount) is int and 0 <= amount <= 4096, "BODY_WINDOW")
            before = self.length
            value = super().read(amount)
            if before is not None:
                require(len(value) == min(before, amount), "INCOMPLETE_LENGTH")
            self._mark_completion()
            return value

        @response_public
        def readinto(self, buffer):
            require(type(buffer) in (bytearray, memoryview) and len(buffer) <= 4096, "BODY_WINDOW")
            before = self.length
            # The caller's buffer is an output; keep it untouched until the
            # parser has validated the entire requested body window.
            scratch = bytearray(len(buffer))
            count = super().readinto(scratch)
            if before is not None:
                require(count == min(before, len(buffer)), "INCOMPLETE_LENGTH")
            self._mark_completion()
            buffer[:count] = scratch[:count]
            return count

        @response_public
        def read1(self, amount=-1):
            raise Refused("UNREVIEWED_READ1")

        @response_public
        def peek(self, amount=-1):
            raise Refused("UNREVIEWED_PEEK")

        @response_public
        def readline(self, limit=-1):
            raise Refused("UNREVIEWED_RESPONSE_LINE")

    return StrictResponse
