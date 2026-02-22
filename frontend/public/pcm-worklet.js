class PCMProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;
    const channel = input[0];
    // Copy to avoid transferring the underlying buffer repeatedly.
    const copy = new Float32Array(channel); 
    this.port.postMessage(copy, [copy.buffer]);
    return true;
  }
}
registerProcessor('pcm-processor', PCMProcessor);
