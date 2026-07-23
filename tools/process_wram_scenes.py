#!/usr/bin/env python3
"""Process WRAM scene captures - fast version"""
import hashlib
from pathlib import Path
from PIL import Image

SRC = Path("/data/user/work/wram_scenes")
OUT = Path("/data/user/work/wram_scenes_analysis")
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
    img = Image.new('RGB', (256, 224), (0, 0, 0))
    px = img.load()
    for y in range(224):
        for x in range(256):
            idx = sb[y * 256 + x]
            if idx < len(colors):
                px[x, y] = colors[idx]
    img.save(out_path)

# Step 1: Load all scenes
print("Loading WRAM scenes...")
scenes = []
for sbf in sorted(SRC.glob("*_sb.bin")):
    label = sbf.name.replace("_sb.bin", "")
    cgf = SRC / f"{label}_cg.bin"
    wrf = SRC / f"{label}_wram.bin"
    if not cgf.exists() or not wrf.exists():
        continue
    wram = wrf.read_bytes()
    scenes.append({'label': label, 'wram': wram})
    print(f"  {label}: {len(wram)} bytes")
    sb_to_png(sbf, cgf, OUT / f"{label}.png")

print(f"\nTotal: {len(scenes)} scenes")

# Step 2: Cross-scene WRAM comparison
base = scenes[0]['wram']
print(f"\nWRAM comparison vs {scenes[0]['label']}:")
print(f"{'Scene':<25} {'Diff KB':>10} {'Diff %':>8}")
print("-" * 45)

for s in scenes:
    diff_bytes = sum(1 for i in range(len(base)) if base[i] != s['wram'][i])
    pct = diff_bytes / len(base) * 100
    print(f"{s['label']:<25} {diff_bytes/1024:>8.1f} {pct:>7.2f}%")

# Step 3: 1KB block analysis
print("\n1KB block volatility (changing in >8 scenes):")
block_counts = [0] * (len(base) // 1024)
for s in scenes[1:]:
    for blk in range(len(block_counts)):
        start = blk * 1024
        if any(base[i] != s['wram'][i] for i in range(start, start+1024)):
            block_counts[blk] += 1

for blk in range(len(block_counts)):
    if block_counts[blk] > 8:
        addr = blk * 1024
        print(f"  0x{addr:05X}: {block_counts[blk]}/{len(scenes)-1} scenes")

# Step 4: Contact sheet
cols, rows = 6, 3
tw, th = 128, 112
sheet = Image.new('RGB', (cols*tw+20, rows*th+20), (32,32,32))
for i, s in enumerate(scenes):
    if i >= cols*rows: break
    img = Image.open(OUT / f"{s['label']}.png")
    img.thumbnail((tw, th))
    sheet.paste(img, ((i%cols)*(tw+4)+4, (i//cols)*(th+4)+4))
sheet.save(OUT / "contact_sheet.png")
print(f"\nContact sheet saved")
