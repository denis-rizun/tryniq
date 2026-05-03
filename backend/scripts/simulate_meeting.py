"""Seed a synthetic meeting (no audio) and run build_graph.

Run inside the worker container:
    docker compose exec -T worker python -m scripts.simulate_meeting

Pipes:
    cat scripts/transcripts/quick.txt | docker compose exec -T worker python -m scripts.simulate_meeting --stdin
"""

import argparse
import asyncio
import sys
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import structlog

from app.db import async_session
from app.graph.tasks import build_graph
from app.meeting.constants import MeetingStatus
from app.meeting.models import Meeting, MeetingRoom
from app.participant.models import Participant
from app.tasks import broker
from app.transcript.models import Utterance

logger = structlog.get_logger()


SAMPLE_LINES: list[tuple[str, str]] = [
    ("Sara", "Okay, let's kick off the weekly platform sync. I want to cover three things: "
            "the eu-west-1 incident, the auth migration, and the Q3 hiring plan."),
    ("Sara", "First, the incident. The rollback yesterday worked, but my analysis shows the canary "
            "missed the regression because the synthetic checks don't hit the payment endpoint."),
    ("Sara", "So I want us to roll back any further deploys to eu-west-1 until we fix that. Agreed? "
            "Yes, let's do it."),
    ("Sara", "Mark, can you draft the postmortem by Friday and get it in front of the SRE guild "
            "before Monday standup?"),
    ("Mark", "Yeah, I'll have it by Friday."),
    ("Sara", "Second, the auth migration. We're moving off the legacy session tokens because Legal "
            "flagged them as non-compliant under the new policy."),
    ("Sara", "Anna, you're owning the rollout. Please book a working session with the security team "
            "this week."),
    ("Sara", "One thing I'm not sure about: do we need to coordinate with the mobile team on the "
            "token format, or can they keep using the old SDK during the transition? "
            "Let's leave that as an open question for now and revisit on Thursday."),
    ("Sara", "Third, hiring. We have two open roles, a senior backend engineer and an SRE. "
            "I'm interviewing the backend candidate Wednesday."),
    ("Sara", "Mike, are you free to do the systems-design round?"),
    ("Mike", "Yeah, sure. Send me the calendar invite."),
    ("Sara", "Oh, and one more thing. Datadog will be down for maintenance Saturday from 2 to 4 UTC. "
            "Just so everyone knows, no action needed."),
    ("Sara", "Okay, that's it. Thanks everyone."),
]


def parse_stdin() -> list[tuple[str, str]]:
    lines: list[tuple[str, str]] = []
    for raw in sys.stdin:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            print(f"skipping malformed line (need 'speaker: text'): {line!r}", file=sys.stderr)
            continue
        speaker, text = line.split(":", 1)
        lines.append((speaker.strip(), text.strip()))
    return lines


async def seed(lines: list[tuple[str, str]], title: str, meet_code: str) -> UUID:
    speakers = sorted({s for s, _ in lines})
    started = datetime.now(UTC) - timedelta(minutes=10)
    ended = datetime.now(UTC)

    async with async_session() as session:
        room = MeetingRoom(meet_code=meet_code, title=title)
        session.add(room)
        await session.flush()

        meeting = Meeting(
            title=title,
            status=MeetingStatus.FINAL,
            started_at=started,
            ended_at=ended,
            room_id=room.id,
        )
        session.add(meeting)
        await session.flush()

        participant_by_speaker: dict[str, Participant] = {}
        for idx, name in enumerate(speakers):
            p = Participant(
                meeting_id=meeting.id,
                stream_id=uuid4(),
                name=name,
                is_local_user=(idx == 0),
            )
            session.add(p)
            await session.flush()
            participant_by_speaker[name] = p

        cursor = 0.0
        for speaker, text in lines:
            duration = max(2.0, len(text) / 18.0)
            participant = participant_by_speaker[speaker]
            session.add(
                Utterance(
                    meeting_id=meeting.id,
                    participant_id=participant.id,
                    stream_id=participant.stream_id,
                    t_start=cursor,
                    t_end=cursor + duration,
                    text=text,
                    confidence=0.95,
                    model="simulator",
                    is_final=True,
                )
            )
            cursor += duration + 0.4

        await session.commit()
        return meeting.id


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a synthetic meeting and build its graph")
    parser.add_argument("--title", default="Simulated meeting")
    parser.add_argument("--meet-code", default=None, help="defaults to a random sim-XXXXXXXX code")
    parser.add_argument("--stdin", action="store_true", help="read 'speaker: text' lines from stdin")
    parser.add_argument("--no-graph", action="store_true", help="skip build_graph after seeding")
    args = parser.parse_args()

    lines = parse_stdin() if args.stdin else SAMPLE_LINES
    if not lines:
        print("no lines provided", file=sys.stderr)
        sys.exit(1)

    code = args.meet_code or f"sim-{uuid4().hex[:8]}"
    meeting_id = await seed(lines, args.title, code)
    print(f"seeded meeting_id = {meeting_id}")
    print(f"  participants    = {len({s for s, _ in lines})}")
    print(f"  utterances      = {len(lines)}")
    print(f"  meet_code       = {code}")

    if args.no_graph:
        return

    await broker.startup()
    try:
        task = await build_graph.kiq(str(meeting_id), None, None)
        print(f"enqueued build_graph task_id = {task.task_id}")
        result = await task.wait_result(timeout=180)
        if result.is_err:
            print(f"build_graph FAILED: {result.error}")
            sys.exit(2)
        print("build_graph done. fetch with:")
        print(f"  curl http://localhost:8000/api/v1/meetings/{meeting_id}/graph")
        print(f"  open http://localhost:3000/meetings/{meeting_id}/graph")
    finally:
        await broker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
