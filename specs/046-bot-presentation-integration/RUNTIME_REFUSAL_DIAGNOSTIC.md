# Synthetic guard-location diagnosis

Production source remains identical to 9dc2875. The original 68-case run
finished 38 passed/30 failed and remains preserved. A normal-fixture-only
exception observer records at most16 (source basename, function, line) tuples
from the selected copied startup modules' `_require` frames, with line tracing
disabled. It never retains exception objects, values, source bytes or locals.
On refusal it emits only these location tuples to the private child stderr.
The original normal-case success requirement and60-second deadline remain.

This is one diagnostic case, not qualification or a production change.
