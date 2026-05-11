import AVFoundation
import Foundation
import FluidAudio

actor SpeakerTranscriber {
    let streamId: String
    let streamIdx: UInt32

    private var asrManager: SlidingWindowAsrManager?
    private var updatesTask: Task<Void, Never>?
    private var lastEmittedEnd: Double = 0
    private let sampleRate: Double

    init(
        streamId: String,
        streamIdx: UInt32,
        sampleRate: Int,
        asrModels: AsrModels,
        onPartial: @escaping @Sendable (String) async -> Void,
        onFinal: @escaping @Sendable (String, Double, Double) async -> Void
    ) async throws {
        self.streamId = streamId
        self.streamIdx = streamIdx
        self.sampleRate = Double(sampleRate)

        let manager = SlidingWindowAsrManager(config: AsrConfigBuilder.fromEnvironment())
        try await manager.loadModels(asrModels)
        try await manager.startStreaming(source: .microphone)
        self.asrManager = manager

        let updates = await manager.transcriptionUpdates
        self.updatesTask = Task { [weak self] in
            for await update in updates {
                guard self != nil else { return }
                if update.isConfirmed {
                    let previousEnd = await self?.lastEmittedEnd ?? 0
                    let newTokens = update.tokenTimings.filter { Double($0.startTime) >= previousEnd }
                    guard let first = newTokens.first, let last = newTokens.last else { continue }
                    let text = newTokens.map { $0.token }.joined()
                    let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
                    if trimmed.isEmpty { continue }
                    let newEnd = Double(last.endTime)
                    await self?.setLastEmittedEnd(newEnd)
                    await onFinal(text, Double(first.startTime), newEnd)
                } else if !update.text.isEmpty {
                    await onPartial(update.text)
                }
            }
        }
    }

    func feedPCM(_ data: Data) async {
        guard let manager = asrManager,
              let buffer = PCMBufferDecoder.decode(littleEndianInt16: data, sampleRate: sampleRate)
        else { return }
        await manager.streamAudio(buffer)
    }

    private func setLastEmittedEnd(_ value: Double) {
        lastEmittedEnd = value
    }

    func finish() async {
        guard let manager = asrManager else { return }
        do {
            _ = try await manager.finish()
        } catch {
            FileHandle.standardError.write(Data("stream \(streamId) finish error: \(error)\n".utf8))
        }
        updatesTask?.cancel()
        updatesTask = nil
        asrManager = nil
    }
}
