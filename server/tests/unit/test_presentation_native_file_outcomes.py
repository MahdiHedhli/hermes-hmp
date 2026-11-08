"""Diagnostic DATA sanitizer only; synthetic exceptions never prove native IO."""
from __future__ import annotations

import errno

import pytest
from hmp_startup.native_file_outcomes import _reported_stat_condition, _StatReport

CASES = ('reported_missing', 'wrong_errno', 'wrong_name', 'bool_errno',
         'foreign_errno', 'subclass_errno', 'foreign_filename', 'subclass_filename',
         'foreign_argument', 'subclass_argument', 'null_argument', 'permission',
         'base_error', 'foreign_subclass', 'missing_fields')


@pytest.mark.parametrize('case', CASES)
def test_closed_stat_diagnostic_category(case):
    calls = []

    class Foreign:
        def __getattr__(self, name):
            calls.append('get')
            raise AssertionError('foreign getter')

        def __eq__(self, other):
            calls.append('eq')
            raise AssertionError('foreign equality')

        def __str__(self):
            calls.append('str')
            raise AssertionError('foreign conversion')

    class Text(str):
        def __eq__(self, other):
            calls.append('text_eq')
            raise AssertionError('foreign string equality')

    class Number(int):
        def __eq__(self, other):
            calls.append('number_eq')
            raise AssertionError('foreign integer equality')

    class ForeignError(FileNotFoundError):
        @property
        def errno(self):
            calls.append('errno_get')
            raise AssertionError('subclass errno getter')

        @property
        def filename(self):
            calls.append('filename_get')
            raise AssertionError('subclass filename getter')

    name = 'synthetic_cache_component'
    error = FileNotFoundError(errno.ENOENT, 'synthetic diagnostic only', name)
    original = name
    if case == 'wrong_errno':
        error.errno = errno.EACCES
    elif case == 'wrong_name':
        error.filename = 'other_synthetic_component'
    elif case == 'bool_errno':
        error.errno = True
    elif case == 'foreign_errno':
        error.errno = Foreign()
    elif case == 'subclass_errno':
        error.errno = Number(errno.ENOENT)
    elif case == 'foreign_filename':
        error.filename = Foreign()
    elif case == 'subclass_filename':
        error.filename = Text(name)
    elif case == 'foreign_argument':
        original = Foreign()
    elif case == 'subclass_argument':
        original = Text(name)
    elif case == 'null_argument':
        original = None
    elif case == 'permission':
        error = PermissionError(errno.ENOENT, 'synthetic', name)
    elif case == 'base_error':
        error = OSError()
        error.errno, error.filename = errno.ENOENT, name
    elif case == 'foreign_subclass':
        error = ForeignError()
    elif case == 'missing_fields':
        error = FileNotFoundError()
    expected = (_StatReport.REPORTED_MISSING_FOR_ORIGINAL_ARGUMENT
                if case == 'reported_missing' else _StatReport.REFUSED)
    assert _reported_stat_condition(error, original) is expected
    assert calls == []
