# Operator read-worker lifetime backport

Candidate c7482f131a5414c6b0d63ed5cb8ffb61b61fbfdc descends directly from deployed
5e247a64e918ec4222537623e426ed5483ac4d95. Its only production change is the existing
read-only operator service's worker tracking. There are no media/schema/CLI additions.
The original socket,512-byte parser, filesystem and peer checks remain unchanged.

The causal cancellation control showed an async to_thread wrapper could end and
release its Store borrow while the synchronous read still ran. The backport keeps
an original concurrent Future and intent ledger, retaining uncertain acquisition/
submission debt, consuming late wrapper errors and sealing the delivery context.
Only actual worker completion retires its original budget. Unknown completion may
conservatively block drain; it never grants permission to close Store or replay.

Independent finite source review found no concrete backport blocker. Both51-case
read/FD suites and592-case listener/adapter/CLI/access/database-ownership suites
passed unchanged on Python3.14.9 and3.11.15. Ruff and Plugin Doctor passed.

The pinned candidate was installed via Hermes PM on ColPanicM2 and LLY520 under
existing restart/update authorization. All109 plugin files match. Fresh gateway
and listener PIDs match, expected TLS identity passes, exact configuration hashes
and device/controls/schema snapshots remain unchanged. Native0.22.7/ed1afb0 on
ColPanicM2 and0.23.0/0f0e96f on LLY520 were preserved. ColPanicM2's3 profiles are ready;
LLY520's Hermes/Belac/SchoolBot are ready, with Lucas/Serenity still unavailable.
LLY520 health exit1 reflects that unchanged aggregate limitation.

RSWORK1 is repaired in this verified deployment; no live incident or production
fault injection was observed/performed. This is not physical phone qualification,
job execution, schema4/media service activation or release acceptance. The isolated
media-authority branch retains separate native/config/lifecycle/migration gates.
