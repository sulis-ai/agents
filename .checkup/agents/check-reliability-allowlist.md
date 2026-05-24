# check-reliability per-project allowlist — agents marketplace

Format: `signature: reason`. Lines starting with `#` are comments.

# sea:probe runner pattern. Each runner wraps its tool in broad-except so
# one tool's failure doesn't crash the whole orchestrator. This is the
# correct design — probe is a multi-tool pipeline where partial-success
# is the expected mode. Each runner's broad catch is paired with a
# structured error in the output envelope.
broad-except::plugins/sea/skills/probe/scripts/probe.py::179: probe orchestrator pattern (partial-success expected)
broad-except::plugins/sea/skills/probe/scripts/probe/runners/architecture_runner.py::101: probe runner pattern
broad-except::plugins/sea/skills/probe/scripts/probe/runners/architecture_runner.py::136: probe runner pattern
broad-except::plugins/sea/skills/probe/scripts/probe/runners/deadcode_runner.py::72: probe runner pattern
broad-except::plugins/sea/skills/probe/scripts/probe/runners/deadcode_runner.py::82: probe runner pattern
broad-except::plugins/sea/skills/probe/scripts/probe/runners/deadcode_runner.py::91: probe runner pattern
broad-except::plugins/sea/skills/probe/scripts/probe/runners/deployment_runner.py::337: probe runner pattern
broad-except::plugins/sea/skills/probe/scripts/probe/runners/duplication_runner.py::55: probe runner pattern
broad-except::plugins/sea/skills/probe/scripts/probe/runners/lint_runner.py::112: probe runner pattern
broad-except::plugins/sea/skills/probe/scripts/probe/runners/test_runner.py::158: probe runner pattern
broad-except::plugins/sea/skills/probe/scripts/probe/runners/test_runner.py::211: probe runner pattern
broad-except::plugins/sea/skills/probe/scripts/probe/workspace.py::137: probe workspace setup; partial-failure tolerance

# idc CLI entry pattern. build_pptx.py is a CLI script; broad-except at
# the top-level entry catches all errors and emits a clean message rather
# than a stack trace to a non-technical founder.
broad-except::plugins/idc/scripts/build_pptx.py::407: CLI top-level entry; clean error reporting to founder

# _wpxlib.py: 2 cases of broad-except that need per-case review.
# Not bulk-allowlisting — these may be real findings. Mark for
# sulis-execution maintainer follow-up.
broad-except::plugins/sulis-execution/scripts/_wpxlib.py::177: needs sulis-execution maintainer review
broad-except::plugins/sulis-execution/scripts/_wpxlib.py::2139: needs sulis-execution maintainer review

# v0.20.0+ tool-wrapper integration: each check-* scanner wraps external
# tool invocations (semgrep / gitleaks / trivy / hadolint / lizard / jscpd /
# coverage / testssl / curl_probe) in broad-except so one tool's failure
# doesn't crash the orchestrator. Same pattern as sea:probe runners.
# Each catch is paired with a structured tool_errors entry in the output
# envelope. Code is annotated with `# noqa: BLE001 — boundary catch for
# tool wrapper`.
broad-except::plugins/sulis/skills/check-build/scripts/builder.py::113: tool-wrapper boundary catch
broad-except::plugins/sulis/skills/check-build/scripts/builder.py::133: tool-wrapper boundary catch
broad-except::plugins/sulis/skills/check-build/scripts/builder.py::647: tool-wrapper boundary catch (main-level)
broad-except::plugins/sulis/skills/check-readability/scripts/audit.py::175: tool-wrapper boundary catch (lizard)
broad-except::plugins/sulis/skills/check-readability/scripts/audit.py::196: tool-wrapper boundary catch (jscpd)
broad-except::plugins/sulis/skills/check-reliability/scripts/scanner.py::337: tool-wrapper boundary catch (semgrep INF-04)
broad-except::plugins/sulis/skills/check-reliability/scripts/scanner.py::491: tool-wrapper boundary catch (main-level)
broad-except::plugins/sulis/skills/check-security/scripts/scanner.py::265: tool-wrapper boundary catch (semgrep)
broad-except::plugins/sulis/skills/check-security/scripts/scanner.py::284: tool-wrapper boundary catch (gitleaks)
broad-except::plugins/sulis/skills/check-security/scripts/scanner.py::299: tool-wrapper boundary catch (trivy)
broad-except::plugins/sulis/skills/check-security/scripts/scanner.py::314: tool-wrapper boundary catch (testssl)
broad-except::plugins/sulis/skills/check-security/scripts/scanner.py::326: tool-wrapper boundary catch (curl_probe)
broad-except::plugins/sulis/skills/check-security/scripts/scanner.py::587: tool-wrapper boundary catch (main-level)
broad-except::plugins/sulis/skills/check-security/scripts/scanner.py::591: tool-wrapper boundary catch (main-level v0.22.0+)
broad-except::plugins/sulis/skills/check-maintainability/scripts/scanner.py::652: CQ-05 git-log analysis boundary catch (v0.22.0+)
