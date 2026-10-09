#!/usr/bin/env bash
# Open an issue for a failed scheduled run, or comment on the one already open.
set -euo pipefail

title="Scheduled run failed: ${GITHUB_WORKFLOW}"
run_url="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
body="The scheduled ${GITHUB_WORKFLOW} run failed on $(date -u +%Y-%m-%d): ${run_url}"

# Exact title match on open issues; the title reaches jq as data, not code.
existing=$(TITLE="$title" gh issue list --repo "$GITHUB_REPOSITORY" --state open \
  --limit 200 --json number,title \
  --jq 'map(select(.title == env.TITLE)) | .[0].number // empty')

if [ -n "$existing" ]; then
  gh issue comment "$existing" --repo "$GITHUB_REPOSITORY" --body "$body"
else
  gh issue create --repo "$GITHUB_REPOSITORY" --title "$title" --body "${body}

Close this issue once the cause is fixed. Until then, later failures are added here as comments."
fi
