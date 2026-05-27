# check-reliability per-project allowlist — agents marketplace

Format: `signature: reason`. Lines starting with `#` are comments.

# sea:probe runner pattern. Each runner wraps its tool in broad-except so
# one tool's failure doesn't crash the whole orchestrator. This is the
# correct design — probe is a multi-tool pipeline where partial-success
# is the expected mode. Each runner's broad catch is paired with a
# structured error in the output envelope.
broad-except::plugins/sulis/skills/analyse-codebase/scripts/probe.py::179: probe orchestrator pattern (partial-success expected)
broad-except::plugins/sulis/skills/analyse-codebase/scripts/probe/runners/architecture_runner.py::101: probe runner pattern
broad-except::plugins/sulis/skills/analyse-codebase/scripts/probe/runners/architecture_runner.py::136: probe runner pattern
broad-except::plugins/sulis/skills/analyse-codebase/scripts/probe/runners/deadcode_runner.py::72: probe runner pattern
broad-except::plugins/sulis/skills/analyse-codebase/scripts/probe/runners/deadcode_runner.py::82: probe runner pattern
broad-except::plugins/sulis/skills/analyse-codebase/scripts/probe/runners/deadcode_runner.py::91: probe runner pattern
broad-except::plugins/sulis/skills/analyse-codebase/scripts/probe/runners/deployment_runner.py::337: probe runner pattern
broad-except::plugins/sulis/skills/analyse-codebase/scripts/probe/runners/duplication_runner.py::55: probe runner pattern
broad-except::plugins/sulis/skills/analyse-codebase/scripts/probe/runners/lint_runner.py::112: probe runner pattern
broad-except::plugins/sulis/skills/analyse-codebase/scripts/probe/runners/test_runner.py::158: probe runner pattern
broad-except::plugins/sulis/skills/analyse-codebase/scripts/probe/runners/test_runner.py::211: probe runner pattern
broad-except::plugins/sulis/skills/analyse-codebase/scripts/probe/workspace.py::137: probe workspace setup; partial-failure tolerance

# idc CLI entry pattern. build_pptx.py is a CLI script; broad-except at
# the top-level entry catches all errors and emits a clean message rather
# than a stack trace to a non-technical founder.
broad-except::plugins/investor-coach/scripts/build_pptx.py::407: CLI top-level entry; clean error reporting to founder

# _wpxlib.py: 2 cases of broad-except that need per-case review.
# Not bulk-allowlisting — these may be real findings. Mark for
# sulis-execution maintainer follow-up.
broad-except::plugins/sulis/scripts/_wpxlib.py::177: needs sulis-execution maintainer review
broad-except::plugins/sulis/scripts/_wpxlib.py::2139: needs sulis-execution maintainer review

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
broad-except::plugins/sulis/skills/check-security/scripts/scanner.py::268: tool-wrapper boundary catch (semgrep)
broad-except::plugins/sulis/skills/check-security/scripts/scanner.py::287: tool-wrapper boundary catch (gitleaks)
broad-except::plugins/sulis/skills/check-security/scripts/scanner.py::302: tool-wrapper boundary catch (trivy)
broad-except::plugins/sulis/skills/check-security/scripts/scanner.py::317: tool-wrapper boundary catch (testssl)
broad-except::plugins/sulis/skills/check-security/scripts/scanner.py::329: tool-wrapper boundary catch (curl_probe)
broad-except::plugins/sulis/skills/check-security/scripts/scanner.py::594: tool-wrapper boundary catch (main-level v0.24.0+; line shifted by SEC-02 emission addition)
broad-except::plugins/sulis/skills/check-maintainability/scripts/scanner.py::652: CQ-05 git-log analysis boundary catch (v0.22.0+)
