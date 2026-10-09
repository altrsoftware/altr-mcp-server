"""A failed scheduled run opens an issue, not only a notice to the cron's last editor."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
SCRIPT = REPO_ROOT / ".github" / "scripts" / "report-scheduled-failure.sh"
SKIPS_SCHEDULE = "github.event_name != 'schedule'"


def _scheduled_workflows():
    for path in sorted(WORKFLOWS.glob("*.yml")):
        workflow = yaml.safe_load(path.read_text())
        if "schedule" in (workflow.get(True) or {}):  # PyYAML reads `on:` as True
            yield pytest.param(workflow, id=path.name)


@pytest.mark.parametrize("workflow", list(_scheduled_workflows()))
def test_every_scheduled_workflow_reports_its_failures(workflow):
    jobs = workflow["jobs"]
    report = jobs["report-failure"]
    needs = report["needs"]
    needs = [needs] if isinstance(needs, str) else needs
    scheduled = {name for name, job in jobs.items()
                 if name != "report-failure" and job.get("if") != SKIPS_SCHEDULE}

    assert set(needs) == scheduled, "every job the schedule runs"
    assert "github.event_name == 'schedule'" in report["if"]
    # A timed-out job ends as cancelled, which failure() does not catch.
    assert "'failure'" in report["if"] and "'cancelled'" in report["if"]
    assert report["permissions"]["issues"] == "write"
    assert any(str(SCRIPT.relative_to(REPO_ROOT)) in step.get("run", "")
               for step in report["steps"])


@pytest.fixture
def run_script(tmp_path):
    """Run the script against a stand-in `gh` that applies the real --jq filter."""
    if shutil.which("jq") is None:
        pytest.skip("jq is needed to apply the script's filter")
    log = tmp_path / "gh.log"
    issues = tmp_path / "issues.json"
    fake = tmp_path / "gh"
    fake.write_text(
        "#!/usr/bin/env bash\n"
        f'printf "%s\\n" "$*" >> "{log}"\n'
        'if [ "$1 $2" = "issue list" ]; then\n'
        '  prev=""; for arg in "$@"; do [ "$prev" = --jq ] && query=$arg; prev=$arg; done\n'
        f'  jq -r "$query" "{issues}"\n'
        "fi\n")
    fake.chmod(0o755)

    def run(open_issues):
        issues.write_text(json.dumps(open_issues))
        env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}",
               "GITHUB_WORKFLOW": "CI", "GITHUB_SERVER_URL": "https://github.com",
               "GITHUB_REPOSITORY": "owner/repo", "GITHUB_RUN_ID": "42"}
        subprocess.run([str(SCRIPT)], env=env, check=True)  # as the workflow runs it
        return log.read_text().splitlines()
    return run


def test_a_first_failure_opens_an_issue(run_script):
    calls = run_script([])

    create = next(c for c in calls if c.startswith("issue create"))
    assert "--title Scheduled run failed: CI " in create
    assert "https://github.com/owner/repo/actions/runs/42" in create


def test_a_repeat_failure_comments_on_the_open_issue(run_script):
    calls = run_script([{"number": 7, "title": "Scheduled run failed: CI"}])

    assert any(c.startswith("issue comment 7 ") for c in calls)
    assert not any(c.startswith("issue create") for c in calls)


def test_a_near_miss_title_is_not_reused(run_script):
    calls = run_script([{"number": 3, "title": "Scheduled run failed: CI extra"}])

    assert any(c.startswith("issue create") for c in calls)
