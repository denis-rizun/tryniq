import AVFoundation
import Foundation
import FluidAudio

actor SpeakerTranscriber {
    let streamId: String
    let streamIdx: UInt32

    private var asrManager: SlidingWindowAsrManager?
    private var updatesTask: Task<Void, Never>?
    private var samplesProcessed: Int = 0
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
        let sampleRateCopy = self.sampleRate
        self.updatesTask = Task { [weak self] in
            for await update in updates {
                guard self != nil else { return }
                let processed = await self?.samplesProcessed ?? 0
                let (tStart, tEnd) = TranscriptTiming.range(
                    update: update,
                    sampleRate: sampleRateCopy,
                    samplesProcessed: processed
                )
                if update.isConfirmed {
                    await onFinal(update.text, tStart, tEnd)
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
        samplesProcessed += Int(buffer.frameLength)
        await manager.streamAudio(buffer)
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
