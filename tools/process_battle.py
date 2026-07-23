#!/usr/bin/env python3
"""Process battle VRAM captures:
1. Convert all screenbuffers to PNGs
2. Compare VRAM between world map and battle scenes
3. Render battle tilemaps and sprite data
"""
import hashlib
from pathlib import Path
from PIL import Image

SRC = Path("/data/user/work/battle_vram")
OUT = Path("/data/user/work/battle_vram_png")
OUT.mkdir(exist_ok=True)

def read_cgram(data):
    colors = []
    for i in range(256):
        if i * 2 + 1 < len(data):
            lo = data[i * 2]
            hi = data[i * 2 + 1]
            val = lo | (hi << 8)
            r = (val & 0x1F) << 3
            g = ((val >> 5) & 0x1F) << 3
            b = ((val >> 10) & 0x1F) << 3
            colors.append((r, g, b))
        else:
            colors.append((0, 0, 0))
    return colors

def sb_to_png(sb_path, cg_path, out_path):
    sb = Path(sb_path).read_bytes()
    cg = Path(cg_path).read_bytes()
    colors = read_cgram(cg)
    width, height = 256, 224
    img = Image.new('RGB', (width, height), (0, 0, 0))
    px = img.load()
    for y in range(height):
        for x in range(width):
            idx = sb[y * width + x]
            if idx < len(colors):
                px[x, y] = colors[idx]
            else:
                px[x, y] = (255, 0, 255)
    img.save(out_path)
    return img

def decode_4bpp_tile(vram, offset):
    pixels = []
    for row in range(8):
        base = offset + row * 2
        if base + 17 >= len(vram):
            pixels.extend([0] * 8)
            continue
        bp0 = vram[base]
        bp1 = vram[base + 1]
        bp2 = vram[base + 16]
        bp3 = vram[base + 17]
        for col in range(8):
            bit = 7 - col
            pixel = ((bp0 >> bit) & 1)
            pixel |= ((bp1 >> bit) & 1) << 1
            pixel |= ((bp2 >> bit) & 1) << 2
            pixel |= ((bp3 >> bit) & 1) << 3
            pixels.append(pixel)
    return pixels

def render_tilemap(vram, colors, map_addr, char_addr, bpp=4, tw=32, th=32, pal_base=0):
    img = Image.new('RGB', (tw * 8, th * 8), (0, 0, 0))
    px = img.load()
    bpt = 32 if bpp == 4 else 16
    for ty in range(th):
        for tx in range(tw):
            idx = map_addr + (ty * tw + tx) * 2
            if idx + 1 >= len(vram):
                continue
            entry = vram[idx] | (vram[idx + 1] << 8)
            tile = entry & 0x3FF
            pal = (entry >> 10) & 7
            hf = (entry >> 14) & 1
            vf = (entry >> 15) & 1
            toff = char_addr + tile * bpt
            if toff + bpt > len(vram):
                continue
            tp = decode_4bpp_tile(vram, toff)
            for r in range(8):
                for c in range(8):
                    sr = (7 - r) if vf else r
                    sc = (7 - c) if hf else c
                    pval = tp[sr * 8 + sc]
                    if pval > 0:
                        ci = pal_base + pal * 16 + pval
                        if ci < len(colors):
                            px[tx * 8 + c, ty * 8 + r] = colors[ci]
    return img

def vram_hash(vram_data):
    return hashlib.md5(vram_data).hexdigest()[:12]

def vram_diff(vram1, vram2, start, end):
    diff = 0
    total = end - start
    for i in range(start, min(end, len(vram1), len(vram2))):
        if vram1[i] != vram2[i]:
            diff += 1
    return diff, total

# === Step 1: Convert all screenbuffers to PNG ===
print("=" * 60)
print("Step 1: Converting screenbuffers to PNG")
print("=" * 60)

sb_files = sorted(SRC.glob("*_sb.bin"))
scenes = []
for sbf in sb_files:
    label = sbf.name.replace("_sb.bin", "")
    cgf = SRC / f"{label}_cg.bin"
    vrf = SRC / f"{label}_vram.bin"
    if not cgf.exists() or not vrf.exists():
        continue
    out_png = OUT / f"{label}.png"
    img = sb_to_png(sbf, cgf, out_png)
    vram_data = vrf.read_bytes()
    scenes.append({
        'label': label,
        'vram': vram_data,
        'vhash': vram_hash(vram_data),
        'png': str(out_png),
        'cg_path': str(cgf),
        'vr_path': str(vrf)
    })
    print(f"  {label}: hash={vram_hash(vram_data)}")

# === Step 2: VRAM region comparison ===
print("\n" + "=" * 60)
print("Step 2: VRAM comparison (worldmap vs battle)")
print("=" * 60)

# Use first worldmap capture as baseline
base = scenes[1]['vram'] if len(scenes) > 1 else scenes[0]['vram']
base_label = scenes[1]['label'] if len(scenes) > 1 else scenes[0]['label']

regions = [
    ("BG1 map 0x0-0x7FF", 0x0000, 0x0800),
    ("BG2 map 0x800-0xFFF", 0x0800, 0x1000),
    ("BG3 map 0x1000-0x17FF", 0x1000, 0x1800),
    ("0x2000-0x3FFF", 0x2000, 0x4000),
    ("Dyn char 0x4000-0x5FFF", 0x4000, 0x6000),
    ("0x6000-0x7FFF", 0x6000, 0x8000),
    ("Static char 0x8000+", 0x8000, 0x10000),
]

print(f"Baseline: {base_label}\n")
header = f"{'Scene':<30}"
for name, _, _ in regions:
    header += f" | {name[:20]:>20}"
print(header)
print("-" * len(header))

for s in scenes:
    row = f"{s['label']:<30}"
    for name, start, end in regions:
        diff, total = vram_diff(base, s['vram'], start, end)
        pct = (diff / total * 100) if total > 0 else 0
        row += f" | {pct:>19.1f}%"
    print(row)

# === Step 3: Render tilemaps for battle and worldmap scenes ===
print("\n" + "=" * 60)
print("Step 3: Rendering tilemaps")
print("=" * 60)

rendered_dir = OUT / "rendered"
rendered_dir.mkdir(exist_ok=True)

# Select key scenes: first worldmap, first battle, last battle
key_scenes = []
for s in scenes:
    if 'encounter' in s['label'] or s['label'] in ['wm_01_worldmap_start', 'wm_10_explore_n3', 'wm_15_explore_final', 'wm_17_end']:
        key_scenes.append(s)

for s in key_scenes:
    vram = s['vram']
    cg = Path(s['cg_path']).read_bytes()
    colors = read_cgram(cg)

    # Render with standard layout
    bg1 = render_tilemap(vram, colors, 0x0000, 0x4000, bpp=4, tw=32, th=32, pal_base=0)
    bg1.save(rendered_dir / f"{s['label']}_bg1.png")
    bg2 = render_tilemap(vram, colors, 0x0800, 0x8000, bpp=4, tw=32, th=32, pal_base=0)
    bg2.save(rendered_dir / f"{s['label']}_bg2.png")
    bg3 = render_tilemap(vram, colors, 0x1000, 0x8000, bpp=4, tw=32, th=32, pal_base=0)
    bg3.save(rendered_dir / f"{s['label']}_bg3.png")

    # Combined
    combined = Image.new('RGB', (256, 256), (0, 0, 0))
    combined.paste(bg3, (0, 0))
    bg1_px = bg1.load()
    comb_px = combined.load()
    for y in range(256):
        for x in range(256):
            if bg1_px[x, y] != (0, 0, 0):
                comb_px[x, y] = bg1_px[x, y]
    bg2_px = bg2.load()
    for y in range(256):
        for x in range(256):
            if bg2_px[x, y] != (0, 0, 0):
                comb_px[x, y] = bg2_px[x, y]
    combined.save(rendered_dir / f"{s['label']}_combined.png")

    print(f"  {s['label']}: rendered")

# === Step 4: Create VRAM tile sheets for battle scenes ===
print("\n" + "=" * 60)
print("Step 4: Creating VRAM tile sheets for battle scenes")
print("=" * 60)

tilesheet_dir = OUT / "tilesheets"
tilesheet_dir.mkdir(exist_ok=True)

for s in key_scenes:
    vram = s['vram']
    cg = Path(s['cg_path']).read_bytes()
    colors = read_cgram(cg)

    # Dynamic char region (0x4000-0x5FFF) = 8KB = 256 tiles at 4bpp
    img_dyn = Image.new('RGB', (16 * 8, 16 * 8), (0, 0, 0))
    px_dyn = img_dyn.load()
    for tile_idx in range(256):
        toff = 0x4000 + tile_idx * 32
        if toff + 32 > len(vram):
            continue
        tp = decode_4bpp_tile(vram, toff)
        tx = (tile_idx % 16) * 8
        ty = (tile_idx // 16) * 8
        for r in range(8):
            for c in range(8):
                pval = tp[r * 8 + c]
                if pval > 0 and pval < len(colors):
                    px_dyn[tx + c, ty + r] = colors[pval]
    img_dyn.save(tilesheet_dir / f"{s['label']}_dyn_tiles.png")

    # Static char region (0x8000-0xFFFF) = 32KB = 1024 tiles at 4bpp
    # Show first 512 tiles (16KB)
    img_static = Image.new('RGB', (32 * 8, 16 * 8), (0, 0, 0))
    px_static = img_static.load()
    for tile_idx in range(512):
        toff = 0x8000 + tile_idx * 32
        if toff + 32 > len(vram):
            continue
        tp = decode_4bpp_tile(vram, toff)
        tx = (tile_idx % 32) * 8
        ty = (tile_idx // 32) * 8
        for r in range(8):
            for c in range(8):
                pval = tp[r * 8 + c]
                if pval > 0 and pval < len(colors):
                    px_static[tx + c, ty + r] = colors[pval]
    img_static.save(tilesheet_dir / f"{s['label']}_static_tiles.png")

    print(f"  {s['label']}: tile sheets created")

# === Step 5: Contact sheet ===
print("\n" + "=" * 60)
print("Step 5: Contact sheet")
print("=" * 60)

cols, rows = 6, 4
thumb_w, thumb_h = 128, 112
sheet = Image.new('RGB', (cols * thumb_w + 20, rows * thumb_h + 20), (32, 32, 32))
for i, s in enumerate(scenes):
    if i >= cols * rows:
        break
    img = Image.open(s['png'])
    img.thumbnail((thumb_w, thumb_h))
    cx = (i % cols) * (thumb_w + 4) + 4
    cy = (i // cols) * (thumb_h + 4) + 4
    sheet.paste(img, (cx, cy))
sheet.save(OUT / "contact_sheet.png")

print(f"  Contact sheet saved")
print(f"\nDone! Output in {OUT}")
print(f"  - {len(scenes)} screen PNGs")
print(f"  - {len(key_scenes)} rendered tilemaps (BG1/BG2/BG3/combined)")
print(f"  - {len(key_scenes) * 2} tile sheets (dynamic + static)")
print(f"  - 1 contact sheet")
