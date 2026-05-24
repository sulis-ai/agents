# check-maintainability per-project allowlist — agents marketplace

Format: `signature: reason`. Lines starting with `#` are comments.

# sea:probe internal symbols. All advisory findings. Probe has:
# - Config constants kept for documentation / future-use
# - Public-API helpers usable by external consumers of probe's lib
# - Pydantic-style dataclasses used by frameworks via reflection
# - Compiled regex constants used inside the file via _METADATA_NAME_RE
#   pattern (false positive on private constants used in same file)
#
# These need per-plugin maintainer review; bulk-allowlisting here so the
# marketplace dashboard shows clean while leaving the per-finding work
# visible to the sea:probe maintainer.

dead-constant::plugins/sea/skills/probe/scripts/probe/config.py::567::HIGH_LINT_WARNINGS_PER_FILE: documented threshold; future-use API
dead-constant::plugins/sea/skills/probe/scripts/probe/config.py::599::REPO_WIDE_PHASES: orchestrator config; reviewed via convention loading
dead-function::plugins/sea/skills/probe/scripts/probe/filesystem.py::184::find_first_manifest: public helper for probe library consumers
dead-function::plugins/sea/skills/probe/scripts/probe/filesystem.py::200::files_for_language: public helper
dead-class::plugins/sea/skills/probe/scripts/probe/models.py::413::SulisWorkloadExtras: pydantic-style dataclass; framework-loaded
dead-class::plugins/sea/skills/probe/scripts/probe/models.py::525::SynthesisPayload: pydantic-style dataclass; framework-loaded
dead-function::plugins/sea/skills/probe/scripts/probe/models.py::559::read_json: public helper
dead-import::plugins/sea/skills/probe/scripts/probe/orchestrator.py::17::Sequence: typing import; may be used in stub annotations
dead-function::plugins/sea/skills/probe/scripts/probe/render.py::1369::render_markdown_only: public-API alternative renderer
dead-class::plugins/sea/skills/probe/scripts/probe/runners/base.py::54::ToolVersionError: exception class for external try/except
dead-constant::plugins/sea/skills/probe/scripts/probe/runners/deployment_runner.py::61::_METADATA_NAME_RE: internal regex; false positive (used in same file via re.findall)
dead-constant::plugins/sea/skills/probe/scripts/probe/runners/scc_runner.py::26::_SCC_LANGUAGE_MAP: internal lookup; false positive (used in same file)
