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
  "sql backups list"*) echo "1761328800000" ;;
  "sql backups describe"*"value(windowStartTime)"*) echo "2026-10-24T18:00:00Z" ;;
  "compute ssh"*"paste -sd"*) echo "active,active NO_REBOOT_REQUIRED" ;;
esac
exit 0
"""

FAKE_CURL = """#!/usr/bin/env bash
echo '{"status":"ok"}'
"""

# Production (port 6541) has two rows more than the restored copy (6542) in every table
FAKE_PSQL = r"""#!/usr/bin/env bash
case "$*" in
  *port=6541*) echo 14 ;;
  *) echo 12 ;;
esac
"""

FAKE_PROXY = """#!/usr/bin/env bash
sleep 30
"""


@pytest.fixture()
def fake_env(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fakes = (("gcloud", FAKE_GCLOUD), ("curl", FAKE_CURL), ("psql", FAKE_PSQL), ("cloud-sql-proxy", FAKE_PROXY))
    for name, body in fakes:
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


def test_restore_test_writes_verification_report_and_deletes_temp_instance(fake_env, tmp_path):
    env, log = fake_env
    report = tmp_path / "restore.md"
    r = run_script("sql-restore-test.sh", env={**env, "REPORT": str(report), "PROXY_WAIT": "0"})
    assert r.returncode == 0, r.stderr
    calls = gcloud_calls(log)
    (create,) = [c for c in calls if "sql instances create" in c]
    temp = create.split()[4]
    assert temp.startswith("labtrack-restore-test-")
    assert any(c.startswith(f"gcloud sql instances delete {temp} ") for c in calls)
    assert not any("sql instances delete labtrack-db-" in c for c in calls)  # never the source
    text = report.read_text(encoding="utf-8")
    assert "| Hasil | **LULUS** |" in text
    assert "ID 1761328800000, jendela backup 2026-10-24T18:00:00Z" in text
    assert "| students | 14 | 12 | OK |" in text


def test_vm_patch_records_change_log(fake_env, tmp_path):
    env, log = fake_env
    change_log = tmp_path / "change-log.md"
    r = run_script("vm-patch.sh", "--snapshot", env={**env, "CHANGE_LOG": str(change_log)})
    assert r.returncode == 0, r.stderr
    calls = gcloud_calls(log)
    snap = next(i for i, c in enumerate(calls) if "disks snapshot" in c)
    upgrade = next(i for i, c in enumerate(calls) if "apt-get -y" in c)
    assert snap < upgrade  # backup before the change
    rows = [line for line in change_log.read_text(encoding="utf-8").splitlines() if "labtrack-ops |" in line]
    assert len(rows) == 1
    assert "snapshot labtrack-ops-manual-prepatch-" in rows[0]
    assert "active,active NO_REBOOT_REQUIRED" in rows[0]


def test_vm_report_saves_output(fake_env, tmp_path):
    env, log = fake_env
    out = tmp_path / "vm.txt"
    r = run_script("vm-report.sh", env={**env, "OUT": str(out)})
    assert r.returncode == 0, r.stderr
    assert any("compute instances describe labtrack-ops" in c for c in gcloud_calls(log))
    assert any("compute ssh labtrack-ops" in c and "--tunnel-through-iap" in c for c in gcloud_calls(log))
    assert "lscpu" in log.read_text()  # the remote script spans several log lines
    assert "LabTrack VM provisioning report" in out.read_text(encoding="utf-8")
