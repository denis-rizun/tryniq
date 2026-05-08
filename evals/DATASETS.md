# Datasets

All datasets land under `<repo>/datasets/` by default (override via `TRYNIQ_EVALS_CACHE`). The directory is in the project `.gitignore` — never commit audio. Total disk on a full prepare is well under 50 GB; subsetting flags are documented per dataset below.

## Registry

| Dataset                  | Style                                    | Speakers | Hours used          | License            | Acquisition                                                                                          |
|--------------------------|------------------------------------------|----------|---------------------|--------------------|------------------------------------------------------------------------------------------------------|
| `librispeech_test_clean` | Read audiobooks (clean)                  | single   | ~5.4 h              | CC-BY-4.0          | [openslr/librispeech_asr](https://huggingface.co/datasets/openslr/librispeech_asr) — `test.clean`    |
| `librispeech_test_other` | Read audiobooks (harder, accented/noisy) | single   | ~5.1 h              | CC-BY-4.0          | same, `test.other`                                                                                   |
| `ami_subset`             | Real meetings, multi-mic                 | 4        | ~1.5 h (3 meetings) | CC-BY-4.0 (gated)  | [edinburghcstr/ami](https://huggingface.co/datasets/edinburghcstr/ami) — picks `ES2004a/b/c`         |
| `earnings21`             | Long-form business meetings              | varies   | ~3 h subset         | CC-BY-4.0          | [revdotcom/speech-datasets](https://github.com/revdotcom/speech-datasets) — `earnings21/`            |
| `chime6_dev`             | Far-field overlapped meeting audio       | 4        | varies              | LDC (non-comm.)    | [CHiME-6 download](https://www.chimechallenge.org/challenges/chime6/download) — **manual**           |

## Acquisition

```bash
make env

uv run eval prepare librispeech_test_clean
uv run eval prepare librispeech_test_other
uv run eval prepare ami_subset            # gated; needs HF_TOKEN
uv run eval prepare earnings21
uv run eval prepare chime6_dev            # manual; see "CHiME-6 manual acquisition" below
```

Or just `make prepare-all`.

### Hugging Face authentication

`ami_subset` and the `pyannote/speaker-diarization-3.1` weights are gated. Accept the model/dataset terms on Hugging Face once, then either:

```bash
huggingface-cli login    # writes token to ~/.cache/huggingface/
# or
export HF_TOKEN=hf_xxx
```

The harness reads `HF_TOKEN` from the environment and passes it through to model loaders.

### CHiME-6 manual acquisition

CHiME-6 is distributed via LDC under restrictive terms — we never auto-download it.

1. Register and download from <https://www.chimechallenge.org/challenges/chime6/download>.
2. Extract the release tree under `<repo>/datasets/_chime6_raw/` (or anywhere reachable, then `export CHIME6_ROOT=/absolute/path`).
3. Run `uv run eval prepare chime6_dev`.

Expected layout (the loader walks the tree, so minor variations are OK):

```
<root>/audio/dev/SXX_*.wav
<root>/transcriptions/dev/SXX.json
```

If `prepare` errors with `CHiME-6 dev not found`, double-check the env var or path.

## Ground-truth manifest format

After `prepare`, every dataset is normalized to a flat manifest the runner consumes:

```jsonl
{"id": "1089-134686-0000", "audio": "/abs/path/to/clip.flac", "text": "HE HOPED THERE WOULD BE STEW ...", "speakers": null, "duration_s": 6.41}
```

For multi-speaker datasets, `text` is a path to an `.stm` file and `speakers` is an `.rttm` path. The runner's `read_reference()` parses STM correctly (extracts only the text column; ignores `;;` comments and `IGNORE_TIME_SEGMENT_IN_SCORING` markers).

```jsonl
{"id": "ES2004a", "audio": ".../ES2004a.wav", "text": ".../ES2004a.stm", "speakers": ".../ES2004a.rttm", "duration_s": 1632.0}
```

The runner reads `<cache>/<dataset>/manifest.jsonl` directly; if it's missing, run `prepare` first.

## Subsetting

For smoke runs and local iteration:

```bash
uv run eval run faster_whisper_large_v3_turbo librispeech_test_clean --limit 25
uv run eval prepare ami_subset --max-meetings 1
uv run eval prepare chime6_dev --max-meetings 1
```

## Why these specific datasets?

- **LibriSpeech test-clean / test-other** — canonical ASR yardstick; numbers are directly comparable to published model cards.
- **AMI subset** — meeting-shaped with overlapping speakers and ground-truth diarization labels (RTTM). Necessary for honest DER numbers.
- **Earnings-21** — long-form, real business-call English. Closest in shape to what a tl;dv replacement actually has to handle.
- **CHiME-6 dev** — far-field, heavy overlap, kitchen-noise meetings. The hardest realistic eval; if a diarization model holds up here it'll hold up in deployment.

We deliberately don't include LibriSpeech `train-*` (overfitting risk) or CommonVoice (different normalization conventions inflate WER unfairly). VoxConverse, DIHARD-III, TEDLIUM-3 are deferred until CHiME-6 has informed an actual model decision.

## License & attribution

Each dataset's license is stubbed into `<cache>/<dataset>/LICENSE` after `prepare`. Don't redistribute the audio — only the WER/DER numbers and model checksums in `results/`.
