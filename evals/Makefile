.PHONY: help env eval-infra-up eval-infra-down dataset-foundation \
	eval-smoke eval-nightly eval-release eval-speech-final eval-speech-live \
	eval-speech-diarization eval-online-once

UV ?= uv
PYTHON ?= 3.13
BACKEND_PATH := $(abspath ../backend)
RUN := PYTHONPATH=$(BACKEND_PATH) $(UV) run --python $(PYTHON) --all-extras

ifneq (,$(wildcard .env))
include .env
export
endif

help:
	@echo "Langfuse-native evaluation targets"
	@echo "  make env                       lock and install Python 3.13 eval dependencies"
	@echo "  make eval-infra-up             start isolated Postgres/Redis/MinIO + app workers"
	@echo "  make dataset-foundation        immutably sync the synthetic smoke dataset"
	@echo "  make eval-smoke                run the dataset-backed foundation experiment"
	@echo "  make eval-nightly              run graph, metadata, RAG, and similarity suites"
	@echo "  make eval-release              run release suites and enforce approved baselines"
	@echo "  make eval-speech-final         run final ASR on its production host"
	@echo "  make eval-speech-live          drive the Swift streamer through the real WS contract"
	@echo "  make eval-speech-diarization   run diarization on its production host"
	@echo "  make eval-online-once          score one capped deterministic online sample"
	@echo
	@echo "Canonical results are stored only in Langfuse; every target prints its run URL."

env:
	$(UV) lock --python $(PYTHON)
	$(UV) sync --python $(PYTHON) --all-extras

eval-infra-up:
	docker compose --profile eval -f compose.yml up --build -d

eval-infra-down:
	docker compose --profile eval -f compose.yml down

dataset-foundation:
	$(RUN) python -c "from pathlib import Path; from langfuse import Langfuse; from tryniq_evals.datasets.manifest import SourceManifest; from tryniq_evals.datasets.sync import load_envelopes,synchronize_dataset; root=Path('.'); manifest=SourceManifest.load(root/'datasets/manifests/synthetic-foundation-1.0.0-smoke.yaml'); print(synchronize_dataset(Langfuse(),manifest,load_envelopes(root/manifest.items_file)))"

eval-smoke:
	$(RUN) python -c "from tryniq_evals.suites.synthetic_foundation import DEFINITION,experiment; from tryniq_evals.suites.support import local_context,print_result; print_result(experiment(local_context(DEFINITION.dataset_name)))"

eval-nightly:
	$(RUN) python -c "from tryniq_evals.suites.graph_extraction import DEFINITION,experiment; from tryniq_evals.suites.support import local_context,print_result; print_result(experiment(local_context(DEFINITION.dataset_name)))"
	$(RUN) python -c "from tryniq_evals.suites.metadata_extraction import DEFINITION,experiment; from tryniq_evals.suites.support import local_context,print_result; print_result(experiment(local_context(DEFINITION.dataset_name)))"
	$(RUN) python -c "from tryniq_evals.suites.rag_retrieval import DEFINITION,experiment; from tryniq_evals.suites.support import local_context,print_result; print_result(experiment(local_context(DEFINITION.dataset_name)))"
	$(RUN) python -c "from tryniq_evals.suites.rag_answer import DEFINITION,experiment; from tryniq_evals.suites.support import local_context,print_result; print_result(experiment(local_context(DEFINITION.dataset_name)))"
	$(RUN) python -c "from tryniq_evals.suites.similarity import DEFINITION,experiment; from tryniq_evals.suites.support import local_context,print_result; print_result(experiment(local_context(DEFINITION.dataset_name)))"

eval-release:
	EVAL_RUN_PURPOSE=release $(RUN) python -c "from tryniq_evals.suites.graph_extraction import DEFINITION,experiment; from tryniq_evals.suites.support import local_context,print_result,qualify_release; result=experiment(local_context(DEFINITION.dataset_name)); print_result(result); qualify_release(result,DEFINITION)"
	EVAL_RUN_PURPOSE=release $(RUN) python -c "from tryniq_evals.suites.rag_retrieval import DEFINITION,experiment; from tryniq_evals.suites.support import local_context,print_result,qualify_release; result=experiment(local_context(DEFINITION.dataset_name)); print_result(result); qualify_release(result,DEFINITION)"
	EVAL_RUN_PURPOSE=release $(RUN) python -c "from tryniq_evals.suites.rag_answer import DEFINITION,experiment; from tryniq_evals.suites.support import local_context,print_result,qualify_release; result=experiment(local_context(DEFINITION.dataset_name)); print_result(result); qualify_release(result,DEFINITION)"

eval-speech-final:
	$(RUN) python -c "from tryniq_evals.suites.asr_final import DEFINITION,experiment; from tryniq_evals.suites.support import local_context,print_result; print_result(experiment(local_context(DEFINITION.dataset_name)))"

eval-speech-live:
	$(RUN) python -c "from tryniq_evals.suites.asr_live import DEFINITION,experiment; from tryniq_evals.suites.support import local_context,print_result; print_result(experiment(local_context(DEFINITION.dataset_name)))"

eval-speech-diarization:
	$(RUN) python -c "from tryniq_evals.suites.diarization import DEFINITION,experiment; from tryniq_evals.suites.support import local_context,print_result; print_result(experiment(local_context(DEFINITION.dataset_name)))"

eval-online-once:
	$(RUN) python -m tryniq_evals.online_worker
