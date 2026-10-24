"""Tests for scripts/ops with fake gcloud and curl binaries on PATH, so no GCP access is needed."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "scripts" / "ops"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="bash not available")

# Canned answers keyed on the gcloud subcommand; every call is appended to $GCLOUD_LOG
FAKE_GCLOUD = r"""#!/usr/bin/env bash
echo "gcloud $*" >> "$GCLOUD_LOG"
case "$*" in
  "run services describe"*"status.traffic[0].revisionName"*) echo "labtrack-api-00003-ccc" ;;
  "run services describe"*"status.url"*) echo "https://labtrack-api.example.run.app" ;;
  "run revisions list"*) printf '%s\n' labtrack-api-00004-ddd labtrack-api-00003-ccc labtrack-api-00002-bbb labtrack-api-00001-aaa ;;
  "sql instances list"*) echo "labtrack-db-ab12" ;;
esac
exit 0
"""

FAKE_CURL = """#!/usr/bin/env bash
echo '{"status":"ok"}'
"""


@pytest.fixture()
def fake_env(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("gcloud", FAKE_GCLOUD), ("curl", FAKE_CURL)):
        path = bin_dir / name
        path.write_text(body, newline="\n")
        path.chmod(0o755)
    log = tmp_path / "gcloud.log"
    log.touch()
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "PROJECT_ID": "labtrack-test",
        "REGION": "asia-southeast2",
        "GCLOUD_LOG": str(log),
    }
    return env, log


def run_script(name: str, *args: str, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [BASH, str(OPS / name), *args], env=env, capture_output=True, text=True, timeout=60
    )


def gcloud_calls(log: Path) -> list[str]:
    return log.read_text().splitlines()


def test_scripts_require_project_id(fake_env):
    env, _ = fake_env
    env = {k: v for k, v in env.items() if k != "PROJECT_ID"}
    r = run_script("scale.sh", "0", "3", env=env)
    assert r.returncode != 0
    assert "Set PROJECT_ID" in r.stderr


def test_rollback_picks_revision_before_the_serving_one(fake_env):
    env, log = fake_env
    r = run_script("rollback.sh", env=env)
    assert r.returncode == 0, r.stderr
    traffic = [c for c in gcloud_calls(log) if "update-traffic" in c]
    assert len(traffic) == 1
    assert "--to-revisions=labtrack-api-00002-bbb=100" in traffic[0]


def test_rollback_to_explicit_revision_and_back_to_latest(fake_env):
    env, log = fake_env
    assert run_script("rollback.sh", "labtrack-api-00001-aaa", env=env).returncode == 0
    assert run_script("rollback.sh", "--to-latest", env=env).returncode == 0
    traffic = [c for c in gcloud_calls(log) if "update-traffic" in c]
    assert "--to-revisions=labtrack-api-00001-aaa=100" in traffic[0]
    assert "--to-latest" in traffic[1]


def test_scale_rejects_min_above_max(fake_env):
    env, log = fake_env
    r = run_script("scale.sh", "4", "2", env=env)
    assert r.returncode == 1
    assert not any("services update" in c for c in gcloud_calls(log))


def test_scale_warns_when_connection_budget_is_exceeded(fake_env):
    env, log = fake_env
    r = run_script("scale.sh", "1", "4", env=env)
    assert r.returncode == 0, r.stderr
    assert "WARNING: 4 instances x 7 connections = 28" in r.stderr
    assert any("--min-instances=1 --max-instances=4" in c for c in gcloud_calls(log))


@pytest.mark.parametrize(("action", "policy"), [("stop", "NEVER"), ("start", "ALWAYS")])
def test_sql_start_stop_sets_activation_policy(fake_env, action, policy):
    env, log = fake_env
    r = run_script("sql-start-stop.sh", action, env=env)
    assert r.returncode == 0, r.stderr
    patch = [c for c in gcloud_calls(log) if "sql instances patch" in c]
    assert patch == [f"gcloud sql instances patch labtrack-db-ab12 --project=labtrack-test --activation-policy={policy} --quiet"]


def test_sql_start_stop_rejects_unknown_action(fake_env):
    env, _ = fake_env
    assert run_script("sql-start-stop.sh", "reboot", env=env).returncode == 1


def test_vm_ssh_uses_iap_tunnel(fake_env):
    env, log = fake_env
    r = run_script("vm-ssh.sh", "uptime", env=env)
    assert r.returncode == 0, r.stderr
    (call,) = [c for c in gcloud_calls(log) if "compute ssh" in c]
    assert "--tunnel-through-iap" in call and "--zone=asia-southeast2-a" in call
