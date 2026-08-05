# -*- coding: utf-8 -*-
"""生成 ComfyUI UI 格式工作流(带节点布局),供用户在界面上加载"""
import json, os

WF = r'C:\Users\24788\Desktop\ComfyUI\user\default\workflows\minimax_h3_ref2va_ui.json'

# 节点定义: id, type, pos, widgets_values, inputs(名称/类型/link), outputs(名称/类型/link ids)
NODES = [
    # 1 UNETLoader
    {"id": 1, "type": "UNETLoader", "pos": [0, 0], "widgets": ["minimax_h3_ref2va_pruned_int8_convrot.safetensors", "default"],
     "outputs": [("MODEL", "MODEL", [1])]},
    # 2 CLIPLoader
    {"id": 2, "type": "CLIPLoader", "pos": [0, 200], "widgets": ["qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "minimax"],
     "outputs": [("CLIP", "CLIP", [2, 13])]},
    # 3 VAELoader video
    {"id": 3, "type": "VAELoader", "pos": [0, 400], "widgets": ["minimax_h3_video_vae_fp16.safetensors"],
     "outputs": [("VAE", "VAE", [3, 11])]},
    # 4 VAELoader audio
    {"id": 4, "type": "VAELoader", "pos": [0, 600], "widgets": ["minimax_h3_audio_vae_fp32.safetensors"],
     "outputs": [("VAE", "VAE", [4, 15])]},
    # 5 LoadImage
    {"id": 5, "type": "LoadImage", "pos": [0, 800], "widgets": ["amiya_ref.png"],
     "outputs": [("IMAGE", "IMAGE", [5])]},
    # 6 MiniMaxH3ReferenceToVideo
    {"id": 6, "type": "MiniMaxH3ReferenceToVideo", "pos": [420, 0],
     "widgets": ["The masked boy from the second reference image kneeling and licking the feet of the rabbit-eared girl from the first reference image, the girl standing with a surprised embarrassed expression, Rhodes Island base background, anime style, cinematic lighting, with sound effects", 832, 480, 124, "match"],
     "inputs": [("clip", "CLIP", 2), ("vae", "VAE", 3), ("audio_vae", "VAE", 4),
                ("ref_images.ref_image_0", "IMAGE", 5), ("ref_images.ref_image_1", "IMAGE", 17)],
     "outputs": [("positive", "CONDITIONING", [6]), ("LATENT", "LATENT", [7])]},
    # 7 MiniMaxH3SigmaShift
    {"id": 7, "type": "MiniMaxH3SigmaShift", "pos": [420, 400], "widgets": [12.0, 3.0],
     "inputs": [("model", "MODEL", 1)],
     "outputs": [("MODEL", "MODEL", [9])]},
    # 8 CLIPTextEncode (negative)
    {"id": 8, "type": "CLIPTextEncode", "pos": [420, 600], "widgets": [""],
     "inputs": [("clip", "CLIP", 13)],
     "outputs": [("CONDITIONING", "CONDITIONING", [8])]},
    # 9 KSampler
    {"id": 9, "type": "KSampler", "pos": [900, 0],
     "widgets": [42, "randomize", 20, 1.0, "euler", "simple", 1.0],
     "inputs": [("model", "MODEL", 9), ("positive", "CONDITIONING", 6), ("negative", "CONDITIONING", 8), ("latent_image", "LATENT", 7)],
     "outputs": [("LATENT", "LATENT", [10, 14])]},
    # 10 VAEDecode
    {"id": 10, "type": "VAEDecode", "pos": [1300, 0],
     "inputs": [("samples", "LATENT", 10), ("vae", "VAE", 11)],
     "outputs": [("IMAGE", "IMAGE", [12])]},
    # 11 SaveAnimatedWEBP
    {"id": 11, "type": "SaveAnimatedWEBP", "pos": [1700, 0],
     "widgets": ["h3_test", 24.0, False, 90, "default"],
     "inputs": [("images", "IMAGE", 12)],
     "outputs": []},
    # 12 VAEDecodeAudio(从同一 latent 解码音频流)
    {"id": 12, "type": "VAEDecodeAudio", "pos": [1300, 300],
     "widgets": [],
     "inputs": [("samples", "LATENT", 14), ("vae", "VAE", 15)],
     "outputs": [("AUDIO", "AUDIO", [16])]},
    # 13 SaveAudio
    {"id": 13, "type": "SaveAudio", "pos": [1700, 300],
     "widgets": ["h3_audio"],
     "inputs": [("audio", "AUDIO", 16)],
     "outputs": []},
    # 14 LoadImage 新角色(参考图2)
    {"id": 14, "type": "LoadImage", "pos": [0, 1000], "widgets": ["newchar_ref.png"],
     "outputs": [("IMAGE", "IMAGE", [17])]},
]

# links: [id, from_node, from_slot, to_node, to_slot, type]
LINKS = [
    [1, 1, 0, 7, 0, "MODEL"],
    [2, 2, 0, 6, 0, "CLIP"],
    [3, 3, 0, 6, 0, "VAE"],
    [4, 4, 0, 6, 0, "VAE"],
    [5, 5, 0, 6, 0, "IMAGE"],
    [6, 6, 0, 9, 1, "CONDITIONING"],
    [7, 6, 1, 9, 3, "LATENT"],
    [8, 8, 0, 9, 2, "CONDITIONING"],
    [9, 7, 0, 9, 0, "MODEL"],
    [10, 9, 0, 10, 0, "LATENT"],
    [11, 3, 0, 10, 1, "VAE"],
    [12, 10, 0, 11, 0, "IMAGE"],
    [13, 2, 0, 8, 0, "CLIP"],
    [14, 9, 0, 12, 0, "LATENT"],
    [15, 4, 0, 12, 1, "VAE"],
    [16, 12, 0, 13, 0, "AUDIO"],
    [17, 14, 0, 6, 4, "IMAGE"],
]

nodes_out = []
for n in NODES:
    node = {
        "id": n["id"], "type": n["type"], "pos": n["pos"],
        "size": [300, 120], "flags": {}, "order": n["id"], "mode": 0,
        "inputs": [{"name": i[0], "type": i[1], "link": i[2],
                    **({"label": i[0].split('.')[-1], "shape": 7} if '.' in i[0] else {})}
                   for i in n.get("inputs", [])],
        "outputs": [{"name": o[0], "type": o[1], "links": o[2], "slot_index": si} for si, o in enumerate(n.get("outputs", []))],
        "properties": {"Node name for S&R": n["type"]},
        "widgets_values": n.get("widgets", []),
    }
    nodes_out.append(node)

wf = {
    "last_node_id": 14, "last_link_id": 17,
    "nodes": nodes_out, "links": LINKS,
    "groups": [], "config": {}, "extra": {}, "version": 0.4,
}
os.makedirs(os.path.dirname(WF), exist_ok=True)
with open(WF, 'w', encoding='utf-8') as f:
    json.dump(wf, f, ensure_ascii=False, indent=1)
print('UI工作流已生成:', WF)
print('节点数:', len(nodes_out), '| 连线数:', len(LINKS))
