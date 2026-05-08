
import importlib
from typing import Annotated

import typer
from rich.console import Console

from eval import diar_runner, runner
from eval.decoding import DEFAULT_DECODING, DecodingConfig
from eval.registry import (
    DATASETS,
    MODELS,
    ModelFamily,
    datasets_for_family,
    get_dataset,
    get_model,
    models_for_family,
)

app = typer.Typer(help="tryniq-evals — model-card harness", no_args_is_help=True)
console = Console()


@app.command(name="list")
def list_cmd() -> None:
    console.print("[bold]Models[/bold]")
    for m in MODELS:
        console.print(f"  [cyan]{m.name:<35}[/cyan] family={m.family:<12} env={m.env:<16} {m.description}")
    console.print()
    console.print("[bold]Datasets[/bold]")
    for d in DATASETS:
        flags = []
        if d.multi_speaker:
            flags.append("multi-speaker")
        if d.has_diarization_truth:
            flags.append("diar-truth")
        console.print(f"  [cyan]{d.name:<28}[/cyan] {' '.join(flags):<25} {d.description}")


@app.command()
def prepare(
    dataset: str,
    max_utterances: Annotated[int | None, typer.Option(help="Cap (smoke runs).")] = None,
    max_meetings: Annotated[int | None, typer.Option(help="Cap (multi-speaker datasets).")] = None,
) -> None:
    ds = get_dataset(dataset)
    mod = importlib.import_module(f"eval.datasets.{ds.name}")
    kwargs: dict = {}
    if max_utterances is not None:
        kwargs["max_utterances"] = max_utterances
    if max_meetings is not None:
        kwargs["max_meetings"] = max_meetings
    out = mod.prepare(**kwargs)
    console.print(f"[green]Prepared[/green] {ds.name} → {out}")


def _decoding_from_cli(
    beam_size: int, temperature: float, language: str,
    vad_aggressiveness: int, pace: str,
) -> DecodingConfig:
    return DecodingConfig(
        beam_size=beam_size, temperature=temperature, language=language,
        vad_aggressiveness=vad_aggressiveness, pace=pace,
    )


@app.command()
def run(
    model: str,
    dataset: str,
    limit: Annotated[int | None, typer.Option(help="Run only the first N samples.")] = None,
    timeout: Annotated[float, typer.Option(help="Per-sample timeout in seconds.")] = 600.0,
    warm: Annotated[bool, typer.Option(help="Reuse one adapter subprocess across samples.")] = False,
    beam_size: Annotated[int, typer.Option(help="Beam width.")] = DEFAULT_DECODING.beam_size,
    temperature: Annotated[float, typer.Option()] = DEFAULT_DECODING.temperature,
    language: Annotated[str, typer.Option()] = DEFAULT_DECODING.language,
    vad_aggressiveness: Annotated[int, typer.Option()] = DEFAULT_DECODING.vad_aggressiveness,
    pace: Annotated[str, typer.Option(help='"realtime" or "fast" (live family).')] = DEFAULT_DECODING.pace,
) -> None:
    m = get_model(model)
    d = get_dataset(dataset)
    decoding = _decoding_from_cli(beam_size, temperature, language, vad_aggressiveness, pace)
    if m.family == "diarization":
                                                                                             
        path = diar_runner.run(m, d, limit=limit, timeout_s=timeout)
    else:
        path = runner.run(m, d, limit=limit, timeout_s=timeout, warm=warm, decoding=decoding)
    console.print(f"[green]Wrote[/green] {path}")


@app.command(name="run-family")
def run_family(
    family: ModelFamily,
    limit: Annotated[int | None, typer.Option()] = None,
    timeout: Annotated[float, typer.Option()] = 600.0,
    warm: Annotated[bool, typer.Option()] = False,
    beam_size: Annotated[int, typer.Option()] = DEFAULT_DECODING.beam_size,
    temperature: Annotated[float, typer.Option()] = DEFAULT_DECODING.temperature,
    language: Annotated[str, typer.Option()] = DEFAULT_DECODING.language,
    vad_aggressiveness: Annotated[int, typer.Option()] = DEFAULT_DECODING.vad_aggressiveness,
    pace: Annotated[str, typer.Option()] = DEFAULT_DECODING.pace,
) -> None:
    models = models_for_family(family)
    datasets = datasets_for_family(family)
    decoding = _decoding_from_cli(beam_size, temperature, language, vad_aggressiveness, pace)
    failures: list[tuple[str, str, str]] = []
    successes = 0

    for m in models:
        for d in datasets:
            console.print(f"[bold]→[/bold] {m.name} × {d.name}")
            try:
                if family == "diarization":
                    diar_runner.run(m, d, limit=limit, timeout_s=timeout)
                else:
                    runner.run(m, d, limit=limit, timeout_s=timeout, warm=warm, decoding=decoding)
                successes += 1
            except Exception as e:                                               
                console.print(f"  [red]failed[/red]: {e}")
                failures.append((m.name, d.name, str(e)))

    if failures:
        console.print(
            f"[red]run-family: {len(failures)} failed, {successes} succeeded[/red]"
        )
        for model_name, dataset_name, err in failures:
            console.print(f"  [red]✗[/red] {model_name} × {dataset_name}: {err}")
        raise typer.Exit(code=1)
    console.print(f"[green]run-family: {successes} succeeded[/green]")


@app.command()
def report() -> None:
    from eval import report as report_mod
    report_mod.generate()
    console.print("[green]Regenerated[/green] RESULTS.md and MODEL_CARD.md tables.")


if __name__ == "__main__":
    app()
