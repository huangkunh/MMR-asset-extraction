#!/usr/bin/env python3
"""Process menu system VRAM captures:
1. Convert screenbuffers to PNGs
2. Compare VRAM between menu states
3. Analyze CGRAM animation frames for palette cycling
"""
import hashlib
from pathlib import Path
from PIL import Image

SRC = Path("/data/user/work/menu_system")
OUT = Path("/data/user/work/menu_system_png")
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

def vram_hash(data):
    return hashlib.md5(data).hexdigest()[:12]

def vram_diff(v1, v2, start, end):
    diff = 0
    total = end - start
    for i in range(start, min(end, len(v1), len(v2))):
        if v1[i] != v2[i]:
            diff += 1
    return diff, total

# === Step 1: Convert screenbuffers to PNG ===
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
    sb_to_png(sbf, cgf, out_png)
    vram_data = vrf.read_bytes()
    scenes.append({
        'label': label,
        'vram': vram_data,
        'vhash': vram_hash(vram_data),
        'png': str(out_png),
        'cg_path': str(cgf)
    })
    print(f"  {label}: hash={vram_hash(vram_data)}")

# === Step 2: VRAM comparison between menu states ===
print("\n" + "=" * 60)
print("Step 2: VRAM comparison (vs first menu state)")
print("=" * 60)

if scenes:
    base = scenes[0]['vram']
    regions = [
        ("BG1 map", 0x0000, 0x0800),
        ("BG2 map", 0x0800, 0x1000),
        ("BG3 map", 0x1000, 0x1800),
        ("Dyn char", 0x4000, 0x6000),
        ("Static char", 0x8000, 0x10000),
    ]

    for s in scenes:
        diffs = []
        for name, start, end in regions:
            diff, total = vram_diff(base, s['vram'], start, end)
            pct = (diff / total * 100) if total > 0 else 0
            diffs.append(f"{name}={pct:.1f}%")
        print(f"  {s['label']:<30} {' '.join(diffs)}")

# === Step 3: CGRAM animation analysis ===
print("\n" + "=" * 60)
print("Step 3: CGRAM animation analysis")
print("=" * 60)

cgram_files = sorted(SRC.glob("cgram_anim_*.bin"))
if cgram_files:
    cgram_data_list = []
    for cf in cgram_files:
        data = cf.read_bytes()
        cgram_data_list.append((cf.name, data))

    # Find which color entries change across all frames
    if len(cgram_data_list) > 1:
        first = cgram_data_list[0][1]
        changed_colors = set()
        for name, data in cgram_data_list[1:]:
            for i in range(0, min(len(first), len(data)), 2):
                if i + 1 < len(data) and i + 1 < len(first):
                    val1 = first[i] | (first[i+1] << 8)
                    val2 = data[i] | (data[i+1] << 8)
                    if val1 != val2:
                        changed_colors.add(i // 2)

        print(f"  CGRAM animation frames: {len(cgram_data_list)}")
        print(f"  Changed color entries: {len(changed_colors)}")
        if changed_colors:
            sorted_colors = sorted(changed_colors)
            print(f"  Color indices: {sorted_colors[:30]}...")
            # Group consecutive colors
            groups = []
            start = sorted_colors[0]
            prev = start
            for c in sorted_colors[1:]:
                if c != prev + 1:
                    groups.append((start, prev))
                    start = c
                prev = c
            groups.append((start, prev))
            print(f"  Color ranges: {groups[:10]}")

        # Create CGRAM animation visualization
        anim_img = Image.new('RGB', (len(cgram_data_list) * 4, 256), (0, 0, 0))
        px = anim_img.load()
        for frame_idx, (name, data) in enumerate(cgram_data_list):
            colors = read_cgram(data)
            for ci, color in enumerate(colors):
                for px_x in range(4):
                    px[frame_idx * 4 + px_x, ci] = color
        anim_img.save(OUT / "cgram_animation.png")
        print(f"  CGRAM animation visualization saved")

# === Step 4: Contact sheet ===
print("\n" + "=" * 60)
print("Step 4: Contact sheet")
print("=" * 60)

cols, rows = 6, 5
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
print(f"  - 1 CGRAM animation visualization")
print(f"  - 1 contact sheet")
