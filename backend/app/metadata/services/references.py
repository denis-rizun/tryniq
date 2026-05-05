from uuid import UUID

from app.metadata.schemas import ExtractedMetadata
from app.participant.models import Participant
from app.transcript.models import Utterance


class MetadataReferences:
    def __init__(self, utterances: list[Utterance], participants: list[Participant]) -> None:
        self.utterances = utterances
        self.participants = participants
        self.utterance_by_token: dict[str, UUID] = {
            f"u{idx:03d}": u.id for idx, u in enumerate(utterances, start=1)
        }
        self.person_by_token: dict[str, UUID] = {self.get_person_ref(p.id): p.id for p in participants}

    @staticmethod
    def get_person_ref(participant_id: UUID) -> str:
        return f"p_{participant_id}"

    def format_user_message(self) -> str:
        name_by_id = {p.id: p.name for p in self.participants}
        person_lines = ["participants:"]
        for token, pid in self.person_by_token.items():
            person_lines.append(f"  [{token}] {name_by_id.get(pid, 'Unknown')}")

        pid_to_token = {pid: token for token, pid in self.person_by_token.items()}
        token_by_uid = {uid: token for token, uid in self.utterance_by_token.items()}
        utt_lines = ["utterances:"]
        for u in self.utterances:
            token = token_by_uid.get(u.id, "")
            person_token = pid_to_token.get(u.participant_id, "p_unknown")
            utt_lines.append(
                f"  [{token}] participant=[{person_token}] t={u.t_start:.2f}-{u.t_end:.2f}: {u.text}"
            )

        return "\n".join([*person_lines, "", *utt_lines])

    def collect_bad_refs(self, metadata: ExtractedMetadata) -> set[str]:
        bad: set[str] = set()
        topic_temp_ids = {t.temp_id for t in metadata.topics}

        for d in metadata.decisions:
            self._check_utterances(d.source_utterance_refs, bad)
            self._check_person(d.decided_by_person_ref, bad)
            self._check_topics(d.topic_refs, topic_temp_ids, bad)
        for a in metadata.action_items:
            self._check_utterances(a.source_utterance_refs, bad)
            self._check_person(a.assignee_person_ref, bad)
            self._check_topics(a.topic_refs, topic_temp_ids, bad)
        for q in metadata.open_questions:
            self._check_utterances(q.source_utterance_refs, bad)
            self._check_topics(q.topic_refs, topic_temp_ids, bad)
        return bad

    def correction_message(self, original: str, errors: str, bad_refs: set[str]) -> str:
        legal_utt = ", ".join(sorted(self.utterance_by_token.keys())[:50])
        legal_person = ", ".join(sorted(self.person_by_token.keys())[:20])
        suffix = f"\n\nYour previous response was rejected. Issues: {errors[:300]}. "
        if bad_refs:
            suffix += f"Unknown ids referenced: {sorted(bad_refs)[:20]}. "
        suffix += (
            f"Use ONLY these utterance tokens: [{legal_utt}]. "
            f"Use ONLY these person tokens: [{legal_person}]. "
            "Topic refs must match temp_ids you create in the same response."
        )
        return original + suffix

    def _check_utterances(self, refs: list[str], bad: set[str]) -> None:
        for ref in refs:
            if ref not in self.utterance_by_token:
                bad.add(ref)

    def _check_person(self, ref: str | None, bad: set[str]) -> None:
        if ref and ref not in self.person_by_token:
            bad.add(ref)

    @staticmethod
    def _check_topics(refs: list[str], known: set[str], bad: set[str]) -> None:
        for ref in refs:
            if ref not in known:
                bad.add(ref)
