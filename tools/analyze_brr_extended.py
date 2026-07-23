#!/usr/bin/env python3
"""Analyze extended BRR captures:
1. Compare SPC RAM/DSP across scenes
2. Extract BRR sample blocks from SPC RAM
3. Identify active audio channels per scene
"""
import hashlib
from pathlib import Path

SRC = Path("/data/user/work/brr_extended")
OUT = Path("/data/user/work/brr_extended_analysis")
OUT.mkdir(exist_ok=True)

# SNES DSP register offsets
DSP_REG_NAMES = {
    0x00: "CH0_VOL_LEFT", 0x01: "CH0_VOL_RIGHT", 0x02: "CH0_PITCH_LOW",
    0x03: "CH0_PITCH_HIGH", 0x04: "CH0_SRCN", 0x05: "CH0_ADSR1",
    0x06: "CH0_ADSR2", 0x07: "CH0_GAIN", 0x08: "CH0_ENVX",
    0x09: "CH0_OUTX",
    0x10: "CH1_VOL_LEFT", 0x11: "CH1_VOL_RIGHT", 0x12: "CH1_PITCH_LOW",
    0x13: "CH1_PITCH_HIGH", 0x14: "CH1_SRCN", 0x15: "CH1_ADSR1",
    0x16: "CH1_ADSR2", 0x17: "CH1_GAIN", 0x18: "CH1_ENVX",
    0x19: "CH1_OUTX",
    0x20: "CH2_VOL_LEFT", 0x21: "CH2_VOL_RIGHT", 0x22: "CH2_PITCH_LOW",
    0x23: "CH2_PITCH_HIGH", 0x24: "CH2_SRCN", 0x25: "CH2_ADSR2",
    0x26: "CH2_ADSR2", 0x27: "CH2_GAIN", 0x28: "CH2_ENVX",
    0x29: "CH2_OUTX",
    0x30: "CH3_VOL_LEFT", 0x31: "CH3_VOL_RIGHT", 0x32: "CH3_PITCH_LOW",
    0x33: "CH3_PITCH_HIGH", 0x34: "CH3_SRCN", 0x35: "CH3_ADSR1",
    0x36: "CH3_ADSR2", 0x37: "CH3_GAIN", 0x38: "CH3_ENVX",
    0x39: "CH3_OUTX",
    0x40: "CH4_VOL_LEFT", 0x41: "CH4_VOL_RIGHT", 0x42: "CH4_PITCH_LOW",
    0x43: "CH4_PITCH_HIGH", 0x44: "CH4_SRCN", 0x45: "CH4_ADSR1",
    0x46: "CH4_ADSR2", 0x47: "CH4_GAIN", 0x48: "CH4_ENVX",
    0x49: "CH4_OUTX",
    0x50: "CH5_VOL_LEFT", 0x51: "CH5_VOL_RIGHT", 0x52: "CH5_PITCH_LOW",
    0x53: "CH5_PITCH_HIGH", 0x54: "CH5_SRCN", 0x55: "CH5_ADSR1",
    0x56: "CH5_ADSR2", 0x57: "CH5_GAIN", 0x58: "CH5_ENVX",
    0x59: "CH5_OUTX",
    0x60: "CH6_VOL_LEFT", 0x61: "CH6_VOL_RIGHT", 0x62: "CH6_PITCH_LOW",
    0x63: "CH6_PITCH_HIGH", 0x64: "CH6_SRCN", 0x65: "CH6_ADSR1",
    0x66: "CH6_ADSR2", 0x67: "CH6_GAIN", 0x68: "CH6_ENVX",
    0x69: "CH6_OUTX",
    0x70: "CH7_VOL_LEFT", 0x71: "CH7_VOL_RIGHT", 0x72: "CH7_PITCH_LOW",
    0x73: "CH7_PITCH_HIGH", 0x74: "CH7_SRCN", 0x75: "CH7_ADSR1",
    0x76: "CH7_ADSR2", 0x77: "CH7_GAIN", 0x78: "CH7_ENVX",
    0x79: "CH7_OUTX",
    0x0C: "MVOLL", 0x0D: "MVOLR", 0x0E: "EVOLL", 0x0F: "EVOLR",
    0x6C: "FLG", 0x7C: "ENDX", 0x7D: "EFB", 0x7E: "DIR",
    0x7F: "ESA", 0x4C: "PMON", 0x5C: "NON", 0x6D: "EON",
    0x3C: "MUTE", 0x4D: "ECHO", 0x2C: "KON", 0x3D: "KOFF",
}

# Load all scenes
print("=" * 60)
print("Loading BRR/SPC captures")
print("=" * 60)

scenes = []
for spcf in sorted(SRC.glob("*_spcRam.bin")):
    label = spcf.name.replace("_spcRam.bin", "")
    spcRom = SRC / f"{label}_spcRom.bin"
    dspRegs = SRC / f"{label}_dspRegs.bin"
    if not all(f.exists() for f in [spcRom, dspRegs]):
        continue
    spc_ram = spcf.read_bytes()
    dsp = dspRegs.read_bytes()
    scenes.append({
        'label': label,
        'spc_ram': spc_ram,
        'spc_rom': spcRom.read_bytes(),
        'dsp': dsp,
        'ram_hash': hashlib.md5(spc_ram).hexdigest()[:12],
        'dsp_hash': hashlib.md5(dsp).hexdigest()[:12]
    })
    print(f"  {label}: RAM hash={hashlib.md5(spc_ram).hexdigest()[:12]}, DSP hash={hashlib.md5(dsp).hexdigest()[:12]}")

# SPC RAM comparison
print("\n" + "=" * 60)
print("SPC RAM comparison (vs title)")
print("=" * 60)

base = scenes[0]['spc_ram']
for s in scenes:
    diff = sum(1 for i in range(min(len(base), len(s['spc_ram']))) if base[i] != s['spc_ram'][i])
    pct = diff / len(base) * 100
    print(f"  {s['label']:<25} {diff:>6} bytes diff ({pct:.2f}%)")

# DSP register analysis - active channels
print("\n" + "=" * 60)
print("Active audio channels per scene")
print("=" * 60)

print(f"{'Scene':<25} {'Active':>8} {'KON':>10} {'SRCNs used':>30}")
print("-" * 80)

for s in scenes:
    dsp = s['dsp']
    kon = dsp[0x2C] if len(dsp) > 0x2C else 0
    endx = dsp[0x7C] if len(dsp) > 0x7C else 0
    eon = dsp[0x6D] if len(dsp) > 0x6D else 0

    active_bits = f"{kon:08b}"
    active_count = bin(kon).count('1')

    srcns = []
    for ch in range(8):
        if kon & (1 << ch):
            reg = 0x04 + ch * 0x10
            srcn = dsp[reg] if reg < len(dsp) else 0
            srcns.append(f"CH{ch}:{srcn}")

    print(f"  {s['label']:<25} {active_count:>8} {kon:>10} {','.join(srcns):>30}")

# SPC ROM comparison
print("\n" + "=" * 60)
print("SPC ROM comparison (should be identical)")
print("=" * 60)

base_rom = scenes[0]['spc_rom']
all_same = True
for s in scenes:
    diff = sum(1 for i in range(min(len(base_rom), len(s['spc_rom']))) if base_rom[i] != s['spc_rom'][i])
    if diff > 0:
        all_same = False
        print(f"  {s['label']}: {diff} bytes diff")
if all_same:
    print("  All SPC ROM dumps are identical (expected)")

# Find BRR samples in SPC RAM
print("\n" + "=" * 60)
print("BRR sample detection in SPC RAM")
print("=" * 60)

def find_brr_samples(data):
    """Find BRR sample headers in SPC RAM"""
    # BRR header: nybble[0] = flags (1=end, 0=loop), nybble[1] = filter mode
    # BRR data blocks are 9 bytes each
    # A sample start has: first byte upper nybble = 0 (start flag), 
    # or look for typical patterns
    samples = []
    i = 0
    while i < len(data) - 9:
        b = data[i]
        # BRR block header: upper nybble bits 0-3, lower nybble bits 4-7
        # flags = b >> 4, filter = b & 0x0F
        # End flag is bit 0 of the flags nybble
        # Look for sequences of BRR blocks
        if (b & 0xC0) == 0x00 or (b & 0xC0) == 0x01:  # Possible BRR header
            # Check if next 8 bytes look like BRR data
            is_brr = True
            for j in range(9):
                if i + j >= len(data):
                    is_brr = False
                    break
                # BRR data should have varied values
                pass  # Hard to distinguish from other data
            if is_brr:
                samples.append(i)
                i += 9  # Skip this BRR block
            else:
                i += 1
        else:
            i += 1
    return samples

# Instead, check the DSP DIR register to find sample directory
for s in scenes:
    dsp = s['dsp']
    if len(dsp) > 0x7E:
        dir_reg = dsp[0x7E]  # DIR
        esa_reg = dsp[0x7F]  # ESA (echo start address)
        print(f"  {s['label']}: DIR=0x{dir_reg:02X}00, ESA=0x{esa_reg:02X}00")
        # DIR points to the sample directory table in SPC RAM
        # Each entry is 4 bytes: start_address(2), loop_address(2)
        dir_addr = dir_reg * 0x100
        spc_ram = s['spc_ram']
        sample_count = 0
        entry = 0
        while entry < 64 and dir_addr + entry * 4 + 4 <= len(spc_ram):
            sa = spc_ram[dir_addr + entry * 4] | (spc_ram[dir_addr + entry * 4 + 1] << 8)
            la = spc_ram[dir_addr + entry * 4 + 2] | (spc_ram[dir_addr + entry * 4 + 3] << 8)
            if sa == 0 and la == 0:
                break
            sample_count += 1
            entry += 1
        print(f"    -> {sample_count} samples in directory (at 0x{dir_addr:04X})")
    break  # Only print first scene (DIR should be same)

# Create SPC RAM contact visualization
print("\n" + "=" * 60)
print("SPC RAM activity map")
print("=" * 60)

# Compare all scenes to title, find active regions
activity = [0] * 65536
for s in scenes[1:]:
    for i in range(min(len(base), len(s['spc_ram']))):
        if base[i] != s['spc_ram'][i]:
            activity[i] += 1

# Find active regions
print("Most active SPC RAM regions (changed in most scenes):")
block_size = 256
block_counts = [0] * (65536 // block_size)
for i in range(65536):
    blk = i // block_size
    if blk < len(block_counts):
        block_counts[blk] += activity[i]

for blk in range(len(block_counts)):
    if block_counts[blk] > len(scenes) * 0.5:
        addr = blk * block_size
        print(f"  0x{addr:04X}-0x{addr+block_size-1:04X}: {block_counts[blk]}/{len(scenes)-1} scenes")

print(f"\nDone! Output in {OUT}")
print(f"  {len(scenes)} SPC captures analyzed")
