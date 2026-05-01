import * as ort from "onnxruntime-web";
import {
  TARGET_SAMPLE_RATE,
  VAD_HANGOVER_FRAMES,
  VAD_ONSET_FRAMES,
  VAD_PREROLL_FRAMES,
  VAD_SPEECH_THRESHOLD,
  VAD_STATE_TENSOR_SHAPE,
  VAD_WINDOW_SAMPLES,
} from "./constants";
import type { VoiceActivityEvent } from "./types";

const INT16_NEGATIVE_SCALE = 0x8000;
const INT16_POSITIVE_SCALE = 0x7fff;
const INT16_MIN = -32768;
const INT16_MAX = 32767;

const createInitialState = (): ort.Tensor =>
  new ort.Tensor(
    "float32",
    new Float32Array(VAD_STATE_TENSOR_SHAPE[0] * VAD_STATE_TENSOR_SHAPE[1] * VAD_STATE_TENSOR_SHAPE[2]),
    [...VAD_STATE_TENSOR_SHAPE],
  );

const floatToInt16 = (samples: Float32Array): Int16Array => {
  const result = new Int16Array(samples.length);
  for (let i = 0; i < samples.length; i++) {
    const sample = samples[i] ?? 0;
    result[i] = sample < 0
      ? Math.max(INT16_MIN, Math.round(sample * INT16_NEGATIVE_SCALE))
      : Math.min(INT16_MAX, Math.round(sample * INT16_POSITIVE_SCALE));
  }
  return result;
};

const int16ToFloat = (samples: Int16Array): Float32Array => {
  const result = new Float32Array(samples.length);
  for (let i = 0; i < samples.length; i++) result[i] = (samples[i] ?? 0) / INT16_NEGATIVE_SCALE;
  return result;
};

const configureOrtRuntime = (): void => {
  ort.env.wasm.numThreads = 1;
  ort.env.wasm.proxy = false;
  ort.env.wasm.wasmPaths = chrome.runtime.getURL("ort/");
};

export class VoiceActivityDetector {
  private session: ort.InferenceSession | null = null;
  private state: ort.Tensor = createInitialState();
  private readonly sampleRateTensor: ort.Tensor;
  private buffer = new Float32Array(0);
  private speechFrameCount = 0;
  private silenceFrameCount = 0;
  private inSpeech = false;
  private prerollFrames: Int16Array[] = [];

  constructor(private readonly modelUrl: string) {
    this.sampleRateTensor = new ort.Tensor("int64", BigInt64Array.from([BigInt(TARGET_SAMPLE_RATE)]), []);
  }

  init = async (): Promise<void> => {
    if (this.session) return;
    configureOrtRuntime();
    this.session = await ort.InferenceSession.create(this.modelUrl, { executionProviders: ["wasm"] });
    await this.runInference(new Float32Array(VAD_WINDOW_SAMPLES));
    this.state = createInitialState();
  };

  push = async (pcm: Int16Array, timestamp: number): Promise<VoiceActivityEvent[]> => {
    const incoming = int16ToFloat(pcm);
    const merged = new Float32Array(this.buffer.length + incoming.length);
    merged.set(this.buffer);
    merged.set(incoming, this.buffer.length);
    this.buffer = merged;

    const events: VoiceActivityEvent[] = [];
    let consumed = 0;
    while (this.buffer.length - consumed >= VAD_WINDOW_SAMPLES) {
      const window = this.buffer.subarray(consumed, consumed + VAD_WINDOW_SAMPLES);
      const speechProbability = await this.runInference(window);
      const isSpeech = speechProbability >= VAD_SPEECH_THRESHOLD;
      const windowAsInt16 = floatToInt16(window);

      if (this.inSpeech) this.handleSpeechFrame(events, isSpeech, windowAsInt16, timestamp);
      else this.handleSilenceFrame(events, isSpeech, windowAsInt16, timestamp);

      consumed += VAD_WINDOW_SAMPLES;
    }
    if (consumed > 0) this.buffer = this.buffer.slice(consumed);
    return events;
  };

  private handleSpeechFrame = (
    events: VoiceActivityEvent[],
    isSpeech: boolean,
    pcm: Int16Array,
    timestamp: number,
  ): void => {
    if (isSpeech) this.silenceFrameCount = 0;
    else this.silenceFrameCount += 1;
    events.push({ kind: "speech", t: timestamp, pcm });
    if (this.silenceFrameCount >= VAD_HANGOVER_FRAMES) {
      this.inSpeech = false;
      this.speechFrameCount = 0;
      this.silenceFrameCount = 0;
      events.push({ kind: "speech_end", t: timestamp });
    }
  };

  private handleSilenceFrame = (
    events: VoiceActivityEvent[],
    isSpeech: boolean,
    pcm: Int16Array,
    timestamp: number,
  ): void => {
    this.prerollFrames.push(pcm);
    if (this.prerollFrames.length > VAD_PREROLL_FRAMES) this.prerollFrames.shift();
    if (!isSpeech) {
      this.speechFrameCount = 0;
      return;
    }
    this.speechFrameCount += 1;
    if (this.speechFrameCount < VAD_ONSET_FRAMES) return;
    this.inSpeech = true;
    this.silenceFrameCount = 0;
    const preroll = this.prerollFrames;
    this.prerollFrames = [];
    events.push({ kind: "speech_start", t: timestamp, preroll });
    events.push({ kind: "speech", t: timestamp, pcm });
  };

  private runInference = async (window: Float32Array): Promise<number> => {
    if (!this.session) return 0;
    const input = new ort.Tensor("float32", window, [1, VAD_WINDOW_SAMPLES]);
    const outputs = await this.session.run({ input, sr: this.sampleRateTensor, state: this.state });
    if (outputs["stateN"]) this.state = outputs["stateN"] as ort.Tensor;
    const probability = (outputs["output"]?.data as Float32Array | undefined)?.[0] ?? 0;
    return probability;
  };
}
