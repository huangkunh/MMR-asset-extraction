#!/usr/bin/env python3
"""Comprehensive cross-session VRAM analysis:
1. Load all VRAM dumps from all extraction sessions
2. Deduplicate by hash to find unique VRAM states
3. Compare tile data across all unique dumps
4. Create master tile sheets showing all unique tiles
5. Generate a summary report
"""
import hashlib
import json
from pathlib import Path
from PIL import Image

REPO = Path("/workspace/MMR-asset-extraction")
OUT = Path("/data/user/work/vram_catalog")
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

def tile_hash(vram, offset):
    """Hash a single 32-byte tile"""
    if offset + 32 > len(vram):
        return "00000000"
    return hashlib.md5(vram[offset:offset+32]).hexdigest()[:8]

# === Step 1: Load all VRAM dumps ===
print("=" * 60)
print("Step 1: Loading all VRAM dumps")
print("=" * 60)

all_dumps = []
# Search all directories for *_vram.bin files
for vram_file in sorted(REPO.rglob("*_vram.bin")):
    rel_path = vram_file.relative_to(REPO)
    data = vram_file.read_bytes()
    if len(data) < 65536:
        continue
    h = hashlib.md5(data).hexdigest()[:12]
    # Find corresponding CGRAM file
    cg_file = vram_file.parent / vram_file.name.replace("_vram.bin", "_cg.bin")
    cg_data = cg_file.read_bytes() if cg_file.exists() else None

    all_dumps.append({
        'path': str(rel_path),
        'dir': str(rel_path.parent),
        'name': vram_file.name.replace("_vram.bin", ""),
        'vram': data,
        'cgram': cg_data,
        'hash': h
    })

print(f"  Total VRAM dumps found: {len(all_dumps)}")

# === Step 2: Deduplicate by hash ===
print("\n" + "=" * 60)
print("Step 2: Deduplication")
print("=" * 60)

unique_dumps = {}
for d in all_dumps:
    if d['hash'] not in unique_dumps:
        unique_dumps[d['hash']] = d
        unique_dumps[d['hash']]['sources'] = [d['path']]
    else:
        unique_dumps[d['hash']]['sources'].append(d['path'])

print(f"  Unique VRAM states: {len(unique_dumps)}")
print(f"  Duplicate rate: {(len(all_dumps) - len(unique_dumps)) / len(all_dumps) * 100:.1f}%")

# Group by directory
dir_counts = {}
for d in all_dumps:
    dir_counts[d['dir']] = dir_counts.get(d['dir'], 0) + 1

print(f"\n  Dumps by directory:")
for dir_name, count in sorted(dir_counts.items()):
    print(f"    {dir_name}: {count}")

# === Step 3: Analyze VRAM regions across all unique dumps ===
print("\n" + "=" * 60)
print("Step 3: VRAM region analysis across all unique dumps")
print("=" * 60)

regions = [
    ("BG1 map", 0x0000, 0x0800),
    ("BG2 map", 0x0800, 0x1000),
    ("BG3 map", 0x1000, 0x1800),
    ("Unused1", 0x1800, 0x2000),
    ("Empty1", 0x2000, 0x4000),
    ("Dyn char", 0x4000, 0x6000),
    ("Empty2", 0x6000, 0x8000),
    ("Static char", 0x8000, 0x10000),
]

# Find the most common VRAM pattern for each region
region_patterns = {}
for name, start, end in regions:
    hashes = []
    for d in unique_dumps.values():
        region_data = d['vram'][start:end]
        rh = hashlib.md5(region_data).hexdigest()[:8]
        hashes.append(rh)
    
    # Count unique patterns
    unique_patterns = len(set(hashes))
    
    # Check if region is all zeros
    all_zero = all(
        all(b == 0 for b in d['vram'][start:end])
        for d in unique_dumps.values()
    )
    
    region_patterns[name] = {
        'unique_patterns': unique_patterns,
        'all_zero': all_zero,
        'size': end - start
    }
    
    status = "ALL ZEROS" if all_zero else f"{unique_patterns} unique patterns"
    print(f"  {name:<15} (0x{start:04X}-0x{end:04X}): {status}")

# === Step 4: Build master tile catalog ===
print("\n" + "=" * 60)
print("Step 4: Building master tile catalog")
print("=" * 60)

# Collect all unique tiles from static char region (0x8000-0xFFFF)
# This region is shared across all scenes
static_tiles = {}  # tile_hash -> (offset, first_scene)
dyn_tiles = {}     # tile_hash -> (offset, first_scene)

for d in unique_dumps.values():
    vram = d['vram']
    name = d['name']
    
    # Static char region: 0x8000-0xFFFF = 32KB = 1024 tiles
    for tile_idx in range(1024):
        offset = 0x8000 + tile_idx * 32
        th = tile_hash(vram, offset)
        if th not in static_tiles:
            static_tiles[th] = {
                'tile_idx': tile_idx,
                'first_scene': name,
                'offset': offset
            }
    
    # Dynamic char region: 0x4000-0x5FFF = 8KB = 256 tiles
    for tile_idx in range(256):
        offset = 0x4000 + tile_idx * 32
        th = tile_hash(vram, offset)
        if th not in dyn_tiles:
            dyn_tiles[th] = {
                'tile_idx': tile_idx,
                'first_scene': name,
                'offset': offset
            }

print(f"  Static char region (0x8000+): {len(static_tiles)} unique tiles (of 1024 slots)")
print(f"  Dynamic char region (0x4000+): {len(dyn_tiles)} unique tiles (of 256 slots)")

# Count non-empty tiles (not all zeros)
static_nonempty = sum(1 for th, info in static_tiles.items() 
                      if th != "00000000" and th != tile_hash(b'\x00' * 32, 0))
dyn_nonempty = sum(1 for th, info in dyn_tiles.items() 
                   if th != "00000000" and th != tile_hash(b'\x00' * 32, 0))
print(f"  Static non-empty tiles: {static_nonempty}")
print(f"  Dynamic non-empty tiles: {dyn_nonempty}")

# === Step 5: Create master tile sheets ===
print("\n" + "=" * 60)
print("Step 5: Creating master tile sheets")
print("=" * 60)

# Use the first dump with CGRAM for rendering
ref_dump = None
for d in unique_dumps.values():
    if d['cgram'] and len(d['cgram']) >= 512:
        ref_dump = d
        break

if ref_dump:
    colors = read_cgram(ref_dump['cgram'])
    ref_vram = ref_dump['vram']
    
    # Static tile sheet - all unique tiles from 0x8000+
    # Grid: 32 tiles wide
    static_nonempty_tiles = [(th, info) for th, info in static_tiles.items() 
                             if th != "00000000"]
    cols = 32
    rows = (len(static_nonempty_tiles) + cols - 1) // cols
    if rows > 0:
        img = Image.new('RGB', (cols * 8, rows * 8), (0, 0, 0))
        px = img.load()
        for i, (th, info) in enumerate(static_nonempty_tiles):
            # Find this tile in ref_vram or any dump
            tile_data = None
            for d in unique_dumps.values():
                offset = 0x8000 + info['tile_idx'] * 32
                if offset + 32 <= len(d['vram']):
                    if tile_hash(d['vram'], offset) == th:
                        tile_data = decode_4bpp_tile(d['vram'], offset)
                        break
            if tile_data:
                tx = (i % cols) * 8
                ty = (i // cols) * 8
                for r in range(8):
                    for c in range(8):
                        pval = tile_data[r * 8 + c]
                        if pval < len(colors):
                            px[tx + c, ty + r] = colors[pval]
        img.save(OUT / "master_static_tiles.png")
        print(f"  Static tile sheet: {cols}x{rows} tiles -> master_static_tiles.png")
    
    # Dynamic tile sheet - all unique tiles from 0x4000+
    dyn_nonempty_tiles = [(th, info) for th, info in dyn_tiles.items() 
                          if th != "00000000"]
    cols = 32
    rows = (len(dyn_nonempty_tiles) + cols - 1) // cols
    if rows > 0:
        img = Image.new('RGB', (cols * 8, rows * 8), (0, 0, 0))
        px = img.load()
        for i, (th, info) in enumerate(dyn_nonempty_tiles):
            tile_data = None
            for d in unique_dumps.values():
                offset = 0x4000 + info['tile_idx'] * 32
                if offset + 32 <= len(d['vram']):
                    if tile_hash(d['vram'], offset) == th:
                        tile_data = decode_4bpp_tile(d['vram'], offset)
                        break
            if tile_data:
                tx = (i % cols) * 8
                ty = (i // cols) * 8
                for r in range(8):
                    for c in range(8):
                        pval = tile_data[r * 8 + c]
                        if pval < len(colors):
                            px[tx + c, ty + r] = colors[pval]
        img.save(OUT / "master_dynamic_tiles.png")
        print(f"  Dynamic tile sheet: {cols}x{rows} tiles -> master_dynamic_tiles.png")

# === Step 6: CGRAM palette comparison ===
print("\n" + "=" * 60)
print("Step 6: CGRAM palette comparison")
print("=" * 60)

unique_cgrams = {}
for d in all_dumps:
    if d['cgram'] and len(d['cgram']) >= 512:
        ch = hashlib.md5(d['cgram']).hexdigest()[:12]
        if ch not in unique_cgrams:
            unique_cgrams[ch] = {
                'data': d['cgram'],
                'scenes': [d['name']]
            }
        else:
            unique_cgrams[ch]['scenes'].append(d['name'])

print(f"  Unique CGRAM palettes: {len(unique_cgrams)}")

# Create palette comparison image
if unique_cgrams:
    cols = min(len(unique_cgrams), 8)
    rows = (len(unique_cgrams) + cols - 1) // cols
    img = Image.new('RGB', (cols * 256, rows * 32), (0, 0, 0))
    px = img.load()
    for i, (ch, info) in enumerate(unique_cgrams.items()):
        colors = read_cgram(info['data'])
        cx = (i % cols) * 256
        cy = (i // cols) * 32
        for ci, color in enumerate(colors):
            for h in range(32):
                px[cx + ci, cy + h] = color
    img.save(OUT / "palette_comparison.png")
    print(f"  Palette comparison image saved ({len(unique_cgrams)} palettes)")

# === Step 7: Generate summary report ===
print("\n" + "=" * 60)
print("Step 7: Generating summary report")
print("=" * 60)

report = {
    'total_vram_dumps': len(all_dumps),
    'unique_vram_states': len(unique_dumps),
    'duplicate_rate_pct': round((len(all_dumps) - len(unique_dumps)) / len(all_dumps) * 100, 1),
    'dumps_by_directory': dir_counts,
    'vram_regions': region_patterns,
    'static_char_tiles': {
        'total_slots': 1024,
        'unique_tiles': len(static_tiles),
        'non_empty_tiles': static_nonempty
    },
    'dynamic_char_tiles': {
        'total_slots': 256,
        'unique_tiles': len(dyn_tiles),
        'non_empty_tiles': dyn_nonempty
    },
    'unique_cgram_palettes': len(unique_cgrams),
    'unique_dumps': [
        {
            'hash': h,
            'name': d['name'],
            'directory': d['dir'],
            'sources': d['sources'][:5]  # First 5 sources
        }
        for h, d in unique_dumps.items()
    ]
}

with open(OUT / "vram_catalog_report.json", 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(f"  Report saved: vram_catalog_report.json")
print(f"\n{'=' * 60}")
print(f"SUMMARY")
print(f"{'=' * 60}")
print(f"  Total VRAM dumps: {len(all_dumps)}")
print(f"  Unique VRAM states: {len(unique_dumps)}")
print(f"  Duplicate rate: {report['duplicate_rate_pct']}%")
print(f"  Unique CGRAM palettes: {len(unique_cgrams)}")
print(f"  Static tiles: {static_nonempty} non-empty (of 1024 slots)")
print(f"  Dynamic tiles: {dyn_nonempty} non-empty (of 256 slots)")
print(f"\n  Output files in {OUT}:")
for f in sorted(OUT.iterdir()):
    print(f"    {f.name}")
