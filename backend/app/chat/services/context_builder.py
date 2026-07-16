from app.chat.constants import ChatScope
from app.chat.services.graph_hits import GraphHit
from app.chat.services.retrieval import RetrievedContext, UtteranceHit


class ContextBuilder:
    @staticmethod
    def build(scope: ChatScope, context: RetrievedContext) -> tuple[str, str]:
        utterance_lines = [ContextBuilder._format_utterance(scope, hit) for hit in context.utterances]
        graph_lines = [ContextBuilder._format_graph(scope, hit) for hit in context.graph_nodes]
        utterance_block = "\n".join(utterance_lines) if utterance_lines else "(none)"
        graph_block = "\n".join(graph_lines) if graph_lines else "(none)"
        return utterance_block, graph_block

    @staticmethod
    def _format_utterance(scope: ChatScope, hit: UtteranceHit) -> str:
        meeting_part = ""
        if scope == ChatScope.ALL and hit.meeting_started_at:
            meeting_part = f" meeting={hit.meeting_started_at.date().isoformat()}"
        speaker_part = f" speaker={hit.speaker}" if hit.speaker else ""
        return f"[{hit.ref}] t={format_mmss(hit.t_start)}{meeting_part}{speaker_part}: {hit.text}"

    @staticmethod
    def _format_graph(scope: ChatScope, hit: GraphHit) -> str:
        meeting_part = ""
        if scope == ChatScope.ALL and hit.meeting_started_at:
            meeting_part = f" meeting={hit.meeting_started_at.date().isoformat()}"
        return f"[{hit.ref}] {hit.type}{meeting_part}: {hit.text}"


def format_mmss(t: float) -> str:
    total = max(0, int(t))
    return f"{total // 60:02d}:{total % 60:02d}"
