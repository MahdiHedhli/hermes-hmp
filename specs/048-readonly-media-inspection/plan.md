# Plan

Route only media-read through a private read-only context before mutable dispatch.
Use the existing custody and identity loaders; a narrow adapter exposes only epoch
and existing store media-decision validation against sqlite3.Row. Open a fresh path-aware committed read view for each epoch/decision sample and
close it before the operator roundtrip or next sample. Never retain immutable
SQLite caches across the roundtrip. SQLite reader-lock metadata is not claimed
byte-immutable; authority DB and WAL contents remain unchanged. Reuse the existing media handler
so output, listener protocol, decision equality and final identity check stay the
same. No SDK, dependency, compatibility, host configuration or grants changes.

Independent contract review accepted this boundary before implementation.
