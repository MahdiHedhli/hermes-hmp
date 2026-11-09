"""Closed transport namespace preparation; no mutation handler is registered."""
from pathlib import Path

import pytest

from hmp_plugin import operator_read as op


def test_default_read_layout_remains_original_socket_and_limit():
    service = op.OperatorReadService(object(), Path('/private/anchor'), 'a' * 32)
    assert service.path == Path('/private/controls-operator.sock')
    assert service._request_limit == op.MAX_REQUEST == 512


def test_separate_media_namespace_has_fixed_larger_envelope_bound_only():
    service = op.OperatorReadService(object(), Path('/private/anchor'), 'a' * 32,
                                     _socket_kind='media_write')
    assert service.path == Path('/private/media-operator.sock')
    assert service._request_limit == 4096
    # This class still has only the original read handler; selecting a pathname
    # never installs a permission-changing operation or changes the read codec.
    assert type(service)._handle is op.OperatorReadService._handle
    assert op.MAX_REQUEST == 512


@pytest.mark.parametrize('value', ('../other', '/tmp/other', 'media', '', None, True, 4096))
def test_arbitrary_names_and_limits_cannot_enter_transport_layout(value):
    with pytest.raises(op.OperatorUnavailableError):
        op.OperatorReadService(object(), Path('/private/anchor'), 'a' * 32,
                               _socket_kind=value)


def test_fd_entry_rejects_unapproved_name_before_filesystem_dispatch(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('must not access filesystem')
    monkeypatch.setattr(op.os, 'stat', forbidden)
    with pytest.raises(op.OperatorUnavailableError):
        op._entry(123, name='../outside')
