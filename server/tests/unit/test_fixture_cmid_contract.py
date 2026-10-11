"""The integration fixtures must send client_message_ids the read bridge can recover.

`bridge._cmid` only recovers canonical lowercase UUIDv7 ids under the exact `hmp:<chat>:` prefix.
A fixture that sends anything else makes the positive wire assertion fail and a refused-id
negative vacuous. The real fixture runner uses the build's locked Python 3.14 interpreter, whose
`uuid.uuid7()` the integration tests call directly.
"""

from __future__ import annotations

import uuid

import pytest

from hmp_plugin import bridge

pytestmark = pytest.mark.skipif(
    not hasattr(uuid, "uuid7"), reason="native uuid.uuid7() needs Python 3.14"
)


def test_fixture_uuid7_round_trips_only_under_its_own_chat_prefix() -> None:
    cmid = str(uuid.uuid7())
    assert bridge._cmid(f"hmp:chat-a:{cmid}", "chat-a") == cmid
    assert bridge._cmid(f"hmp:chat-a:{cmid}", "chat-b") is None
    assert bridge._cmid(f"hmp:chat-b:{cmid}", "chat-a") is None
    assert bridge._cmid(f"hmp:chat-a:{cmid}", None) is None
    assert bridge._cmid(f"other:chat-a:{cmid}", "chat-a") is None


def test_uuid4_is_rejected_on_reads() -> None:
    cmid = str(uuid.uuid4())
    assert bridge._cmid(f"hmp:chat-a:{cmid}", "chat-a") is None
