from __future__ import annotations

from pathlib import Path

import yaml

from tryniq_evals.gates.models import GateException, SuiteGatePolicy


def load_policies(path: Path) -> dict[str, SuiteGatePolicy]:
    payload = yaml.safe_load(path.read_text()) or {}
    policies = [SuiteGatePolicy.model_validate(item) for item in payload.get("suites", [])]
    if len({policy.suite for policy in policies}) != len(policies):
        raise ValueError("gate policy contains duplicate suites")
    return {policy.suite: policy for policy in policies}


def load_exceptions(path: Path) -> tuple[GateException, ...]:
    payload = yaml.safe_load(path.read_text()) or {}
    return tuple(GateException.model_validate(item) for item in payload.get("exceptions", []))
