#!/usr/bin/env bash
# Inject the autoreward validation-tiers policy into YOUR project's CLAUDE.md
# (or AGENTS.md). Idempotent - re-running updates the block in place.
# Usage:  bash install.sh [/path/to/your/project] [CLAUDE.md|AGENTS.md]
set -u
WITH_AR=0; POS=()
for a in "$@"; do
  if [ "$a" = "--with-autoresearch" ]; then WITH_AR=1; else POS+=("$a"); fi
done
TARGET="${POS[0]:-$PWD}"
FILE="${POS[1]:-CLAUDE.md}"
ATLAS="$(cd "$(dirname "$0")" && pwd)"
DST="$TARGET/$FILE"
BEGIN="<!-- BEGIN autoreward validation-tiers (injected) -->"
END="<!-- END autoreward validation-tiers -->"

POLICY="$(sed -n '/^```markdown$/,/^```$/p' "$ATLAS/AGENT_POLICY.md" | sed '1d;$d')"

BLOCK="$BEGIN
$POLICY

autoreward reference (read when building a gauge):
- $ATLAS/gauges/by-goal.md   - worked examples by workflow goal, copy & adapt
- $ATLAS/models/index.json   - B-proxy models by domain + reliability ranking
- $ATLAS/README.md           - the full method
$END"

mkdir -p "$TARGET"
if [ -f "$DST" ] && grep -qF "$BEGIN" "$DST"; then
  awk -v b="$BEGIN" -v e="$END" 'index($0,b){s=1} !s{print} index($0,e){s=0}' "$DST" > "$DST.tmp" && mv "$DST.tmp" "$DST"
  echo "updated existing autoreward block in $DST"
else
  echo "adding autoreward block to $DST"
fi
printf '\n%s\n' "$BLOCK" >> "$DST"
echo "done. Your agent now frames validation as A/B/C (C>B>A) and can consult the atlas."

if [ "$WITH_AR" = 1 ]; then
  AR_DIR="$(dirname "$ATLAS")/autoresearch"
  if [ ! -d "$AR_DIR" ]; then
    echo "cloning karpathy/autoresearch -> $AR_DIR"
    git clone --depth 1 https://github.com/karpathy/autoresearch "$AR_DIR" || echo "clone failed - clone it manually"
  else echo "autoresearch already present at $AR_DIR"; fi
  echo "connect the reward: see $ATLAS/CONNECT.md + $ATLAS/integrations/autoresearch_bridge.py"
fi
