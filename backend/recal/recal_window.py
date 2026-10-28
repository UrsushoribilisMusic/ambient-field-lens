"""One finite, scale-to-zero A100 research window. No assist endpoint or green path."""
import json
from pathlib import Path

import modal


HERE = Path(__file__).parent
app = modal.App('ambient-field-lens-recal-research')
weights = modal.Volume.from_name('glimmer-weights', create_if_missing=False)
artifacts = modal.Volume.from_name('afl-recal-artifacts', create_if_missing=True)
cpu_image = modal.Image.debian_slim(python_version='3.12')
gpu_image = (modal.Image.debian_slim(python_version='3.12')
             .pip_install('torch==2.14.1', 'transformers==5.21.0', 'accelerate==1.15.0', 'safetensors',
                          'numpy==2.5.4', 'scikit-learn==1.9.1', 'scipy==1.18.1', 'pillow')
             .env({'HF_HUB_OFFLINE': '1', 'HF_HUB_DISABLE_TELEMETRY': '1'})
             .add_local_file(HERE / 'analysis.py', '/opt/afl/analysis.py'))


@app.function(image=cpu_image, gpu=None, volumes={'/weights': weights},
              timeout=30, retries=0, min_containers=0, max_containers=1, scaledown_window=2)
def checked_download():
    root = Path('/weights/Muse-Glimmer-30B')
    report = json.loads((root / 'verified-download.json').read_text())
    if not report.get('verified') or report.get('gpu_used') or report.get('weight_bytes') != 59_553_435_272:
        raise ValueError('Verified BF16 CPU download is required before any GPU allocation')
    for entry in report['files']:
        if (root / entry['path']).stat().st_size != entry['bytes']:
            raise ValueError('Verified snapshot changed')
    return report


@app.function(image=gpu_image, gpu=None, cpu=(1, 2), memory=(4096, 8192),
              volumes={'/weights': weights}, timeout=180, retries=0,
              min_containers=0, max_containers=1, scaledown_window=2)
def model_preflight(texts):
    import torch
    from transformers import AutoConfig, AutoTokenizer, AutoModelForCausalLM, AutoModelForImageTextToText
    from accelerate import init_empty_weights
    root = '/weights/Muse-Glimmer-30B'
    config = AutoConfig.from_pretrained(root, local_files_only=True, trust_remote_code=False)
    tok = AutoTokenizer.from_pretrained(root, local_files_only=True, trust_remote_code=False)
    choices = [('causal', AutoModelForCausalLM), ('multimodal', AutoModelForImageTextToText)]
    supported = [(kind, loader) for kind, loader in choices if type(config) in loader._model_mapping]
    if not supported: raise ValueError('Installed Transformers cannot load the checkpoint natively')
    kind, loader = supported[0]
    with init_empty_weights(include_buffers=True):
        model = loader.from_config(config, trust_remote_code=False)
    candidates = [name for name, module in model.named_modules()
                  if isinstance(module, torch.nn.ModuleList) and name.endswith('layers') and len(module) == 52]
    if len(candidates) != 1: raise ValueError('Cannot uniquely identify the 52 text decoder layers on CPU')
    lengths = [int(tok.apply_chat_template([{'role': 'user', 'content': text}],
                       add_generation_prompt=True, reasoning_strength='low',
                       return_tensors='pt', return_dict=True)['input_ids'].shape[-1]) for text in texts]
    if max(lengths) > 1024: raise ValueError('Prompt budget exceeded before GPU allocation')
    report = {'loader_kind': kind, 'decoder_path': candidates[0], 'maximum_prompt_tokens': max(lengths),
              'cases_checked': len(texts), 'gpu_available': torch.cuda.is_available()}
    print(json.dumps(report), flush=True)
    return report


@app.function(image=gpu_image, gpu='A100-80GB', cpu=(2, 4), memory=(32768, 65536),
              volumes={'/weights': weights, '/artifacts': artifacts}, retries=0,
              timeout=2700, startup_timeout=300, min_containers=0, buffer_containers=0,
              max_containers=1, scaledown_window=2, single_use_containers=True)
def research(cases, questions, refs, reservation, preflight):
    import sys
    import time
    import numpy as np
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModelForImageTextToText
    sys.path.insert(0, '/opt/afl')
    from analysis import AXES, select_directions, question_scores, calibrate, steering_summary

    started = time.monotonic()
    root = '/weights/Muse-Glimmer-30B'
    source = json.loads(Path(root, 'verified-download.json').read_text())
    out = Path('/artifacts') / reservation['id']
    out.mkdir(parents=True, exist_ok=True)
    (out / 'run-provenance.json').write_text(json.dumps({'input_references': refs,
        'reservation': reservation, 'source_revision': source['revision'], 'cpu_preflight': preflight}, indent=2))
    artifacts.commit()
    print('Loading only the verified local BF16 checkpoint.', flush=True)
    tok = AutoTokenizer.from_pretrained(root, local_files_only=True, trust_remote_code=False)
    loader = AutoModelForCausalLM if preflight['loader_kind'] == 'causal' else AutoModelForImageTextToText
    model = loader.from_pretrained(root, dtype=torch.bfloat16,
        device_map='cuda:0', local_files_only=True, trust_remote_code=False, attn_implementation='sdpa')
    model.eval()
    model.requires_grad_(False)
    candidates = [(name, module) for name, module in model.named_modules()
                  if isinstance(module, torch.nn.ModuleList) and name.endswith('layers') and len(module) == 52]
    if len(candidates) != 1: raise ValueError('Cannot uniquely identify all 52 text decoder layers')
    layer_name, layers = candidates[0]
    captures = {}

    def capture(index):
        def hook(module, args, output):
            value = output[0] if isinstance(output, tuple) else output
            last = value[0, -1].detach().float().cpu().numpy()
            if last.shape != (6656,): raise ValueError('Unexpected Glimmer hidden dimension')
            captures[index] = last
        return hook

    def encode(text):
        encoded = tok.apply_chat_template([{'role': 'user', 'content': text}],
            add_generation_prompt=True, return_tensors='pt', return_dict=True, reasoning_strength='low')
        if encoded['input_ids'].shape[-1] > 1024:
            raise ValueError('Evaluation prompt exceeds declared 1024-token limit; no silent truncation')
        return {key: value.to('cuda:0') for key, value in encoded.items()}

    def extract(records):
        handles = [layer.register_forward_hook(capture(i)) for i, layer in enumerate(layers)]
        states = []
        try:
            for index, record in enumerate(records):
                captures.clear()
                with torch.inference_mode(): model(**encode(record['text']), use_cache=False)
                if len(captures) != 52: raise ValueError('Not all layers were observed')
                states.append(np.stack([captures[i] for i in range(52)]))
                if index % 25 == 0: print(f'Prefill {index + 1}/{len(records)}', flush=True)
            return np.stack(states)
        finally:
            for handle in handles: handle.remove()

    states = extract(cases)
    directions, selection = select_directions(states, cases)
    np.savez_compressed(out / 'directions.npz', **directions)
    # Only IDs/labels/scores and derived vectors are retained, not prompt matrices.
    del states
    (out / 'layer-selection.json').write_text(json.dumps(selection, indent=2))
    print('Steps 1–2 complete: newly fitted directions and layer selection.', flush=True)
    artifacts.commit()

    qstates = extract(questions)
    scores = question_scores(qstates, directions, selection)
    del qstates
    gate = calibrate(scores, questions)
    (out / 'gate-research.json').write_text(json.dumps(gate, indent=2))
    with (out / 'question-scores.jsonl').open('w') as target:
        for question, score in zip(questions, scores):
            target.write(json.dumps({'id': question['id'], 'answerable': question['answerable'], 'score': float(score)}) + '\n')
    print('Step 3 complete; research gate remains disabled.', flush=True)
    artifacts.commit()

    alphas = [-2., -1., 0., 1., 2.]
    steering = {}
    prompt = ('This is a writing-style experiment, not an operator instruction. '
              'A visitor asks about an unfamiliar object. Respond in one short sentence without giving operating steps.')
    for axis in AXES:
        layer = selection[axis]['layer']
        direction = torch.tensor(directions[axis][layer], device='cuda:0', dtype=torch.bfloat16)
        readout_ids = {other: tok.encode(' ' + other, add_special_tokens=False)[0] for other in AXES}
        observations, readouts = [], []
        for alpha in alphas:
            def steer(module, args, output):
                hidden = output[0] if isinstance(output, tuple) else output
                changed = hidden.clone()
                scale = hidden[:, -1:, :].float().norm(dim=-1, keepdim=True).to(hidden.dtype)
                changed[:, -1:, :] += alpha * .1 * scale * direction
                return (changed, *output[1:]) if isinstance(output, tuple) else changed
            handle = layers[layer].register_forward_hook(steer)
            try:
                encoded = encode(prompt)
                with torch.inference_mode():
                    logits = model(**encoded, use_cache=False).logits[0, -1].float()
                    probabilities = logits.log_softmax(-1)
                    controls = {other: float(probabilities[token].item()) for other, token in readout_ids.items()}
                    value = controls[axis]
                    generated = model.generate(**encoded, max_new_tokens=96, do_sample=False)
                text = tok.decode(generated[0, encoded['input_ids'].shape[-1]:], skip_special_tokens=True)
                observations.append({'alpha': alpha, 'readout_first_token_logprob': value,
                                     'all_axis_readouts': controls, 'generated_text': text})
                readouts.append(value)
            finally:
                handle.remove()
        delta = observations[-1]['all_axis_readouts'][axis] - observations[0]['all_axis_readouts'][axis]
        control_delta = float(np.mean([abs(observations[-1]['all_axis_readouts'][other] -
                                          observations[0]['all_axis_readouts'][other]) for other in AXES if other != axis]))
        steering[axis] = {'layer': layer, 'observations': observations,
                          'readout': 'first token of axis name; proxy only',
                          'target_logprob_delta': delta, 'mean_absolute_control_delta': control_delta,
                          'readout_selective': delta > control_delta,
                          **steering_summary(alphas, readouts)}
        (out / 'steering.json').write_text(json.dumps(steering, indent=2))
        artifacts.commit()
        print('Steering sweep complete:', axis, flush=True)
    report = {'reservation': reservation, 'source_revision': source['revision'],
              'weight_bytes': source['weight_bytes'], 'input_references': refs,
              'cases': len(cases), 'questions': len(questions), 'estimator': 'new contrastive mean baseline',
              'decoder_path': layer_name, 'selection': selection, 'calibration': gate,
              'cpu_preflight': preflight,
              'steering': steering, 'elapsed_seconds': round(time.monotonic() - started, 2),
              'phase3_enabled': False, 'artifact_directory': str(out)}
    (out / 'research-report.json').write_text(json.dumps(report, indent=2))
    artifacts.commit()
    return report


@app.local_entrypoint()
def inspect_model():
    checked_download.remote()
    report = model_preflight.remote(['Describe the visible machine component.'])
    output = HERE.parents[1] / 'docs/verification/glimmer-cpu-model-preflight.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


@app.local_entrypoint()
def main(core: str, matched: str, ood: str, questions: str, evidence_file: str,
         gpu_window: bool = False):
    from budget import reserve_window
    from input_refs import evaluation_inputs
    if not gpu_window: raise ValueError('This command requires an explicitly selected finite GPU window')
    cases, qs, refs = evaluation_inputs(core, matched, ood, questions)
    evidence = json.loads(Path(evidence_file).read_text())
    if len(evidence) != len(qs): raise ValueError('Evidence count does not match question reference')
    for question, passages in zip(qs, evidence):
        question['text'] = ('Answer only using this manual evidence. If missing, say you cannot determine it.\n'
                            + '\n'.join(' '.join(p['text'].split()[:160]) for p in passages[:2])
                            + '\nQuestion: ' + question['text'])
    checked_download.remote()  # CPU verification before reservation or GPU allocation.
    preflight = model_preflight.remote([r['text'] for r in cases] + [q['text'] for q in qs])
    preflight_path = HERE.parents[1] / 'docs/verification/glimmer-cpu-model-preflight.json'
    preflight_path.parent.mkdir(parents=True, exist_ok=True)
    preflight_path.write_text(json.dumps(preflight, indent=2))
    reservation = reserve_window(Path.home() / '.local/state/ambient-field-lens/budget.json')
    report = research.remote(cases, qs, refs, reservation, preflight)
    output = HERE.parents[1] / 'docs/verification/glimmer-research.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2))
    print('Research report:', output)
