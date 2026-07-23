#!/usr/bin/env python3
"""Process town interior VRAM captures:
1. Convert all screenbuffers to PNGs for visual inspection
2. Compare VRAM dumps to identify interior vs exterior scenes
3. Generate tile sheets for unique scenes
"""
import os
import hashlib
from pathlib import Path
from PIL import Image

SRC = Path("/data/user/work/town_interior")
OUT = Path("/data/user/work/town_interior_png")
OUT.mkdir(exist_ok=True)

def read_cgram(data):
    """Read SNES CGRAM: 256 colors, 2 bytes each (BGR555)"""
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
    """Convert screenbuffer + CGRAM to PNG"""
    sb = Path(sb_path).read_bytes()
    cg = Path(cg_path).read_bytes()
    colors = read_cgram(cg)
    
    # SNES screenbuffer: 256x224, each byte = palette index
    width, height = 256, 224
    if len(sb) < width * height:
        print(f"  WARN: short screenbuffer {len(sb)} bytes")
        return None
    
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
    """Decode 8x8 4bpp tile, returns 64 pixel indices"""
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
    """Render a tilemap from VRAM"""
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
            tp = decode_4bpp_tile(vram, toff) if bpp == 4 else None
            if tp is None:
                continue
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
    """Get hash of VRAM data for deduplication"""
    return hashlib.md5(vram_data).hexdigest()[:12]

def vram_diff(vram1, vram2, start, end):
    """Count differing bytes in a VRAM region"""
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
        print(f"  SKIP {label}: missing files")
        continue
    out_png = OUT / f"{label}.png"
    img = sb_to_png(sbf, cgf, out_png)
    vram_data = vrf.read_bytes()
    scenes.append({
        'label': label,
        'sb_path': str(sbf),
        'cg_path': str(cgf),
        'vr_path': str(vrf),
        'vram': vram_data,
        'vhash': vram_hash(vram_data),
        'png': str(out_png)
    })
    print(f"  {label}: PNG saved, VRAM hash={vram_hash(vram_data)}")

print(f"\nTotal scenes: {len(scenes)}")

# === Step 2: Identify unique VRAM dumps ===
print("\n" + "=" * 60)
print("Step 2: Unique VRAM analysis")
print("=" * 60)

unique_hashes = {}
for s in scenes:
    h = s['vhash']
    if h not in unique_hashes:
        unique_hashes[h] = []
    unique_hashes[h].append(s['label'])

print(f"Unique VRAM hashes: {len(unique_hashes)}")
for h, labels in unique_hashes.items():
    print(f"  {h}: {', '.join(labels)}")

# === Step 3: Compare VRAM regions between first scene and others ===
print("\n" + "=" * 60)
print("Step 3: VRAM region comparison (vs first scene)")
print("=" * 60)

base = scenes[0]['vram']
regions = [
    ("0x0000-0x1FFF (BG1 map)", 0x0000, 0x2000),
    ("0x0800-0x0FFF (BG2 map)", 0x0800, 0x1000),
    ("0x1000-0x17FF (BG3 map)", 0x1000, 0x1800),
    ("0x2000-0x3FFF (empty?)", 0x2000, 0x4000),
    ("0x4000-0x5FFF (dyn char)", 0x4000, 0x6000),
    ("0x6000-0x7FFF (empty?)", 0x6000, 0x8000),
    ("0x8000-0xFFFF (static char)", 0x8000, 0x10000),
]

header = f"{'Scene':<30}"
for name, _, _ in regions:
    header += f" | {name[:18]:>18}"
print(header)
print("-" * len(header))

for s in scenes:
    row = f"{s['label']:<30}"
    for name, start, end in regions:
        diff, total = vram_diff(base, s['vram'], start, end)
        pct = (diff / total * 100) if total > 0 else 0
        row += f" | {pct:>17.1f}%"
    print(row)

# === Step 4: Render tilemaps for each unique scene ===
print("\n" + "=" * 60)
print("Step 4: Rendering tilemaps for unique scenes")
print("=" * 60)

rendered_dir = OUT / "rendered"
rendered_dir.mkdir(exist_ok=True)

for h, labels in unique_hashes.items():
    s = scenes[0]  # Use first scene with this hash
    for s2 in scenes:
        if s2['label'] == labels[0]:
            s = s2
            break
    
    vram = s['vram']
    cg = Path(s['cg_path']).read_bytes()
    colors = read_cgram(cg)
    
    # Render BG1 (map@0x0000, char@0x4000, 4bpp)
    bg1 = render_tilemap(vram, colors, 0x0000, 0x4000, bpp=4, tw=32, th=32, pal_base=0)
    bg1.save(rendered_dir / f"{s['label']}_bg1.png")
    
    # Render BG2 (map@0x0800, char@0x8000, 4bpp)
    bg2 = render_tilemap(vram, colors, 0x0800, 0x8000, bpp=4, tw=32, th=32, pal_base=0)
    bg2.save(rendered_dir / f"{s['label']}_bg2.png")
    
    # Render BG3 (map@0x1000, char@0x8000, 2bpp) - skip 2bpp for now, use 4bpp
    bg3 = render_tilemap(vram, colors, 0x1000, 0x8000, bpp=4, tw=32, th=32, pal_base=0)
    bg3.save(rendered_dir / f"{s['label']}_bg3.png")
    
    # Combined render (BG3 bottom, BG1 middle, BG2 top)
    combined = Image.new('RGB', (256, 256), (0, 0, 0))
    combined.paste(bg3, (0, 0))
    # Overlay BG1 where non-black
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
    
    print(f"  {s['label']}: BG1/BG2/BG3/combined rendered")

# === Step 5: Create contact sheet ===
print("\n" + "=" * 60)
print("Step 5: Creating contact sheet")
print("=" * 60)

# 4 columns x 6 rows for 22 scenes
cols, rows = 4, 6
thumb_w, thumb_h = 128, 112  # Half resolution
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
print(f"  Contact sheet saved: {OUT / 'contact_sheet.png'}")

print(f"\nDone! All output in {OUT}")
print(f"  - {len(scenes)} screen PNGs")
print(f"  - {len(unique_hashes)} unique VRAM renders (BG1/BG2/BG3/combined)")
print(f"  - 1 contact sheet")
