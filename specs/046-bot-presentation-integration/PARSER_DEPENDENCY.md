# BI1 parser dependency and closed-surface amendment

CI38196929251 failed the closed-import scanner because actual PyYAML parsing was
not declared as a runtime dependency/allowed module. Tests previously inherited
PyYAML from the development environment. This is a packaging/contract omission;
the scanner finding is retained, not disabled.

Proposed runtime dependency: PyYAML>=6,<7 in plugin.yaml and server project metadata.
The target native development environment currently runs6.0.3; only that actual
parser has been exercised here. Future eligible versions must pass parser cases.
The worker uses yaml.scan and yaml.parse with SafeLoader to obtain bounded tokens
and events. It never calls yaml.load/safe_load or constructs a profile object graph.
The closed reducer rejects explicit tags/directives/anchors/aliases and projects
only five metadata fields. The parser performs no network or provider operation.

Scanner amendment is an exact lazy-import exception for
presentation_yaml_adapter.py; global third-party allowlist stays unchanged.
server/adapter/reads/bridge/CLI YAML imports remain rejected, and module-level
worker imports are rejected. Negative scanner cases demonstrate these limits.
This amendment requires independent review before convergence; no runtime plugin
update, route activation or provider/permission change is part of it.
