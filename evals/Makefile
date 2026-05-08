.PHONY: help env env-all env-faster-whisper env-mlx env-moonshine env-pyannote \
        env-streamer env-diarizen env-cuda \
        prepare-all run-final run-live run-diar run-all report clean-results

PY ?= python3.13
UV ?= uv

help:
	@echo "evals/ — model-card harness"
	@echo
	@echo "Bootstrap:"
	@echo "  make env                    # core uv env (CLI + report)"
	@echo "  make env-faster-whisper     # faster-whisper large-v3-turbo (Mac default)"
	@echo "  make env-mlx                # parakeet-mlx (Apple Silicon)"
	@echo "  make env-moonshine          # Moonshine ONNX (live)"
	@echo "  make env-pyannote           # pyannote-3.1 + Reverb v2 + ECAPA"
	@echo "  make env-streamer           # WS wrapper for prebuilt Swift `streamer` binary"
	@echo "  make env-diarizen           # DiariZen (BUTSpeechFIT, EEND-style diarization)"
	@echo "  make env-cuda               # NVIDIA Canary-Qwen-2.5B + WhisperLive (Linux + CUDA 12.x)"
	@echo "  make env-all                # everything above"
	@echo
	@echo "Datasets:"
	@echo "  make prepare-all            # prepare every dataset"
	@echo "  $(UV) run eval prepare <name>  # one dataset"
	@echo
	@echo "Run:"
	@echo "  make run-final              # all final-ASR models × all datasets"
	@echo "  make run-live               # all live-ASR models × all datasets"
	@echo "  make run-diar               # all diarization models × diarization-truth datasets"
	@echo "  make run-all                # everything"
	@echo "  make report                 # regenerate RESULTS.md and MODEL_CARD.md tables"

env:
	$(UV) sync

env-faster-whisper:
	cd envs/faster-whisper && $(UV) sync

env-mlx:
	cd envs/mlx && $(UV) sync

env-moonshine:
	cd envs/moonshine && $(UV) sync

env-pyannote:
	cd envs/pyannote && $(UV) sync

env-streamer:
	cd envs/streamer && $(UV) sync

env-diarizen:
	cd envs/diarizen && $(UV) sync

env-cuda:
	cd envs/cuda && $(UV) sync

env-all: env env-faster-whisper env-mlx env-moonshine env-pyannote env-streamer env-diarizen env-cuda

prepare-all:
	$(UV) run eval prepare librispeech_test_clean
	$(UV) run eval prepare librispeech_test_other
	$(UV) run eval prepare ami_subset
	$(UV) run eval prepare earnings21
	$(UV) run eval prepare chime6_dev

run-final:
	$(UV) run eval run-family --family final

run-live:
	$(UV) run eval run-family --family live

run-diar:
	$(UV) run eval run-family --family diarization

run-all: run-final run-live run-diar

report:
	$(UV) run eval report

clean-results:
	rm -rf results/*
