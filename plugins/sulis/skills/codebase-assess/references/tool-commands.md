# Tool Commands

Invocations for the automated tools the assessment uses. Each tool has a
Docker variant (preferred — no install required) and a native-binary
variant (faster if installed). If neither is available, the relevant
primitive defaults to `NOT ASSESSED` and the coverage gap is noted in
Methodology.

The `$ASSESS_DIR` variable is set in the skill's Setup phase:
`/tmp/security-assessment/{project}-$(date +%s)/`.

---

## Gitleaks — Secret Detection (SEC-07, DAT-04, INF-02)

**Docker:**

```bash
docker run --rm -v "$ASSESS_DIR/repo:/src:ro" zricethezav/gitleaks:latest \
  detect --source /src --report-format sarif --report-path /dev/stdout \
  > "$ASSESS_DIR/outputs/gitleaks.sarif" 2>/dev/null
```

**Native:**

```bash
gitleaks detect --source "$ASSESS_DIR/repo" \
  --report-format sarif \
  --report-path "$ASSESS_DIR/outputs/gitleaks.sarif"
```

**Full history (when initial clone was --depth 1):**

```bash
cd "$ASSESS_DIR/repo" && git fetch --unshallow && cd -
# Then run gitleaks again as above
```

**Parsing the SARIF:** look for `results[].level == "error"` for critical
findings, `level == "warning"` for high. Each result has `locations[].physicalLocation.artifactLocation.uri` (file) and `region.startLine` (line).

---

## Trivy — Dependency CVEs, Container Scan, SBOM (SC-01..SC-04, INF-01)

**Docker (filesystem scan):**

```bash
docker run --rm -v "$ASSESS_DIR/repo:/src:ro" aquasec/trivy:latest \
  fs --scanners vuln,secret,misconfig --format json /src \
  > "$ASSESS_DIR/outputs/trivy.json" 2>/dev/null
```

**Native:**

```bash
trivy fs --scanners vuln,secret,misconfig --format json "$ASSESS_DIR/repo" \
  > "$ASSESS_DIR/outputs/trivy.json"
```

**SBOM generation (SC-03):**

```bash
trivy fs --format spdx-json "$ASSESS_DIR/repo" \
  > "$ASSESS_DIR/outputs/trivy-sbom.spdx.json"
```

**Container image scan (INF-01 — if Dockerfile builds an image):**

```bash
# Build the image
docker build -t "assess-${PROJECT}:latest" "$ASSESS_DIR/repo"

# Scan it
trivy image --format json "assess-${PROJECT}:latest" \
  > "$ASSESS_DIR/outputs/trivy-image.json"

# Clean up
docker rmi "assess-${PROJECT}:latest"
```

**Parsing:** `Results[].Vulnerabilities[]` contains the CVE list. Filter
by `Severity == "CRITICAL"` or `"HIGH"` for the report.

---

## Semgrep — SAST (SEC-01 through SEC-06, INF-04)

**Docker:**

```bash
docker run --rm -v "$ASSESS_DIR/repo:/src:ro" returntocorp/semgrep \
  semgrep --config auto --severity WARNING --sarif -o /dev/stdout /src \
  > "$ASSESS_DIR/outputs/semgrep.sarif" 2>/dev/null
```

**Native (via pip):**

```bash
semgrep --config auto --severity WARNING --sarif \
  -o "$ASSESS_DIR/outputs/semgrep.sarif" "$ASSESS_DIR/repo"
```

**Higher-signal rulesets:**

```bash
# OWASP Top 10 specifically
semgrep --config "p/owasp-top-ten" --sarif \
  -o "$ASSESS_DIR/outputs/semgrep-owasp.sarif" "$ASSESS_DIR/repo"

# Security-only rules
semgrep --config "p/security-audit" --sarif \
  -o "$ASSESS_DIR/outputs/semgrep-security.sarif" "$ASSESS_DIR/repo"
```

**Parsing:** standard SARIF — `runs[0].results[]`. Each result has a rule
ID (often maps to OWASP or CWE), severity, and location.

---

## lizard — Cyclomatic Complexity (CQ-01)

**Native (pip install):**

```bash
lizard -l python -l javascript -l typescript -l java -l go \
  --xml "$ASSESS_DIR/repo" > "$ASSESS_DIR/outputs/lizard.xml"
```

**Heuristic fallback (if lizard not available):**

```bash
# Find functions over 100 lines as proxy for high complexity
for f in $(find "$ASSESS_DIR/repo" -type f \( -name '*.js' -o -name '*.ts' -o -name '*.py' -o -name '*.go' -o -name '*.java' \)); do
  awk '/^(function|def|public|private|protected|func) /,/^}|^$/' "$f" | wc -l
done | sort -n | tail -20 > "$ASSESS_DIR/outputs/long-functions.txt"
```

---

## hadolint — Dockerfile Lint (INF-01)

**Docker:**

```bash
for df in $(find "$ASSESS_DIR/repo" -name "Dockerfile*"); do
  docker run --rm -i hadolint/hadolint < "$df" \
    >> "$ASSESS_DIR/outputs/hadolint.txt" 2>&1
done
```

**Native:**

```bash
find "$ASSESS_DIR/repo" -name "Dockerfile*" -exec hadolint {} \; \
  > "$ASSESS_DIR/outputs/hadolint.txt" 2>&1
```

---

## testssl.sh — TLS Analysis (DAT-02)

**Native (recommended — Docker variant exists but the script is small):**

```bash
testssl.sh --quiet --color 0 --severity HIGH \
  --logfile "$ASSESS_DIR/outputs/testssl.log" \
  {deployed-url}
```

**curl-based fallback (header-level only):**

```bash
curl -sI --tlsv1.2 {deployed-url} | head -50 > "$ASSESS_DIR/outputs/tls-headers.txt"
```

---

## HTTP Security Headers (INF-03)

**Always available (curl):**

```bash
URL={deployed-url}
{
  echo "=== Status ==="
  curl -sI "$URL" | head -1
  echo
  echo "=== Security Headers ==="
  curl -sI "$URL" | grep -iE "strict-transport-security|content-security-policy|x-frame-options|x-content-type-options|referrer-policy|permissions-policy"
  echo
  echo "=== Common Exposure Probes ==="
  for path in .env .git/config .DS_Store robots.txt sitemap.xml .well-known/security.txt; do
    code=$(curl -s -o /dev/null -w "%{http_code}" "$URL/$path")
    echo "$code  $URL/$path"
  done
} > "$ASSESS_DIR/outputs/headers.txt"
```

---

## Git History Analysis (CQ-05)

**Always available:**

```bash
cd "$ASSESS_DIR/repo"

# Direct-to-main commit ratio
TOTAL=$(git log --oneline --first-parent main | wc -l)
MERGES=$(git log --oneline --merges main | wc -l)
DIRECT=$((TOTAL - MERGES))
echo "Total first-parent commits: $TOTAL" > "$ASSESS_DIR/outputs/git-review.txt"
echo "Merge commits: $MERGES" >> "$ASSESS_DIR/outputs/git-review.txt"
echo "Direct-to-main: $DIRECT ($(awk "BEGIN {printf \"%.0f\", $DIRECT/$TOTAL*100}")%)" >> "$ASSESS_DIR/outputs/git-review.txt"

# Recent activity
echo "Commits in last 6 months: $(git log --oneline --since='6 months ago' | wc -l)" >> "$ASSESS_DIR/outputs/git-review.txt"

# PR template presence
[ -f ".github/pull_request_template.md" ] && echo "PR template: yes" >> "$ASSESS_DIR/outputs/git-review.txt" || echo "PR template: no" >> "$ASSESS_DIR/outputs/git-review.txt"

# Branch protection check requires GitHub API — flag in hypothesis if not checkable
cd -
```

---

## Technical Debt Markers (CQ-04)

**Always available (heuristic):**

```bash
DEBT=$(grep -rn --include="*.{js,ts,py,rb,go,java,rs,kt,swift}" \
  -E "TODO|FIXME|HACK|XXX|TEMPORARY|WORKAROUND" "$ASSESS_DIR/repo" | wc -l)
LOC=$(find "$ASSESS_DIR/repo" -type f \( -name '*.js' -o -name '*.ts' -o -name '*.py' -o -name '*.go' \) -exec cat {} + | wc -l)
echo "Debt markers: $DEBT" > "$ASSESS_DIR/outputs/tech-debt.txt"
echo "Estimated LOC: $LOC" >> "$ASSESS_DIR/outputs/tech-debt.txt"
echo "Density: $(awk "BEGIN {printf \"%.2f per 1k LOC\", $DEBT/$LOC*1000}")" >> "$ASSESS_DIR/outputs/tech-debt.txt"
```

---

## PII/PHI Pattern Scan (DAT-03)

**Always available (heuristic — high false-positive rate, verify before flagging):**

```bash
# Email addresses in non-test source
grep -rn --include="*.{js,ts,py,rb,go,java}" \
  -E "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" \
  "$ASSESS_DIR/repo/src" 2>/dev/null \
  | grep -vE "(test|spec|fixture|mock|example)" \
  | head -50 > "$ASSESS_DIR/outputs/pii-emails.txt"

# SSN patterns
grep -rn --include="*.{js,ts,py,rb,go,java}" \
  -E "\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b" "$ASSESS_DIR/repo" \
  | head -20 > "$ASSESS_DIR/outputs/pii-ssn.txt"
```

---

## Dependency File Inventory (SC-01, SC-02)

**Always available:**

```bash
{
  echo "=== Dependency files present ==="
  for f in package.json yarn.lock pnpm-lock.yaml package-lock.json \
           requirements.txt poetry.lock Pipfile.lock \
           Gemfile Gemfile.lock \
           go.mod go.sum \
           Cargo.toml Cargo.lock \
           pom.xml build.gradle build.gradle.kts; do
    [ -f "$ASSESS_DIR/repo/$f" ] && echo "  $f"
  done

  echo
  echo "=== Direct dependency count (where countable) ==="
  [ -f "$ASSESS_DIR/repo/package.json" ] && \
    echo "  npm dependencies: $(python3 -c "import json; d=json.load(open('$ASSESS_DIR/repo/package.json')); print(len(d.get('dependencies',{})))")"
  [ -f "$ASSESS_DIR/repo/requirements.txt" ] && \
    echo "  python requirements: $(grep -cE '^[a-zA-Z]' "$ASSESS_DIR/repo/requirements.txt")"
  [ -f "$ASSESS_DIR/repo/go.mod" ] && \
    echo "  go modules: $(grep -c '^\s*[^v]' "$ASSESS_DIR/repo/go.mod")"
} > "$ASSESS_DIR/outputs/deps.txt"
```

---

## Tool Availability Probe

Run at the start of Cycle 1 to determine which tools are usable.

```bash
{
  echo "=== Tool availability ==="
  command -v docker      >/dev/null && echo "docker:    yes" || echo "docker:    no"
  command -v gitleaks    >/dev/null && echo "gitleaks:  yes (native)" || echo "gitleaks:  via docker only"
  command -v trivy       >/dev/null && echo "trivy:     yes (native)" || echo "trivy:     via docker only"
  command -v semgrep     >/dev/null && echo "semgrep:   yes (native)" || echo "semgrep:   via docker only"
  command -v lizard      >/dev/null && echo "lizard:    yes" || echo "lizard:    no — use heuristic"
  command -v hadolint    >/dev/null && echo "hadolint:  yes (native)" || echo "hadolint:  via docker only"
  command -v testssl.sh  >/dev/null && echo "testssl:   yes" || echo "testssl:   no — curl fallback"
  command -v jq          >/dev/null && echo "jq:        yes" || echo "jq:        no — use python3 for JSON"
  command -v python3     >/dev/null && echo "python3:   yes" || echo "python3:   no (required for JWT — block App auth)"
} > "$ASSESS_DIR/outputs/tool-probe.txt"
```

If neither Docker nor a native tool is available for a primitive, that
primitive gets `NOT ASSESSED` status. The report's Methodology section
lists which tools were unavailable.

---

## Cleanup

After all tool outputs are collected and parsed, move the kept outputs into
the user's project folder:

```bash
mkdir -p .security/{project}/tool-outputs
cp "$ASSESS_DIR/outputs/"*.{sarif,json,xml,txt,log} \
   .security/{project}/tool-outputs/ 2>/dev/null
```

Then delete the temp directory:

```bash
rm -rf "$ASSESS_DIR"
```
