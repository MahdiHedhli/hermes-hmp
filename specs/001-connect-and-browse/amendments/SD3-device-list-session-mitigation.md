# SD3 — device-list Hermes-session mitigation

## Requirement and boundary

Devices/list must refuse before opening or migrating the store whenever any
HERMES_SESSION_* variable is present, including empty values and future suffixes.
It must emit only the existing fixed session-refusal error and no device metadata.
An operator outside a Hermes session can still list populated devices without a
TTY. All mutation session/TTY checks retain their ordering and existing behavior.
No pairing/grant/authentication/identity/store schema or other read-command policy
changes. SEC-1's same-OS-user authority remains; this environment mitigation is
not a security sandbox and does not prevent deliberate environment removal/PTYS.
No live exposure or auth bypass was demonstrated.

## Source plan

Extract the existing prefix-presence check into a shared helper, retaining the
fixed refusal text. Existing mutation helper calls it before its TTY check.
Dispatch invokes it for the devices/list read path before _open, without classifying
list as mutating or adding a TTY requirement. Source base3e676ec10266ef958ca631b6f8384c6aa297745e.

## Verification tasks

- [ ] Prefix presence: known ID, known source and future suffix; empty/nonempty/space
      values; both fake TTY and non-TTY. A forbidden-open sentinel proves refusal
      precedes all store opening; populated synthetic metadata never reaches output.
- [ ] Ordinary populated operator listings pass with either TTY state, retain full
      device/user/label/state output and leave fake store state unchanged.
- [ ] Existing mutation refusal tests and normal read behavior remain unchanged.
- [ ] Independent source/test review, focused lint/privacy/diff and exact-head
      hosted CI before integration; record scopes and skips honestly.

Tests use existing isolated hmp_kit homes, injected environment and synthetic
credentials only. No native import, live home/device/provider/config action is
needed. No deployment or full security/release certification follows unit CI.
