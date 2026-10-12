# Compose reviewed AT1/push and current readiness/image baseline

Parents: current app HMP pin 26e41db43e14245153ae2202d2782d9b9c94b6c0 and reviewed AT1 candidate 39fd7b28c22655168de86f9af882663f3583b357. The AT1 ancestry also carries reviewed push prerequisites; these must retain disabled/unconfigured defaults and are not live provider activation.

Conflict decisions: preserve readiness Store transaction serialization/poison ownership; combine terminal REVOKED predicate with serialized writes. Keep AT1 retained stop owner and perform readiness operator stop inside it; defer Store close while readiness worker debt remains. Preserve both route sets and exact uniqueness assertions. Reverse exact readiness additions before original AT1/push/S5 bridge witnesses; do not drop baseline or mutation checks.

Initial conflict-focused run: 275 passes/four failures in composed inventory/witness/fixture shape. Corrected run: 279 passes. Broad source/runtime review, full tests and actual composed native/device qualification remain required before updating app gitlink. No deployment, grant/provider configuration or release action is implied.
