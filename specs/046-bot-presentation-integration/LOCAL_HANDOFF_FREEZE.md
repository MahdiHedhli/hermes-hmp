# Local producer handoff freeze — integrated source

Source `797dbbc`, integrated through PR114, fills the sender-data step in
[terminal transport](TERMINAL_TRANSPORT.md). It does not qualify the producer or
receiver, enable a service route, write TERMINAL/ACK, or release native credit.

`LocalStartedProducer.freeze_handoff_data()` is a one-use call by the original
service Task. The attempt is latched before `_guard` or `_current`, because these
cross native/control boundaries. Reentry, duplication or failure poisons the
handoff attempt permanently. Restoration cannot permit a retry.

The method captures the original producer scope, immutable historical claim,
observation, completed transfer and original shared cancellation budget. It
derives a cleanup stamp only from that budget's actual minimum end, reconstructing
`start = end - CLEANUP_NS`. It never starts another interval. An uncaused normal
claim has no stamp; an aborted claim requires one. Historical OK followed by a
cause uses the actual caused window, without changing the historical outcome.

Encoding and fresh native checks must leave the captured claim, scope, cause and
end unchanged. Callback-free metadata guards after the native tail revalidate
the original Task/connection, registry/record/resources, controller/channel,
observation/transfer and clock-domain references. A final same-end/nonfailed
budget check precedes publication of immutable envelope bytes and their digest.
The frozen object is DATA only; its `repr` discloses neither content nor authority.

## Future writer requirement

A qualified writer must independently establish actual runtime/native authority,
validate original custody and compare the current cause/end with this exact
frozen envelope immediately before IO. It must reject `_handoff_failed` even when
the original producer's `_failed` remains false and `claim_data()` still exposes
historical data. A later cause or shorter end invalidates old envelope timing for
IO; it does not permit refreezing or retrying a torn write.

Existing `encode_handoff` and decoded claims remain closed data codecs. Neither
a typed frozen object, matching digest, generation string, same UID nor clock
marker grants receiver acceptance, ACK permission, native retirement or image
publication.

## Current verification scope

The 27 focused cases use actual synthetic service Tasks, parent policy and Unix
IO. Native authority, peer identity and clock qualification are mocked. Root's
exact-source serial eleven-module regression passes 418 cases on Python 3.11.15
and 418 on Python 3.14.4, plus 230 budget/grammar cases on each runtime. These
counts include existing regressions, not just the new freeze cases. Cases cover normal/aborted/historical-OK-after-cause,
reentry, wrong actor, encoding failure, scope/claim/cause/budget mutation across
encoding and sampling, and final descriptor-tail custody drift. Failure keeps
registry PENDING and native headers/credits retained. Independent source review
accepted the final metadata-tail repair and causal scope; reviewer execution is
not claimed. Exact-source CI42129488493 passes every job: 7,219 passed,
21 skipped, 18 warnings and 190 subtests, plus Unicode 17 jobs on Python
3.12–3.14. Qualified factories, actual terminal transport and runtime/physical
qualification remain pending.
