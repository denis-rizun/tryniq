/// <reference path="./audio-worklet.d.ts" />

const TARGET_SAMPLE_RATE = 16000;
const FRAME_SAMPLES = 3200;
const PROCESSOR_NAME = "tryniq-capture";
const INT16_NEGATIVE_SCALE = 0x8000;
const INT16_POSITIVE_SCALE = 0x7fff;

class TryniqCaptureProcessor extends AudioWorkletProcessor {
  private readonly decimationRatio: number;
  private bucketSum = 0;
  private bucketSampleCount = 0;
  private decimationPhase = 0;
  private outputFrame = new Int16Array(FRAME_SAMPLES);
  private outputIndex = 0;

  constructor() {
    super();
    this.decimationRatio = sampleRate / TARGET_SAMPLE_RATE;
  }

  process(inputs: Float32Array[][]): boolean {
    const channel = inputs[0]?.[0];
    if (!channel || channel.length === 0) return true;

    for (let i = 0; i < channel.length; i++) {
      this.bucketSum += channel[i] ?? 0;
      this.bucketSampleCount += 1;
      this.decimationPhase += 1;
      if (this.decimationPhase < this.decimationRatio) continue;

      const averagedSample = this.bucketSum / this.bucketSampleCount;
      this.bucketSum = 0;
      this.bucketSampleCount = 0;
      this.decimationPhase -= this.decimationRatio;

      const clamped = Math.max(-1, Math.min(1, averagedSample));
      this.outputFrame[this.outputIndex++] = clamped < 0
        ? Math.round(clamped * INT16_NEGATIVE_SCALE)
        : Math.round(clamped * INT16_POSITIVE_SCALE);

      if (this.outputIndex < FRAME_SAMPLES) continue;
      const buffer = this.outputFrame.buffer.slice(0);
      this.port.postMessage({ kind: "pcm", t: currentTime, pcm: buffer }, [buffer]);
      this.outputIndex = 0;
    }
    return true;
  }
}

registerProcessor(PROCESSOR_NAME, TryniqCaptureProcessor);
