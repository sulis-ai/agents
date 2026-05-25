# Per-project security allowlist

One entry per line. Format: `signature: reason` OR `signature` alone.
Lines starting with `#` are comments.

# Marketplace's own test-credential-runner intentionally includes fake AWS keys
# to test sea:probe's credential-detection capability. Not real keys.
AWS Access Key ID::plugins/sulis/skills/analyse-codebase/tests/integration/test_end_to_end_polyglot.py::144::AKIA1234…: sea:probe test fixture for credential detection
AWS Access Key ID::plugins/sulis/skills/analyse-codebase/tests/unit/test_credential_runner.py::180::AKIA1234…: sea:probe test fixture
AWS Access Key ID::plugins/sulis/skills/analyse-codebase/tests/unit/test_credential_runner.py::193::AKIA1234…: sea:probe test fixture
AWS Access Key ID::plugins/sulis/skills/analyse-codebase/tests/unit/test_credential_runner.py::205::AKIA9999…: sea:probe test fixture

# Gitleaks variants of the same sea:probe test fixtures (v0.20.0+ wrapper integration)
gitleaks::generic-api-key::plugins/sulis/skills/analyse-codebase/tests/unit/test_credential_runner.py::46: sea:probe test fixture
gitleaks::generic-api-key::plugins/sulis/skills/analyse-codebase/tests/unit/test_credential_runner.py::59: sea:probe test fixture
gitleaks::generic-api-key::plugins/sulis/skills/analyse-codebase/tests/unit/test_credential_runner.py::180: sea:probe test fixture

# Semgrep-found documentation example AWS keys (canonical AKIAIOSFODNN7EXAMPLE etc.)
semgrep::generic.secrets.security.detected-aws-access-key-id-value.detected-aws-access-key-id-value::plugins/sulis/skills/check-security/COMPLETENESS_REPORT.md::41: documentation example AWS key in skill report
semgrep::generic.secrets.security.detected-aws-access-key-id-value.detected-aws-access-key-id-value::plugins/sulis/skills/check-security/references/security-patterns.md::102: documentation example AWS key in skill reference doc

# Real XXE + SHA1 findings in sea + sulis-execution — surfaced for review,
# not allowlisted (legitimate concerns). Maintainers track via the findings
# themselves. Documented here for transparency:
# semgrep::python.lang.security.use-defused-xml.use-defused-xml::plugins/sulis/skills/analyse-codebase/scripts/probe/workspace.py::40 — XXE vuln; needs defusedxml swap
# semgrep::python.lang.security.use-defused-xml-parse.use-defused-xml-parse::plugins/sulis/skills/analyse-codebase/scripts/probe/workspace.py::269 — XXE vuln; needs defusedxml swap
# semgrep::python.lang.security.insecure-hash-algorithms.insecure-hash-algorithm-sha1::plugins/sulis-execution/scripts/wpx-findings::40 — SHA1 usage; non-cryptographic hash use likely intentional but should be reviewed
