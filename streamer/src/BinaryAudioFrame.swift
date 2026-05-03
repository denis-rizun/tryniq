import Foundation

struct BinaryAudioFrame {
    let streamIdx: UInt32
    let sequence: UInt32
    let pcm: Data

    static func parse(_ data: Data) -> BinaryAudioFrame? {
        guard data.count >= 8 else { return nil }
        let streamIdx = data.subdata(in: 0..<4).withUnsafeBytes { $0.load(as: UInt32.self).littleEndian }
        let sequence = data.subdata(in: 4..<8).withUnsafeBytes { $0.load(as: UInt32.self).littleEndian }
        return BinaryAudioFrame(
            streamIdx: streamIdx,
            sequence: sequence,
            pcm: data.subdata(in: 8..<data.count)
        )
    }
}
