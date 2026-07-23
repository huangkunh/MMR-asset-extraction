#!/usr/bin/env python3
"""Parse WRAM dumps for game state variables.
Common SNES RPG WRAM layout patterns:
- $7E0000-$7E00FF: Direct page / zero page (game flags, counters)
- $7E0100-$7E01FF: Stack
- $7E0200+: Game state variables (player position, stats, etc.)
"""
import hashlib
from pathlib import Path

SRC = Path("/data/user/work/wram_scenes")
OUT = Path("/data/user/work/wram_state_analysis")
OUT.mkdir(exist_ok=True)

# Load all WRAM dumps
scenes = []
for wf in sorted(SRC.glob("*_wram.bin")):
    label = wf.name.replace("_wram.bin", "")
    data = wf.read_bytes()
    scenes.append({'label': label, 'data': data})

print(f"Loaded {len(scenes)} WRAM dumps")

# Analyze direct page ($0000-$00FF) across all scenes
print("\n" + "=" * 60)
print("Direct Page ($0000-$00FF) Analysis")
print("=" * 60)

# Find bytes that change between scenes
base = scenes[0]['data']
changing_bytes = {}
for i in range(256):
    values = set()
    for s in scenes:
        values.add(s['data'][i])
    if len(values) > 1:
        changing_bytes[i] = values

print(f"  Changing bytes in direct page: {len(changing_bytes)} / 256")

# Group changing bytes
if changing_bytes:
    print("\n  Address  | Values across scenes")
    print("  " + "-" * 50)
    for addr in sorted(changing_bytes.keys())[:30]:
        vals = []
        for s in scenes:
            vals.append(f"{s['data'][addr]:02X}")
        print(f"  $00:{addr:02X} ({addr:3d}) | {' '.join(vals)}")

# Analyze $0200-$0FFF range for game state
print("\n" + "=" * 60)
print("Game State Variables ($0200-$0FFF)")
print("=" * 60)

state_vars = []
for i in range(0x200, 0x1000):
    values = []
    for s in scenes:
        values.append(s['data'][i])
    unique = len(set(values))
    if unique > 1 and unique < len(scenes):
        # This looks like a state variable
        state_vars.append({
            'addr': i,
            'values': values,
            'unique': unique
        })

print(f"  State variables found: {len(state_vars)}")

# Show top changing variables
for v in sorted(state_vars, key=lambda x: x['unique'], reverse=True)[:30]:
    vals_str = ' '.join(f"{x:02X}" for x in v['values'])
    print(f"  $7E{v['addr']:04X} | {v['unique']:2d} values | {vals_str}")

# Look for 16-bit position counters (common in RPGs)
print("\n" + "=" * 60)
print("16-bit counters (potential position/stats)")
print("=" * 60)

for i in range(0x200, 0x2000):
    # Check if this + next byte form a changing 16-bit value
    vals16 = []
    for s in scenes:
        val = s['data'][i] | (s['data'][i+1] << 8)
        vals16.append(val)
    
    unique16 = len(set(vals16))
    if unique16 > 3 and unique16 < len(scenes):
        # Check if values look like coordinates (small, incrementing)
        max_val = max(vals16)
        min_val = min(vals16)
        if 0 < max_val < 0x10000 and max_val - min_val < 0x1000:
            vals_str = ' '.join(f"{v:04X}" for v in vals16)
            print(f"  $7E{i:04X} | {unique16:2d} values | range [{min_val:04X}-{max_val:04X}] | {vals_str}")

# Analyze higher WRAM regions for patterns
print("\n" + "=" * 60)
print("WRAM Region Summary")
print("=" * 60)

regions = [
    ("Direct Page", 0x0000, 0x0100),
    ("Stack", 0x0100, 0x0200),
    ("Game State", 0x0200, 0x1000),
    ("Work Buffer 1", 0x1000, 0x2000),
    ("Work Buffer 2", 0x2000, 0x4000),
    ("DMA Buffer", 0x4000, 0x6000),
    ("Extended RAM", 0x6000, 0x10000),
    ("Bank $7E Upper", 0x10000, 0x20000),
]

for name, start, end in regions:
    total = 0
    changing = 0
    for i in range(start, min(end, len(base))):
        total += 1
        vals = set(s['data'][i] for s in scenes)
        if len(vals) > 1:
            changing += 1
    pct = changing / total * 100 if total > 0 else 0
    print(f"  {name:<20} ($7E{start:04X}-${end:04X}): {changing:>5}/{total:>5} changing ({pct:.1f}%)")

# Save analysis report
with open(OUT / "wram_state_report.txt", 'w', encoding='utf-8') as f:
    f.write("MMR WRAM Game State Analysis\n")
    f.write("=" * 60 + "\n\n")
    f.write(f"Scenes analyzed: {len(scenes)}\n")
    f.write(f"Scene labels: {[s['label'] for s in scenes]}\n\n")
    
    f.write("Direct Page changing bytes:\n")
    for addr in sorted(changing_bytes.keys()):
        vals = ' '.join(f"{s['data'][addr]:02X}" for s in scenes)
        f.write(f"  $00:{addr:02X}: {vals}\n")
    
    f.write(f"\nGame state variables ($0200-$0FFF): {len(state_vars)} found\n")
    for v in sorted(state_vars, key=lambda x: x['unique'], reverse=True):
        vals_str = ' '.join(f"{x:02X}" for x in v['values'])
        f.write(f"  $7E{v['addr']:04X}: {v['unique']} values | {vals_str}\n")

print(f"\nReport saved: {OUT / 'wram_state_report.txt'}")
