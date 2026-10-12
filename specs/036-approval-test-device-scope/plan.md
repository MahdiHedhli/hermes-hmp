# Plan

Add an optional internal target device to PromptRow. Filter list and answer operations using authenticated bearer identity supplied by existing server routes. Check scope before replay and resolver invocation. Do not add a wire field or trust a device identifier from the request body. Follow with the separately admitted operator/current-authority handler and producer lifecycle integration.

## Listener composition checkpoint

Attach the service after the native-backed HTTP listener starts and its generation nonce exists. The current adapter uses HmpServer.start_operator_read at that boundary; the approval-test endpoint must share the same generation and private anchor without changing the existing read endpoint. HmpServer.stop must drain the test endpoint/service before store close; cancellation must retain ownership. Fixture retained-resource paths require explicit separate accounting, not an implicit ordinary-path attachment. Current integrated approval checks: 102 passed; actual native composed once/deny passes with synthetic admission only. No listener attachment or CLI is implemented yet.
