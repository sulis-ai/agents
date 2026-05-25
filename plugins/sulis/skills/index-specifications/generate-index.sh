#!/bin/bash
# Generate INDEX.md from .specifications/*/SPEC.yaml files
#
# Usage: ./generate-index.sh [specs-dir]
# Default specs-dir: .specifications/ in the current working directory
# Ships with the srd plugin at srd/skills/spec-index/
#
# Requires: yq (https://github.com/mikefarah/yq) for YAML parsing
# Install: brew install yq

set -euo pipefail

SPECS_DIR="${1:-.specifications}"
INDEX_FILE="$SPECS_DIR/INDEX.md"

# Check for yq
if ! command -v yq &> /dev/null; then
  echo "Error: yq is required but not installed. Install with: brew install yq" >&2
  exit 1
fi

# Collect all SPEC.yaml files
SPEC_FILES=$(find "$SPECS_DIR" -maxdepth 2 -name 'SPEC.yaml' | sort)

if [ -z "$SPEC_FILES" ]; then
  echo "No SPEC.yaml files found in $SPECS_DIR" >&2
  exit 1
fi

# Start building the index
cat > "$INDEX_FILE" << 'HEADER'
# Specification Index

> **Generated file.** Do not edit directly — regenerate with `./scripts/generate-index.sh`
> or `/sulis:index-specifications`. Source of truth is each folder's `SPEC.yaml`.

| Status | Meaning |
|--------|---------|
| draft | Specification session not yet started |
| in-progress | Specification session started, not complete |
| specified | SRD artifacts produced, not yet implemented |
| implemented | Merged into the agent/skills, version noted |
| verified | Tested in facilitation sessions and confirmed working |

---

## Specifications

| ID | Name | Type | Status | Version | Owner | Folder |
|----|------|------|--------|---------|-------|--------|
HEADER

# Parse each SPEC.yaml and add a row
while IFS= read -r spec_file; do
  dir=$(dirname "$spec_file")
  folder=$(basename "$dir")

  id=$(yq -r '.id // "—"' "$spec_file")
  name=$(yq -r '.name // "—"' "$spec_file")
  type=$(yq -r '.type // "—"' "$spec_file")
  status=$(yq -r '.status // "—"' "$spec_file")
  version=$(yq -r '.version // "—"' "$spec_file")
  owner=$(yq -r '.owner // "—"' "$spec_file")

  # Normalise null/empty version
  if [ "$version" = "null" ] || [ -z "$version" ]; then
    version="—"
  fi

  echo "| $id | $name | $type | $status | $version | $owner | \`$folder/\` |" >> "$INDEX_FILE"
done <<< "$SPEC_FILES"

# Add artifact completeness matrix
cat >> "$INDEX_FILE" << 'SECTION'

---

## Artifact Completeness

| ID | Folder | SRD | Diagrams | NFR | Glossary | Completeness | Handover | Journal |
|----|--------|-----|----------|-----|----------|-------------|----------|---------|
SECTION

while IFS= read -r spec_file; do
  dir=$(dirname "$spec_file")
  folder=$(basename "$dir")
  id=$(yq -r '.id // "—"' "$spec_file")

  check_file() { [ -f "$dir/$1" ] && echo "Yes" || echo "—"; }
  check_dir() { [ -d "$dir/$1" ] && echo "Yes" || echo "—"; }

  srd=$(check_file "SRD.md")
  diagrams=$(check_dir "diagrams")
  nfr=$(check_file "NFR.md")
  glossary=$(check_file "GLOSSARY.md")
  completeness=$(check_file "COMPLETENESS_REPORT.md")
  handover=$(check_file "HANDOVER.md")
  journal=$(check_file "EXPLORATION_JOURNAL.md")

  echo "| $id | \`$folder/\` | $srd | $diagrams | $nfr | $glossary | $completeness | $handover | $journal |" >> "$INDEX_FILE"
done <<< "$SPEC_FILES"

# Add counter info
NEXT_ID=$(cat "$SPECS_DIR/.next-id" 2>/dev/null || echo "?")
cat >> "$INDEX_FILE" << EOF

---

*Next specification ID: SPEC-$(printf '%03d' "$NEXT_ID")*
*Generated: $(date -u '+%Y-%m-%dT%H:%M:%SZ')*
EOF

echo "Generated $INDEX_FILE with $(echo "$SPEC_FILES" | wc -l | tr -d ' ') specifications"
