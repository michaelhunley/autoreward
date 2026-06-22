#!/usr/bin/env bash
# Inject the Gauge Atlas validation-tiers policy into YOUR project's CLAUDE.md
# (or AGENTS.md). Idempotent - re-running updates the block in place.
# Usage:  bash install.sh [/path/to/your/project] [CLAUDE.md|AGENTS.md]
set -u
TARGET="${1:-$PWD}"
FILE="${2:-CLAUDE.md}"
ATLAS="$(cd "$(dirname "$0")" && pwd)"
DST="$TARGET/$FILE"
BEGIN="<!-- BEGIN gauge-atlas validation-tiers (injected) -->"
END="<!-- END gauge-atlas validation-tiers -->"

POLICY="$(sed -n '/^```markdown$/,/^```$/p' "$ATLAS/AGENT_POLICY.md" | sed '1d;$d')"

BLOCK="$BEGIN
$POLICY

Gauge Atlas reference (read when building a gauge):
- $ATLAS/gauges/by-goal.md   - worked examples by workflow goal, copy & adapt
- $ATLAS/models/index.json   - B-proxy models by domain + reliability ranking
- $ATLAS/README.md           - the full method
$END"

mkdir -p "$TARGET"
if [ -f "$DST" ] && grep -qF "$BEGIN" "$DST"; then
  awk -v b="$BEGIN" -v e="$END" 'index($0,b){s=1} !s{print} index($0,e){s=0}' "$DST" > "$DST.tmp" && mv "$DST.tmp" "$DST"
  echo "updated existing gauge-atlas block in $DST"
else
  echo "adding gauge-atlas block to $DST"
fi
printf '\n%s\n' "$BLOCK" >> "$DST"
echo "done. Your agent now frames validation as A/B/C (C>B>A) and can consult the atlas."
