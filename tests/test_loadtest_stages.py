"""Stress profile used by scripts/loadtest/locustfile.py (LOAD_SHAPE=stress)."""

import importlib.util
import sys
from pathlib import Path

_path = Path(__file__).resolve().parent.parent / "scripts" / "loadtest" / "stages.py"
_spec = importlib.util.spec_from_file_location("stages", _path)
stages = importlib.util.module_from_spec(_spec)
sys.modules["stages"] = stages
_spec.loader.exec_module(stages)


def test_steps_from_100_to_300_users_then_recovers():
    users = [s.users for s in stages.STRESS_STAGES]
    assert users == [100, 150, 200, 250, 300, 20]
    assert stages.total_duration() == 12 * 60


def test_target_at_stage_boundaries():
    assert stages.target_at(0) == (100, 10)
    assert stages.target_at(119.9) == (100, 10)
    assert stages.target_at(120) == (150, 10)
    assert stages.target_at(599) == (300, 10)
    assert stages.target_at(600) == (20, 50)


def test_target_at_ends_the_test():
    assert stages.target_at(stages.total_duration()) is None
