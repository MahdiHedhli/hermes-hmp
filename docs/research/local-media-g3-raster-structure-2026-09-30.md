# Local generated media: G3 raster structure prototype (2026-09-30)

Research prototype for root review. Not a design, wire shape, qualification or product change. It
implements root's option A: standard-library structural checks on one bounded immutable `bytes`
buffer, no host decoding. No path, descriptor, database, grant, reference, route, manifest or existing
fixture is touched. G1/G2 were not rerun. Concurrency (eventual 2 per device / 4 per instance) belongs
to a later route and is not in this pure function.

Files: `tools/research/local_media_raster_structure.py` (`check_raster_structure(data) -> Structure`
or `RasterRefused(reason, detail)`) and `tools/research/tests/test_local_media_raster_structure.py`.

## What a pass means

"This buffer has the structure of an admitted static PNG, JPEG or WebP." Nothing more.

- **Decodability is never established.** Zlib, Huffman/entropy and VP8/VP8L payloads are not read, so
  a structurally valid file with corrupt compressed data is admitted. `Structure.decodability` is the
  constant `"unvalidated"`. The phone's bounded Flutter codec is the decoder and alone decides.
- **Not a polyglot filter.** Only the rules below are enforced. Nothing claims a file cannot be valid
  in another format elsewhere, or that every ambiguous byte layout is caught.
- Header dimensions are not cross-checked against the compressed data (a 8192x2441 PNG whose IDAT is a
  few bytes is admitted).
- The function takes bytes only. A file name or suffix cannot influence the result.

## Policy enforced

Exact `bytes` type (bytearray/memoryview refused); 1..8 MiB; each edge 1..8192; width x height
<= 20,000,000 (width/height are the dimensions *declared* in the header, not decoded); at most 10,000
PNG chunks or JPEG segments+restart markers; at most 64 JPEG scans (`MAX_JPEG_SCANS`, refused as
`too_many_units`/`jpeg.scan_count`); refusals are a closed
`Reason` plus a fixed detail tag and never contain input bytes. Metadata (PNG ancillary, JPEG APPn/COM,
WebP ICCP/EXIF/XMP) passes through unchanged, subject only to the length/order rules below.

## Admitted subset (anything else is refused)

**PNG.** Signature; IHDR first, length 13, legal colour/depth pair, method 0/0, interlace 0 or 1;
every chunk length within the buffer and <= 2^31-1; ASCII-letter type with the reserved bit clear;
CRC-32 over type+data verified for every chunk; only IHDR/PLTE/IDAT/IEND as critical chunks (unknown
critical, including `CgBI`, refused); `acTL`/`fcTL`/`fdAT` refused anywhere; one contiguous run of
IDAT; PLTE before IDAT, once, 1..256 entries, <= 2^depth for indexed, required for indexed, forbidden
for grey/grey+alpha; tRNS length by colour type and forbidden for alpha types; hIST needs PLTE; known
ancillary chunks (gAMA, cHRM, iCCP, sBIT, sRGB, cICP, mDCV, cLLI, bKGD, hIST, tRNS, pHYs, tIME, eXIf)
at most once and in their legal position relative to PLTE/IDAT; unknown ancillary chunks pass; IEND
empty, last, with no trailing byte; first two IDAT bytes form a legal zlib header (CM 8, window <= 32K,
FCHECK, no preset dictionary).

**JPEG.** `FFD8` then segments; exactly one SOF, only SOF0 (baseline) or SOF2 (progressive), 8-bit,
1 or 3 components (CMYK, 2 components, 12-bit, SOF1/3/5-7/9-15, arithmetic DAC, DNL, height 0 refused),
unique component ids, sampling 1..4, Tq <= 3; SOF before any SOS; only DQT, DHT, DRI, APPn, COM, SOF,
SOS markers (anything else, including fill bytes `FF FF` and stray RSTn, refused); segment lengths
bounded; DQT/DHT bodies exactly consumed, DHT code count 1..256; SOS header exact, components known
and unique, interleaved MCU <= 10 blocks; baseline scans `0,63,0,0`, each component scanned once;
progressive scans: DC scans `Ss=Se=0`, AC scans single-component `1<=Ss<=Se<=63`, `Ah/Al <= 13`, `Ah
= Al+1` for refinements, every component gets a DC-first and an AC-first scan; quant table and needed
Huffman tables defined before the scan; entropy data is traversed by one regex search per marker
(`FF 00` stuffed, `FF D0-D7` restart, other `FF xx` ends the scan), non-empty, restarts only with a
non-zero DRI and in strict RST0..7 cycle; EOI is the last two bytes (no trailing payload).

**WebP.** `RIFF` size equals buffer length minus 8 exactly; chunk sizes within bounds; odd payloads
followed by a zero pad byte; ANIM/ANMF and the VP8X animation flag refused anywhere. Layouts: a single
`VP8 ` or `VP8L`; or `VP8X` (size 10, reserved bits zero) then optional ICCP, optional ALPH (VP8 only,
valid header, raw length checked), exactly one image, then optional EXIF/XMP, each at most once and only
if its VP8X flag is set. Unknown chunks refused. VP8 header: shown key frame, version <= 3, start code,
partition within chunk, no scaling bits. VP8L: signature `2F`, version 0. VP8X canvas must equal the
bitstream dimensions.

## Known conservative refusals

Valid but refused: SOF1 (extended sequential), 12-bit/arithmetic/lossless/hierarchical JPEG, JPEG fill
bytes, any JPEG with more than 64 scans, and any JPEG with more than 10,000 segments plus restart markers (very small restart intervals on
large images), DRI-less restart streams, VP8 scaling bits, unknown WebP chunks, PNG with an unknown
critical chunk, non-zero PNG/WebP reserved fields, and WebP ICCP/ALPH/EXIF/XMP chunks whose VP8X
flag is not set (a flag set with no chunk is admitted).

## Evidence

- 143 synthetic tests (fixed byte constants built in the test file; no user content, no files, no
  network, no decoder). Each negative is a one-property change from an accepted control.
- Mutation check (scratch only, not committed): 23 single-guard removals (CRC, trailing bytes, APNG,
  indexed palette, IDAT contiguity, unknown critical, chunk cap, zlib header, JPEG trailing/CMYK/second
  SOF/restart/fill/unsupported SOF/progressive params, WebP RIFF size/padding/canvas/animation flag/
  animation chunk/unknown chunk, pixel cap, byte cap) were each caught by at least one test. An independent review repeated this with 32 removals: 29 caught; of the 3 survivors, 2 are unreachable dead code (`jpeg.sof_after_scan`, a WebP extra-chunk branch) kept as defence in depth, and the JPEG component guard (duplicate id, sampling 0 or >4, Tq>3) now has a parametrized causal test. The SOS-at-EOF and 64-scan guards were checked by running the new tests against a copy with each guard removed (both fail; `IndexError` for the former).
- Every strict prefix of each accepted PNG/JPEG/WebP fixture is refused; every single-byte mutation
  (xor 01/80/FF) of eight fixtures yields either a structure or a closed `RasterRefused`. That is the
  tested corpus only: an Opus review fuzz (~608k cases) found one further escape, an SOS segment of
  length 2 ending the buffer (`IndexError`), now fixed and covered by a causal test. No broader
  "never another exception" claim is made.
- Bounds: an 8 MiB stuffed JPEG scan and an 8 MiB PNG chunk are checked with peak traced allocation
  under 256 KiB and a 5 s wall guard; 20,000 JPEG segments and 50,000 PNG chunks stop at the cap.
- A fresh interpreter that runs the check imports none of `PIL`, `pillow_heif`, `hermes_cli`, `agent`;
  a static test confines the module's imports to `re, struct, zlib, dataclasses, enum`. `zlib` is used
  only for `crc32`.

## Limits of this evidence

- Root's current host structural check passed all three actual app synthetic assets (onePixelPng,
  onePixelJpeg, onePixelWebp from `media_test_support.dart`); they are byte-exact base64 copies in the
  test file, admitted as 1x1 with decodability `unvalidated`. That the real Flutter codec decodes them
  is prior app evidence (`image_media_loader_test.dart`), not a new cross-layer end-to-end run. R1
  (all encoder variants) and R7 (bomb) remain unsatisfied.

- Synthetic fixtures only; no real encoder output and no Flutter codec was run, so the claim that the
  phone decoder accepts every admitted file is not tested here (R1/R7 of the architecture review need
  the phone side).
- The 64-scan cap is a conservative availability limit, not proof of any phone freeze: review found a
  120 KB progressive 5000x4000 file with ~9,980 scans was structurally admitted, and decode cost grows
  with scans x blocks. It is not a complete CPU/decompression-bomb guard; the phone public path needs a
  separate pre-decode guard (assigned elsewhere), and the Flutter codec alone decides decodability.
- Restart counts are not compared with the MCU count, DHT code sets are not checked for validity
  (Kraft sum), progressive refinement order is not checked beyond the rules above, VP8/VP8L bodies and
  ALPH compressed data are opaque.
- Size is a judgement call: the module is about 575 lines (formatter-expanded) with no decoding. Root
  may prefer fewer rules; reached guards have causal tests, with the two documented
  unreachable branches retained as defence in depth.
- This does not authorize or qualify a media service, route, reference or path policy.

## Root acceptance after repair (2026-10-01)

The original independent review found an empty JPEG SOS-at-EOF out-of-bounds read and
a many-scan availability case. Both are repaired: header access is bounded, and the 65th
scan is refused before entropy traversal. A bounded independent re-review passed the
repair at module SHA-256 `f293d0c1e379d20ec5d466e9a92e9c0e6b961a2a2b7009b5aac3705410b47610`
and test SHA-256 `80bec5b0d88cdd5a28b74387d1fcfe7330ebe66084a9ac914022a9f9a6dd044b`.
It passed 22 selected tests, exercised SOS/truncation counterexamples and repeated
the empty-SOS, scan-count and six component-rule guard-removal checks causally.
It did not repeat the full corpus, broad fuzzing or native G1/G2 fixtures. Root separately
passed 11 selected tests for these repairs and the three actual synthetic app assets.

Root accepts this as research-only structural evidence. No route, handle, grant, build
entry or device delivery is implemented. The phone public-image decoder needs its own
preflight because public CDN bytes do not pass through this host prototype.
