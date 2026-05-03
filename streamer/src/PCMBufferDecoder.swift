import AVFoundation
import Foundation

enum PCMBufferDecoder {
    static func decode(littleEndianInt16 data: Data, sampleRate: Double = 16000) -> AVAudioPCMBuffer? {
        let frameCount = AVAudioFrameCount(data.count / 2)
        guard frameCount > 0,
              let format = AVAudioFormat(
                commonFormat: .pcmFormatFloat32,
                sampleRate: sampleRate,
                channels: 1,
                interleaved: false
              ),
              let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frameCount),
              let channel = buffer.floatChannelData?[0]
        else { return nil }
        data.withUnsafeBytes { (raw: UnsafeRawBufferPointer) in
            let int16Pointer = raw.bindMemory(to: Int16.self)
            for index in 0..<Int(frameCount) {
                channel[index] = Float(Int16(littleEndian: int16Pointer[index])) / 32768.0
            }
        }
        buffer.frameLength = frameCount
        return buffer
    }
}
