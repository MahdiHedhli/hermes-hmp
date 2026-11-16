"""Strict test-only inverse of the historic image_cache layout amendment.

Unknown or modified source deltas are refused; original witnesses remain intact.
"""

REVERSES = {
    "local_media_candidate.py": (
        (
            (
                "\nA candidate is **not authority**. This module answers o"
                "ne question per row: did this strict\n`image_generate` to"
                "ol row pass the 64 KiB bound and the one accepted parser"
                ", and does its `image`\nlexically sit in one of the three"
                " closed same-profile native image-cache layouts? If so t"
                "he row is a\n`MediaCandidate` holding\nonly the row id and"
                " the scanner's canonical tool digest. The image string, "
                "the flat name, the home\nand the raw content are used for"
                " that pass/fail test and dropped; none is carried or log"
                "ged. A\n"
            ),
            (
                "\nA candidate is **not authority**. This module answers o"
                "ne question per row: did this strict\n`image_generate` to"
                "ol row pass the 64 KiB bound and the one accepted parser"
                ", and does its `image`\nlexically sit in one of the two c"
                "losed same-profile native image-cache layouts? If so the"
                " row is a\n`MediaCandidate` holding\nonly the row id and t"
                "he scanner's canonical tool digest. The image string, th"
                "e flat name, the home\nand the raw content are used for t"
                "hat pass/fail test and dropped; none is carried or logge"
                "d. A\n"
            ),
        ),
        (
            (
                "    return name if classify_candidate(name) is None else"
                " None\n\n\ndef derive_cache_location(image: str, home: str)"
                ' -> tuple[CacheLayout, str] | None:\n    """Select one li'
                "teral native cache layout; never normalize or search a f"
                'allback."""\n    legacy = derive_flat_name(image, home)\n'
            ),
            (
                "    return name if classify_candidate(name) is None else"
                " None\n\n\n\ndef derive_cache_location(image: str, home: str"
                ') -> tuple[CacheLayout, str] | None:\n    """Select one l'
                "iteral native cache layout; never normalize or search a "
                'fallback."""\n    legacy = derive_flat_name(image, home)\n'
            ),
        ),
        (
            (
                "        return CacheLayout.LEGACY, legacy\n    if type(im"
                "age) is not str or not _valid_home(home):\n        return"
                ' None\n    historic_prefix = home + "/image_cache/"\n    i'
                "f image.startswith(historic_prefix):\n        historic_na"
                "me = image[len(historic_prefix) :]\n        if classify_c"
                "andidate(historic_name) is not None:\n            return "
                "None\n        return CacheLayout.HISTORIC_IMAGE_CACHE, hi"
                "storic_name\n    historic_prefix = None  # Release before"
                " allocating the generated-layout prefix.\n    prefix = ho"
                'me + "/cache/generated/images/"\n    if not image.startsw'
                "ith(prefix):\n        return None\n    generated_name = im"
                "age[len(prefix) :]\n    if classify_candidate(generated_n"
                "ame) is not None:\n        return None\n    return CacheLa"
                "yout.GENERATED, generated_name\n\n\ndef raw_tool_candidate("
                "item: Mapping[object, object], home: str) -> MediaCandid"
                'ate | None:\n    """The candidate for one native row, or '
                '`None`. Total: it never raises and never logs."""\n'
            ),
            (
                "        return CacheLayout.LEGACY, legacy\n    if type(im"
                "age) is not str or not _valid_home(home):\n        return"
                ' None\n    prefix = home + "/cache/generated/images/"\n   '
                " if not image.startswith(prefix):\n        return None\n  "
                "  generated_name = image[len(prefix):]\n    if classify_c"
                "andidate(generated_name) is not None:\n        return Non"
                "e\n    return CacheLayout.GENERATED, generated_name\n\ndef "
                "raw_tool_candidate(item: Mapping[object, object], home: "
                'str) -> MediaCandidate | None:\n    """The candidate for '
                "one native row, or `None`. Total: it never raises and ne"
                'ver logs."""\n'
            ),
        ),
    ),
    "local_media_file_safety.py": (
        (
            (
                "- `profile_home` is the caller's already-selected, alrea"
                "dy-resolved profile home. The caller\n  owns resolving an"
                "d pinning it; this leaf opens it with O_NOFOLLOW on the "
                "final component and\n  never resolves it. Ancestors of th"
                "e home are trusted as the caller supplied them.\n- `candi"
                "date` is untrusted. Root decision: **flat only**. The th"
                "ree supported roots are\n  `cache/images`, `cache/generat"
                "ed/images` and `image_cache`; selection is an exact inte"
                "rnal enum,\n  not a path, so the candidate must be exactl"
                "y one component. Nesting, absolute strings,\n  `.`/`..`, "
                "empty,\n  control/format characters, backslashes and over"
                "-long names are refused. Nested names would need a\n  sep"
                "arate reviewed amendment; no other root (`cache/document"
                "s`,\n  another profile) is ever consulted or used as a fa"
                "llback.\n\nMethod: open home and each selected literal cac"
                "he directory with\n"
            ),
            (
                "- `profile_home` is the caller's already-selected, alrea"
                "dy-resolved profile home. The caller\n  owns resolving an"
                "d pinning it; this leaf opens it with O_NOFOLLOW on the "
                "final component and\n  never resolves it. Ancestors of th"
                "e home are trusted as the caller supplied them.\n- `candi"
                "date` is untrusted. Root decision: **flat only**. The tw"
                "o supported roots are\n  `cache/images` and `cache/genera"
                "ted/images`; selection is an exact internal enum, not a "
                "path, so\n  the candidate must be exactly one component. "
                "Nesting, absolute strings, `.`/`..`, empty,\n  control/fo"
                "rmat characters, backslashes and over-long names are ref"
                "used. Nested names would need a\n  separate reviewed amen"
                "dment; no other root (legacy `image_cache`, `cache/docum"
                "ents`,\n  another profile) is ever consulted or used as a"
                " fallback.\n\nMethod: open home and each selected literal "
                "cache directory with\n"
            ),
        ),
        (
            (
                'READ_CHUNK = 64 * 1024\nCACHE_COMPONENTS = ("cache", "ima'
                'ges")\nGENERATED_CACHE_COMPONENTS = ("cache", "generated"'
                ', "images")\nHISTORIC_CACHE_COMPONENTS = ("image_cache",)'
                '\n\n\nclass CacheLayout(enum.Enum):\n    LEGACY = "legacy_im'
                'ages"\n    GENERATED = "generated_images"\n    HISTORIC_IM'
                'AGE_CACHE = "historic_image_cache"\n\n\nBYTES_LABEL = "unva'
                'lidated_raster_bytes"\n\nHOOK_NAMES = frozenset(\n'
            ),
            (
                'READ_CHUNK = 64 * 1024\nCACHE_COMPONENTS = ("cache", "ima'
                'ges")\nGENERATED_CACHE_COMPONENTS = ("cache", "generated"'
                ', "images")\n\n\nclass CacheLayout(enum.Enum):\n    LEGACY ='
                ' "legacy_images"\n    GENERATED = "generated_images"\nBYTE'
                'S_LABEL = "unvalidated_raster_bytes"\n\nHOOK_NAMES = froze'
                "nset(\n"
            ),
        ),
        (
            (
                "        components = CACHE_COMPONENTS\n    elif cache_lay"
                "out is CacheLayout.GENERATED:\n        components = GENER"
                "ATED_CACHE_COMPONENTS\n    elif cache_layout is CacheLayo"
                "ut.HISTORIC_IMAGE_CACHE:\n        components = HISTORIC_C"
                "ACHE_COMPONENTS\n    else:\n        return _refuse(Outcome"
                ".CACHE_LAYOUT_INVALID)\n    hooks = dict(_hooks or {})\n"
            ),
            (
                "        components = CACHE_COMPONENTS\n    elif cache_lay"
                "out is CacheLayout.GENERATED:\n        components = GENER"
                "ATED_CACHE_COMPONENTS\n    else:\n        return _refuse(O"
                "utcome.CACHE_LAYOUT_INVALID)\n    hooks = dict(_hooks or "
                "{})\n"
            ),
        ),
    ),
}


def reverse_historic_image_cache(text: str, name: str) -> str:
    for addition, historical in REVERSES.get(name, ()):
        assert text.count(addition) == 1, (name, "historic cache amendment changed")
        text = text.replace(addition, historical, 1)
    return text
