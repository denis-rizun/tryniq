import importlib

import pytest

SUITES = (
    "synthetic_foundation",
    "asr_final",
    "asr_live",
    "diarization",
    "graph_extraction",
    "metadata_extraction",
    "rag_retrieval",
    "rag_answer",
    "similarity",
    "related_meetings",
    "end_to_end",
)


@pytest.mark.parametrize("module_name", SUITES)
def test_suite_exports_action_compatible_experiment(module_name: str) -> None:
    module = importlib.import_module(f"tryniq_evals.suites.{module_name}")
    assert callable(module.experiment)
    assert module.DEFINITION.dataset_name.startswith(
        f"tryniq/{module.DEFINITION.suite}/{module.DEFINITION.version}/"
    )
