# Per-project security allowlist

One entry per line. Format: `signature: reason` OR `signature` alone.
Lines starting with `#` are comments.

# Marketplace's own test-credential-runner intentionally includes fake AWS keys
# to test sea:probe's credential-detection capability. Not real keys.
AWS Access Key ID::plugins/sea/skills/probe/tests/integration/test_end_to_end_polyglot.py::144::AKIA1234…: sea:probe test fixture for credential detection
AWS Access Key ID::plugins/sea/skills/probe/tests/unit/test_credential_runner.py::180::AKIA1234…: sea:probe test fixture
AWS Access Key ID::plugins/sea/skills/probe/tests/unit/test_credential_runner.py::193::AKIA1234…: sea:probe test fixture
AWS Access Key ID::plugins/sea/skills/probe/tests/unit/test_credential_runner.py::205::AKIA9999…: sea:probe test fixture
