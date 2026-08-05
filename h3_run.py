import json, urllib.request, sys, time

# H3 Ref2VA 工作流(API 提交)
prompt = {
    "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "minimax_h3_ref2va_pruned_int8_convrot.safetensors", "weight_dtype": "default"}},
    "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "type": "minimax"}},
    "3": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}},
    "4": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
    "5": {"class_type": "LoadImage", "inputs": {"image": "test_ref.png"}},
    "6": {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": {
        "clip": ["2", 0], "vae": ["3", 0], "audio_vae": ["4", 0],
        "prompt": "A red tractor driving across a green field, cinematic lighting, realistic",
        "width": 832, "height": 480, "length": 124,
        "ref_image_size": "match", "ref_images": [["5", 0]]}},
    "7": {"class_type": "MiniMaxH3SigmaShift", "inputs": {"model": ["1", 0], "shift_video": 12.0, "shift_audio": 3.0}},
    "8": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": ""}},
    "9": {"class_type": "KSampler", "inputs": {
        "model": ["7", 0], "seed": 42, "steps": 20, "cfg": 1.0,
        "sampler_name": "euler", "scheduler": "simple",
        "positive": ["6", 0], "negative": ["8", 0], "latent_image": ["6", 1], "denoise": 1.0}},
    "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
    "11": {"class_type": "SaveAnimatedWEBP", "inputs": {"images": ["10", 0], "filename_prefix": "h3_test", "fps": 24, "lossless": False, "quality": 90, "method": "default"}}
}

req = urllib.request.Request(
    'http://127.0.0.1:8188/prompt',
    data=json.dumps({'prompt': prompt}).encode('utf-8'),
    headers={'Content-Type': 'application/json'})
try:
    resp = json.load(urllib.request.urlopen(req, timeout=60))
    print('提交成功! prompt_id:', resp.get('prompt_id', resp))
except Exception as e:
    print('提交失败:', str(e)[:500])
    try:
        print('详情:', e.read().decode()[:500])
    except Exception:
        pass
