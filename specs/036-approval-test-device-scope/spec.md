# AT1 target-device prompt scope

Selected-device synthetic approval cards must be listed and answered only by their target paired device. Existing bearer, active-device, approval-owner, bot authorization and runtime gates remain required. The internal target identifier is not serialized. Ordinary unscoped approval rows retain their existing behavior. This prerequisite does not publish a synthetic card, register a command or change grants.

Acceptance: another device of the same user cannot list, answer or replay the scoped request; missing device identity fails closed; the target can answer once and replay its own acknowledgement; ordinary approvals remain available under existing gates. Invalid answers do not invoke the native resolver or settle the row.

Selected-device test rows expire at their exact advertised deadline without ordinary approval grace. Persistent session/always choices are not offered by the test. Ordinary approvals retain the existing grace period.

Cancellation removes only the exact internally owned target row. A replaced row is untouched; ordinary rows cannot use this withdrawal port. Answer locks with active waiters remain retained until their users leave.
