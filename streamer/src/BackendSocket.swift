import Foundation
import FluidAudio

actor BackendSocket {
    private let url: URL
    private let workerId: String
    private let asrModels: AsrModels

    init(backendBaseUrl: String, authToken: String, workerId: String, asrModels: AsrModels) {
        var components = URLComponents(string: "\(backendBaseUrl)/api/v1/asr/sessions")!
        components.queryItems = [URLQueryItem(name: "token", value: authToken)]
        self.url = components.url!
        self.workerId = workerId
        self.asrModels = asrModels
    }

    func runForever() async {
        var backoffSeconds: UInt64 = 1
        while !Task.isCancelled {
            do {
                try await runOneConnection()
                backoffSeconds = 1
            } catch {
                FileHandle.standardError.write(
                    Data("ws error: \(error); reconnecting in \(backoffSeconds)s\n".utf8)
                )
                try? await Task.sleep(nanoseconds: backoffSeconds * 1_000_000_000)
                backoffSeconds = min(backoffSeconds * 2, 30)
            }
        }
    }

    private func runOneConnection() async throws {
        let urlSession = URLSession(configuration: .default)
        let task = urlSession.webSocketTask(with: url)
        task.resume()

        let publisher = TranscriptPublisher(task: task)
        let sessions = SessionManager(asrModels: asrModels, publisher: publisher)
        defer {
            task.cancel(with: .goingAway, reason: nil)
            Task { await sessions.closeAll() }
        }

        try await sendHandshake(task: task)

        while !Task.isCancelled {
            let message = try await task.receive()
            switch message {
            case .string(let text):
                await sessions.handleControlText(text)
            case .data(let data):
                if let frame = BinaryAudioFrame.parse(data) {
                    await sessions.feedPCM(frame: frame)
                }
            @unknown default:
                continue
            }
        }
    }

    private func sendHandshake(task: URLSessionWebSocketTask) async throws {
        let handshake = HandshakeMessage(
            worker_id: workerId,
            models: ["parakeet-tdt-v2"],
            capacity: 4
        )
        let data = try JSONEncoder().encode(handshake)
        try await task.send(.string(String(data: data, encoding: .utf8)!))
    }
}
