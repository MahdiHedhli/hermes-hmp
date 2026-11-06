"""Exact inverse of the independently reviewed two-root C1 amendment.

Historical byte/bridge witnesses still validate their original source after this
closed inverse. Unknown or modified additions are never stripped. Test-only.
"""

REVERSES = {
    'local_media_candidate.py': (
        (
            (
                '            return None\n        imag'
                'e = parse_image_result(content)  # t'
                'he one bounded, accepted parse\n     '
                '   if type(image) is not str or deri'
                've_cache_location(image, home) is No'
                'ne:\n            return None\n        '
                'digest = _scan._tool_digest(row_id, '
                'IMAGE_TOOL, call_id, content)\n'
            ),
            (
                '            return None\n        imag'
                'e = parse_image_result(content)  # t'
                'he one bounded, accepted parse\n     '
                '   if type(image) is not str or deri'
                've_flat_name(image, home) is None:\n '
                '           return None\n        diges'
                't = _scan._tool_digest(row_id, IMAGE'
                '_TOOL, call_id, content)\n'
            ),
        ),
        (
            (
                '\n\n\ndef derive_cache_location(image: '
                'str, home: str) -> tuple[CacheLayout'
                ', str] | None:\n    """Select one lit'
                'eral native cache layout; never norm'
                'alize or search a fallback."""\n    l'
                'egacy = derive_flat_name(image, home'
                ')\n    if legacy is not None:\n       '
                ' return CacheLayout.LEGACY, legacy\n '
                '   if type(image) is not str or not '
                '_valid_home(home):\n        return No'
                'ne\n    prefix = home + "/cache/gener'
                'ated/images/"\n    if not image.start'
                'swith(prefix):\n        return None\n '
                '   generated_name = image[len(prefix'
                '):]\n    if classify_candidate(genera'
                'ted_name) is not None:\n        retur'
                'n None\n    return CacheLayout.GENERA'
                'TED, generated_name\n\ndef raw_tool_ca'
                'ndidate(item: Mapping[object, object'
                '], home: str) -> MediaCandidate | No'
                'ne:\n    """The candidate for one nat'
                'ive row, or `None`. Total: it never '
                'raises and never logs."""\n'
            ),
            (
                '\n\ndef raw_tool_candidate(item: Mappi'
                'ng[object, object], home: str) -> Me'
                'diaCandidate | None:\n    """The cand'
                'idate for one native row, or `None`.'
                ' Total: it never raises and never lo'
                'gs."""\n'
            ),
        ),
        (
            (
                '\nfrom . import local_media_active_sc'
                'an as _scan\nfrom .local_media_file_s'
                'afety import CacheLayout, classify_c'
                'andidate\nfrom .local_media_result im'
                'port parse_image_result\nfrom .local_'
                'media_sidecar import (\n'
            ),
            (
                '\nfrom . import local_media_active_sc'
                'an as _scan\nfrom .local_media_file_s'
                'afety import classify_candidate\nfrom'
                ' .local_media_result import parse_im'
                'age_result\nfrom .local_media_sidecar'
                ' import (\n'
            ),
        ),
        (
            (
                'A candidate is **not authority**. Th'
                'is module answers one question per r'
                'ow: did this strict\n`image_generate`'
                ' tool row pass the 64 KiB bound and '
                'the one accepted parser, and does it'
                's `image`\nlexically sit in one of th'
                'e two closed same-profile native ima'
                'ge-cache layouts? If so the row is a'
                '\n`MediaCandidate` holding\nonly the r'
                "ow id and the scanner's canonical to"
                'ol digest. The image string, the fla'
                't name, the home\nand the raw content'
                ' are used for that pass/fail test an'
                'd dropped; none is carried or logged'
                '. A\n'
            ),
            (
                'A candidate is **not authority**. Th'
                'is module answers one question per r'
                'ow: did this strict\n`image_generate`'
                ' tool row pass the 64 KiB bound and '
                'the one accepted parser, and does it'
                's `image`\nlexically sit directly und'
                'er `<home>/cache/images/`? If so the'
                ' row is a `MediaCandidate` holding\no'
                "nly the row id and the scanner's can"
                'onical tool digest. The image string'
                ', the flat name, the home\nand the ra'
                'w content are used for that pass/fai'
                'l test and dropped; none is carried '
                'or logged. A\n'
            ),
        ),
    ),
    'local_media_file_safety.py': (
        (
            (
                '    children: list[tuple[int, str, t'
                'uple[int, int]]] = []  # (parent fd,'
                ' name, identity)\n    parent_fd = hom'
                'e_fd\n    for name in components:\n   '
                '     try:\n            fd = open_trac'
                'ked(name, _DIR_FLAGS, parent_fd)\n'
            ),
            (
                '    children: list[tuple[int, str, t'
                'uple[int, int]]] = []  # (parent fd,'
                ' name, identity)\n    parent_fd = hom'
                'e_fd\n    for name in CACHE_COMPONENT'
                'S:\n        try:\n            fd = ope'
                'n_tracked(name, _DIR_FLAGS, parent_f'
                'd)\n'
            ),
        ),
        (
            (
                '    fire: Callable[[str], None],\n   '
                ' open_tracked: Callable[..., int],\n '
                '   components: tuple[str, ...],\n) ->'
                ' ReadResult:\n    # Pin home and ever'
                'y selected ancestor; each step is re'
                'lative to the previous descriptor.\n '
                '   try:\n        home_fd = open_track'
                'ed(home_path, _DIR_FLAGS)\n'
            ),
            (
                '    fire: Callable[[str], None],\n   '
                ' open_tracked: Callable[..., int],\n)'
                ' -> ReadResult:\n    # Pin home, cach'
                'e, images by descriptor. Each step i'
                's relative to the previous descripto'
                'r.\n    try:\n        home_fd = open_t'
                'racked(home_path, _DIR_FLAGS)\n'
            ),
        ),
        (
            (
                '\n    try:\n        return _read_pinne'
                'd(\n            home_path, candidate,'
                ' max_bytes, _chunk_size, fire, open_'
                'tracked, components\n        )\n    ex'
                'cept _FstatFailedError:\n        retu'
                'rn _refuse(Outcome.READ_FAILED)\n'
            ),
            (
                '\n    try:\n        return _read_pinne'
                'd(home_path, candidate, max_bytes, _'
                'chunk_size, fire, open_tracked)\n    '
                'except _FstatFailedError:\n        re'
                'turn _refuse(Outcome.READ_FAILED)\n'
            ),
        ),
        (
            (
                '    *,\n    max_bytes: int = MAX_BYTE'
                'S,\n    cache_layout: CacheLayout = C'
                'acheLayout.LEGACY,\n    _hooks: Mappi'
                'ng[str, Callable[[], None]] | None ='
                ' None,\n    _chunk_size: int = READ_C'
                'HUNK,\n) -> ReadResult:\n    """Read o'
                'ne basename in the selected closed c'
                'ache layout; never try a fallback.""'
                '"\n    if not 0 < max_bytes <= MAX_BY'
                'TES or _chunk_size <= 0:\n        rai'
                'se ValueError("bounds out of range")'
                '\n    if type(cache_layout) is not Ca'
                'cheLayout:\n        return _refuse(Ou'
                'tcome.CACHE_LAYOUT_INVALID)\n    if c'
                'ache_layout is CacheLayout.LEGACY:\n '
                '       components = CACHE_COMPONENTS'
                '\n    elif cache_layout is CacheLayou'
                't.GENERATED:\n        components = GE'
                'NERATED_CACHE_COMPONENTS\n    else:\n '
                '       return _refuse(Outcome.CACHE_'
                'LAYOUT_INVALID)\n    hooks = dict(_ho'
                'oks or {})\n    if not hooks.keys() <'
                '= HOOK_NAMES:\n'
            ),
            (
                '    *,\n    max_bytes: int = MAX_BYTE'
                'S,\n    _hooks: Mapping[str, Callable'
                '[[], None]] | None = None,\n    _chun'
                'k_size: int = READ_CHUNK,\n) -> ReadR'
                'esult:\n    """Read `<profile_home>/c'
                'ache/images/<candidate>` or return a'
                ' closed refusal."""\n    if not 0 < m'
                'ax_bytes <= MAX_BYTES or _chunk_size'
                ' <= 0:\n        raise ValueError("bou'
                'nds out of range")\n    hooks = dict('
                '_hooks or {})\n    if not hooks.keys('
                ') <= HOOK_NAMES:\n'
            ),
        ),
        (
            (
                '    PROFILE_HOME_INVALID = "profile_'
                'home_invalid"\n    PROFILE_HOME_UNAVA'
                'ILABLE = "profile_home_unavailable"\n'
                '    CACHE_LAYOUT_INVALID = "cache_la'
                'yout_invalid"\n    CANDIDATE_TYPE = "'
                'candidate_type"\n    CANDIDATE_EMPTY '
                '= "candidate_empty"\n'
            ),
            (
                '    PROFILE_HOME_INVALID = "profile_'
                'home_invalid"\n    PROFILE_HOME_UNAVA'
                'ILABLE = "profile_home_unavailable"\n'
                '    CANDIDATE_TYPE = "candidate_type'
                '"\n    CANDIDATE_EMPTY = "candidate_e'
                'mpty"\n'
            ),
        ),
        (
            (
                'READ_CHUNK = 64 * 1024\nCACHE_COMPONE'
                'NTS = ("cache", "images")\nGENERATED_'
                'CACHE_COMPONENTS = ("cache", "genera'
                'ted", "images")\n\n\nclass CacheLayout('
                'enum.Enum):\n    LEGACY = "legacy_ima'
                'ges"\n    GENERATED = "generated_imag'
                'es"\nBYTES_LABEL = "unvalidated_raste'
                'r_bytes"\n\n'
            ),
            (
                'READ_CHUNK = 64 * 1024\nCACHE_COMPONE'
                'NTS = ("cache", "images")\nBYTES_LABE'
                'L = "unvalidated_raster_bytes"\n\n'
            ),
        ),
        (
            (
                '  another profile) is ever consulted'
                ' or used as a fallback.\n\nMethod: ope'
                'n home and each selected literal cac'
                'he directory with\nO_DIRECTORY|O_NOFO'
                'LLOW|O_CLOEXEC relative to the\nprevi'
                'ous descriptor; open the file relati'
                've to `images` with O_NOFOLLOW|O_NON'
                'BLOCK; `fstat`\n(regular, one link, 0'
                ' < size <= bound); bounded read of a'
                't most bound+1 bytes; `fstat` again;'
                '\n'
            ),
            (
                '  another profile) is ever consulted'
                ' or used as a fallback.\n\nMethod: ope'
                'n home, `cache`, `images` each with '
                'O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC rel'
                'ative to the\nprevious descriptor; op'
                'en the file relative to `images` wit'
                'h O_NOFOLLOW|O_NONBLOCK; `fstat`\n(re'
                'gular, one link, 0 < size <= bound);'
                ' bounded read of at most bound+1 byt'
                'es; `fstat` again;\n'
            ),
        ),
        (
            (
                '  owns resolving and pinning it; thi'
                's leaf opens it with O_NOFOLLOW on t'
                'he final component and\n  never resol'
                'ves it. Ancestors of the home are tr'
                'usted as the caller supplied them.\n-'
                ' `candidate` is untrusted. Root deci'
                'sion: **flat only**. The two support'
                'ed roots are\n  `cache/images` and `c'
                'ache/generated/images`; selection is'
                ' an exact internal enum, not a path,'
                ' so\n  the candidate must be exactly '
                'one component. Nesting, absolute str'
                'ings, `.`/`..`, empty,\n  control/for'
                'mat characters, backslashes and over'
                '-long names are refused. Nested name'
                's would need a\n'
            ),
            (
                '  owns resolving and pinning it; thi'
                's leaf opens it with O_NOFOLLOW on t'
                'he final component and\n  never resol'
                'ves it. Ancestors of the home are tr'
                'usted as the caller supplied them.\n-'
                ' `candidate` is untrusted. Root deci'
                'sion: **flat only**. Native producer'
                's and the inbound\n  cache write top-'
                'level files of `cache/images` (name '
                'shapes in the G3 delivery-paths note'
                '), so\n  the candidate must be exactl'
                'y one component. Nesting, absolute s'
                'trings, `.`/`..`, empty,\n  control/f'
                'ormat characters, backslashes and ov'
                'er-long names are refused. Nested na'
                'mes would need a\n'
            ),
        ),
        (
            (
                '#!/usr/bin/env python3\n"""Bounded de'
                'scriptor-relative filesystem leaf fo'
                'r host-local generated images.\n\nIt r'
                'eads one candidate file from a selec'
                'ted closed native cache layout under'
                '\nthe supplied profile home through p'
                'inned directory descriptors and retu'
                'rns the\nbytes only to an in-process '
                'caller. It defines no media referenc'
                'e, route, grant, token, schema,\nwire'
                ' shape or public API, and it reads n'
                'othing from any Hermes install.\n'
            ),
            (
                '#!/usr/bin/env python3\n"""G3 filesys'
                'tem safety prototype for host-local '
                'generated images (research leaf, not'
                ' product).\n\nTest tooling: `server/hm'
                'p_plugin` never imports it. It reads'
                ' one candidate file from\n`<profile h'
                'ome>/cache/images/<candidate>` throu'
                'gh pinned directory descriptors and '
                'returns the\nbytes only to an in-proc'
                'ess caller. It defines no media refe'
                'rence, route, grant, token, schema,\n'
                'wire shape or public API, and it rea'
                'ds nothing from any Hermes install.\n'
            ),
        ),
    ),
    'local_media_active_batch.py': (
        (
            (
                '    if not hmac.compare_digest(claim'
                '.tool_digest, digest):\n        retur'
                'n DIGEST_MISMATCH\n    if _candidate.'
                'derive_cache_location(claim.image, h'
                'ome) is None:\n        return LEXICAL'
                '_MISMATCH\n    return OK\n'
            ),
            (
                '    if not hmac.compare_digest(claim'
                '.tool_digest, digest):\n        retur'
                'n DIGEST_MISMATCH\n    if _candidate.'
                'derive_flat_name(claim.image, home) '
                'is None:\n        return LEXICAL_MISM'
                'ATCH\n    return OK\n'
            ),
        ),
    ),
    'bridge.py': (
        (
            (
                '                if not secrets.compa'
                're_digest(claim.tool_digest, digest)'
                ':\n                    return None\n  '
                '              location = candidate.d'
                'erive_cache_location(claim.image, ho'
                'me)\n                if location is N'
                'one:\n                    return None'
                '\n                layout, name = loca'
                'tion\n                read = file_saf'
                'ety.read_profile_cache_image(home, n'
                'ame, cache_layout=layout)\n          '
                '      if read.outcome is not file_sa'
                'fety.Outcome.OK:\n                   '
                ' return None\n'
            ),
            (
                '                if not secrets.compa'
                're_digest(claim.tool_digest, digest)'
                ':\n                    return None\n  '
                '              name = candidate.deriv'
                'e_flat_name(claim.image, home)\n     '
                '           if name is None:\n        '
                '            return None\n            '
                '    read = file_safety.read_profile_'
                'cache_image(home, name)\n            '
                '    if read.outcome is not file_safe'
                'ty.Outcome.OK:\n                    r'
                'eturn None\n'
            ),
        ),
    ),
}


def reverse_cache_layout_additions(text: str, name: str) -> str:
    for addition, historical in REVERSES.get(name, ()):
        assert text.count(addition) == 1, (name, "cache-layout amendment changed")
        text = text.replace(addition, historical, 1)
    return text
