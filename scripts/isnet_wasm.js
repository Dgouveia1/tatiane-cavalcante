/*
  Roda um modelo ONNX (isnet-general-use, do rembg) em WebAssembly via onnxruntime-web.
  Usado pelo scripts/cutout.py quando o onnxruntime nativo do Python não carrega
  (Windows sem o Visual C++ Redistributable).

  uso: node scripts/isnet_wasm.js <modelo.onnx> <entrada.f32> <saida.f32> <tamanho>
       entrada = float32 [1,3,tamanho,tamanho] (raw, little-endian); saída = float32 raw do 1º output
  requer: npm i onnxruntime-web   (procura em scripts/node_modules ou no NODE_PATH)
*/
const fs = require('fs');
const path = require('path');

function requireOrt() {
  const candidates = [
    path.join(__dirname, 'node_modules', 'onnxruntime-web'),
    'onnxruntime-web',
  ];
  for (const c of candidates) {
    try { return require(c); } catch (_) { /* tenta o próximo */ }
  }
  throw new Error('onnxruntime-web não encontrado: rode "npm i onnxruntime-web" dentro de scripts/ (ou defina NODE_PATH)');
}

(async () => {
  const [modelPath, inPath, outPath, sizeArg] = process.argv.slice(2);
  if (!modelPath || !inPath || !outPath || !sizeArg) {
    console.error('uso: node isnet_wasm.js <modelo.onnx> <entrada.f32> <saida.f32> <tamanho>');
    process.exit(2);
  }
  const S = parseInt(sizeArg, 10);
  const ort = requireOrt();
  ort.env.wasm.numThreads = 1; // estável no Node; multi-thread exige flags extras

  const buf = fs.readFileSync(inPath);
  const input = new Float32Array(buf.buffer, buf.byteOffset, buf.byteLength / 4);
  const t0 = Date.now();
  const session = await ort.InferenceSession.create(modelPath, { executionProviders: ['wasm'] });
  console.error(`modelo carregado em ${((Date.now() - t0) / 1000).toFixed(1)}s`);

  const feeds = { [session.inputNames[0]]: new ort.Tensor('float32', input, [1, 3, S, S]) };
  const t1 = Date.now();
  const out = await session.run(feeds);
  console.error(`inferência em ${((Date.now() - t1) / 1000).toFixed(1)}s`);

  const first = out[session.outputNames[0]];
  const data = first.data; // Float32Array
  fs.writeFileSync(outPath, Buffer.from(data.buffer, data.byteOffset, data.byteLength));
  console.error(`saída ${first.dims.join('x')} -> ${outPath}`);
})().catch((err) => { console.error(err); process.exit(1); });
