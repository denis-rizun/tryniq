"""Generate a synthetic multi-speaker meeting audio file for upload testing.

Uses macOS `say` (different voice per speaker) plus `ffmpeg` to concatenate
turns with short silences. Output is an mp3 mixed-down meeting recording.

Usage:
    python backend/scripts/generate_test_meeting.py [output_path]

Defaults output to ``test-data/test-meeting.mp3`` at the repo root.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# (display_name, say_voice)
SPEAKERS = {
    "Alice": "Samantha",   # PM
    "Bob": "Daniel",       # Eng lead
    "Carol": "Karen",      # Designer
    "Dave": "Fred",        # CEO
}

# Conversational script — covers: kickoff, Q2 roadmap, infra migration,
# customer churn, design system, hiring, action items.
SCRIPT: list[tuple[str, str]] = [
    ("Alice", "Good morning everyone, thanks for joining the Q2 planning sync. I think we have Bob, Carol, and Dave on. Let's go through the agenda real quick."),
    ("Dave", "Morning. Before we start, I want to flag that the board meeting moved to May twentieth, so anything we decide today should land before then."),
    ("Alice", "Got it. Agenda is roadmap review, the Postgres migration, the churn investigation Carol pulled together, and hiring. Bob, do you want to kick us off with the roadmap?"),
    ("Bob", "Sure. The big rocks for Q2 are the new ingestion pipeline, the search rewrite, and the mobile beta. The pipeline is on track, search slipped by about two weeks because we found a regression in ranking, and mobile is blocked on hiring an iOS engineer."),
    ("Dave", "What is the customer impact of the search slip?"),
    ("Bob", "Minimal for now. The old ranker is still serving traffic. The risk is if we do not ship by end of June we will not have time to A B test before the enterprise renewals in August."),
    ("Carol", "From a design side I already have the new results page ready, so whenever the backend lands I can ship the front end in a couple of days."),
    ("Alice", "Great. Let's commit to a June twentieth date for the search rewrite to be in production. Bob, can you own that?"),
    ("Bob", "Yes, I will own June twentieth for search in prod."),
    ("Alice", "Action item logged. Next, the Postgres migration. Bob, where are we?"),
    ("Bob", "We finished the dry run on staging last Friday. The dump and restore took about four hours on the full data set. We are planning to do production on a Saturday night, probably May seventeenth, with a one hour maintenance window."),
    ("Dave", "Saturday the seventeenth works for me. Make sure support knows so they can post a status page notice."),
    ("Bob", "Will do. I also want to flag that we will lose the read replica for about thirty minutes during cutover, so any analytics jobs need to be paused."),
    ("Carol", "I had a question about that. Will the migration affect the embeddings table? We just added the pgvector column last week."),
    ("Bob", "Good catch. Yes, it will. I will double check the dump includes the extension and the vector index. Let me take that as an action item."),
    ("Alice", "Action item: Bob to verify pgvector data and index survive the migration, by May tenth so we have a buffer."),
    ("Alice", "Ok, churn. Carol, you pulled some numbers, walk us through it."),
    ("Carol", "So in March we lost eleven accounts, which is double February. I dug into the cancellation reasons and seven of them mentioned the dashboard being slow or confusing. Three were price related, and one was an acquisition."),
    ("Dave", "Seven out of eleven on UX. That is a strong signal. What is your hypothesis on the dashboard?"),
    ("Carol", "Two things. First, the initial load is genuinely slow, about six seconds on a cold cache. Second, the empty state is bad. New users land and do not know what to click. I think we can fix the empty state in a sprint and it will move the needle."),
    ("Bob", "On the load time, I think we can knock two or three seconds off by paginating the activity feed. That is a small change."),
    ("Alice", "Let's pair those up. Carol, can you own the empty state redesign? And Bob, the pagination change. Target end of May."),
    ("Carol", "Yes, I can have a draft by next Wednesday."),
    ("Bob", "Pagination I can probably ship this week."),
    ("Dave", "I want to push back gently on the price thing. Three out of eleven is not nothing. Are these all on the starter plan?"),
    ("Carol", "Two on starter, one on pro. The pro one specifically said they could not justify the cost without the reporting features that are coming in Q3."),
    ("Dave", "Ok. That is a product gap, not a pricing problem. Let's not change pricing."),
    ("Alice", "Agreed. Moving on to design system. Carol?"),
    ("Carol", "Quick update. The new component library is ninety percent migrated. Buttons, inputs, modals, tables all done. The remaining piece is the chart components, which depend on the search rewrite landing first because the new charts use the new query API."),
    ("Bob", "Makes sense. We will coordinate."),
    ("Alice", "Last topic, hiring. Dave?"),
    ("Dave", "We have the iOS role open, the senior backend role, and we are about to open a second designer role. The iOS one is the most urgent because it is blocking mobile beta. We have two candidates in final round next week."),
    ("Carol", "On the designer role, I would really like someone with a research background. Our last few hires have all been visual designers."),
    ("Dave", "Noted. I will update the job description. Carol, can you send me three or four bullet points on what research skills matter most?"),
    ("Carol", "Will do, by Friday."),
    ("Alice", "Ok let me read back the action items. Bob owns search in production by June twentieth. Bob owns verifying pgvector survives the migration by May tenth. Bob ships activity feed pagination this week. Carol owns the empty state redesign with a draft by next Wednesday. Carol sends Dave research skill bullets by Friday. Dave updates the designer job description. Anything I missed?"),
    ("Bob", "I think that's it."),
    ("Carol", "Looks complete to me."),
    ("Dave", "One more thing. Can someone open a question for the next sync about whether we should accelerate the mobile beta if we do not close the iOS hire by end of May? I do not want to decide today, but it should be on the agenda."),
    ("Alice", "Open question logged. Let's revisit on May thirteenth. Thanks everyone, good meeting."),
    ("Bob", "Thanks all."),
    ("Carol", "Thanks, bye."),
    ("Dave", "Bye."),
]


def check_tools() -> None:
    for tool in ("say", "ffmpeg"):
        if shutil.which(tool) is None:
            sys.exit(f"required tool not found on PATH: {tool}")


def synthesize_turn(text: str, voice: str, out_path: Path) -> None:
    # `say` writes AIFF natively. We pipe through ffmpeg to get a normalized wav.
    aiff_path = out_path.with_suffix(".aiff")
    subprocess.run(
        ["say", "-v", voice, "-r", "180", "-o", str(aiff_path), text],
        check=True,
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(aiff_path),
            "-ac", "1", "-ar", "16000",
            str(out_path),
        ],
        check=True,
    )
    aiff_path.unlink()


def make_silence(duration_s: float, out_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"anullsrc=r=16000:cl=mono",
            "-t", f"{duration_s}",
            str(out_path),
        ],
        check=True,
    )


def main() -> None:
    check_tools()

    repo_root = Path(__file__).resolve().parents[2]
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else repo_root / "test-data" / "test-meeting.mp3"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        silence = tmp_dir / "silence.wav"
        make_silence(0.35, silence)

        concat_lines: list[str] = []
        for i, (speaker, text) in enumerate(SCRIPT):
            voice = SPEAKERS[speaker]
            turn = tmp_dir / f"turn_{i:03d}.wav"
            synthesize_turn(text, voice, turn)
            concat_lines.append(f"file '{turn}'")
            concat_lines.append(f"file '{silence}'")
            print(f"[{i + 1:02d}/{len(SCRIPT)}] {speaker} ({voice}): {text[:60]}{'...' if len(text) > 60 else ''}")

        concat_list = tmp_dir / "concat.txt"
        concat_list.write_text("\n".join(concat_lines))

        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "concat", "-safe", "0",
                "-i", str(concat_list),
                "-c:a", "libmp3lame", "-b:a", "96k",
                str(out_path),
            ],
            check=True,
        )

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(out_path)],
        check=True, capture_output=True, text=True,
    )
    duration = float(probe.stdout.strip())
    minutes, seconds = divmod(duration, 60)
    print(f"\nWrote {out_path} ({int(minutes)}m {seconds:.1f}s, {len(SCRIPT)} turns, {len(SPEAKERS)} speakers)")


if __name__ == "__main__":
    main()
