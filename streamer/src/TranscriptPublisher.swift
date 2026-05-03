import Foundation

actor TranscriptPublisher {
    private let task: URLSessionWebSocketTask

    init(task: URLSessionWebSocketTask) {
        self.task = task
    }

    func publishPartial(streamId: String, text: String) async {
        let message = PartialTranscriptMessage(
            stream_id: streamId,
            text: text,
            timestamp: Self.nowIso8601()
        )
        await send(message)
    }

    func publishFinal(streamId: String, text: String, tStart: Double, tEnd: Double) async {
        let message = FinalTranscriptMessage(
            stream_id: streamId,
            text: text,
            t_start: tStart,
            t_end: tEnd,
            client_utterance_id: UUID().uuidString,
            timestamp: Self.nowIso8601()
        )
        await send(message)
    }

    private func send<Message: Encodable>(_ message: Message) async {
        guard let data = try? JSONEncoder().encode(message),
              let text = String(data: data, encoding: .utf8) else { return }
        try? await task.send(.string(text))
    }

    private static func nowIso8601() -> String {
        ISO8601DateFormatter().string(from: Date())
    }
}
