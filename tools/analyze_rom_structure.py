#!/usr/bin/env python3
"""Analyze ROM structure: bank mapping, data distribution, identify code vs data banks"""
from pathlib import Path
import struct

ROM_PATH = Path("/workspace/.uploads/db23ff94-7eea-4a72-b2d6-9e125cf021b5_MMR.smc")
OUT = Path("/data/user/work/rom_analysis")
OUT.mkdir(exist_ok=True)

data = ROM_PATH.read_bytes()
print(f"ROM size: {len(data)} bytes ({len(data)/1024/1024:.2f} MB)")

# Check for SMC header
header_offset = 512 if data[8:16] == b'\x00' * 8 else 0
if header_offset:
    print(f"SMC copier header detected, offset: {header_offset}")

rom = data[header_offset:]
rom_size = len(rom)
print(f"ROM data: {rom_size} bytes")

# SNES LoROM bank mapping:
# Bank $00-$3F: ROM $0000-$7FFF = $C00000-$FFFF at even banks, $8000-$FFFF = $8000-$FFFF at odd banks
# Bank $40-$7F: mirrors of $00-$3F (LoROM)
# Bank $80-$BF: same as $00-$3F (LoROM)
# Bank $C0-$FF: same as $00-$3F (LoROM)

# For LoROM 4MB:
# PC addr $8000-$FFFF in bank $00-$3F maps to ROM offset
# Formula: offset = (bank * 8192) + ($8000 offset within bank)
# For LoROM: ROM_offset = bank * 0x8000 + (addr & 0x7FFF) - 0x8000
# Actually for LoROM: $00-$3F banks map to ROM linearly
# Bank $XX8000 maps to ROM_offset = XX * 0x8000 (for banks 00-3F)

def lorom_pc_to_rom(bank, addr):
    """Convert SNES LoROM PC address to ROM offset"""
    # LoROM: banks $00-$3F and $80-$BF
    bank = bank & 0x7F
    if bank >= 0x40:
        return None
    offset = bank * 0x8000 + (addr & 0x7FFF)
    return offset

# Analyze each 8KB bank
print("\n" + "=" * 60)
print("ROM BANK ANALYSIS (LoROM 8KB banks)")
print("=" * 60)

num_banks = rom_size // 0x8000
print(f"Total banks: {num_banks}")

# Classify each bank by entropy
import math

def byte_entropy(block):
    """Calculate Shannon entropy of a byte block"""
    if len(block) == 0:
        return 0
    freq = [0] * 256
    for b in block:
        freq[b] += 1
    entropy = 0
    for f in freq:
        if f > 0:
            p = f / len(block)
            entropy -= p * math.log2(p)
    return entropy

bank_info = []
for bank_idx in range(num_banks):
    start = bank_idx * 0x8000
    end = min(start + 0x8000, rom_size)
    block = rom[start:end]

    entropy = byte_entropy(block)
    zero_pct = sum(1 for b in block if b == 0) / len(block) * 100
    ff_pct = sum(1 for b in block if b == 0xFF) / len(block) * 100
    high_entropy = entropy > 7.0

    # SNES bank number
    snes_bank = bank_idx
    if bank_idx < 0x40:
        snes_bank = bank_idx
    else:
        snes_bank = bank_idx - 0x40  # Mirror

    bank_info.append({
        'idx': bank_idx,
        'start': start,
        'snes_bank': snes_bank,
        'entropy': entropy,
        'zero_pct': zero_pct,
        'ff_pct': ff_pct,
        'is_data': high_entropy,
    })

# Print bank table
print(f"\n{'Bank':>4} {'ROM Addr':>10} {'Entropy':>8} {'Zero%':>7} {'FF%':>6} {'Type':>8}")
print("-" * 50)

for b in bank_info:
    btype = "DATA" if b['is_data'] else ("EMPTY" if b['zero_pct'] > 90 else "CODE/TBL")
    marker = " *" if b['is_data'] else ""
    print(f"${b['snes_bank']:02X}   0x{b['start']:06X}   {b['entropy']:>7.3f} {b['zero_pct']:>6.1f}% {b['ff_pct']:>5.1f}% {btype:>8}{marker}")

# Summarize by type
code_banks = [b for b in bank_info if not b['is_data'] and b['zero_pct'] < 90]
data_banks = [b for b in bank_info if b['is_data']]
empty_banks = [b for b in bank_info if b['zero_pct'] > 90]

print(f"\n{'='*60}")
print(f"SUMMARY")
print(f"{'='*60}")
print(f"  Code/Table banks: {len(code_banks)} ({len(code_banks)*32} KB)")
print(f"  Data banks (high entropy): {len(data_banks)} ({len(data_banks)*32} KB)")
print(f"  Empty banks (>90% zeros): {len(empty_banks)} ({len(empty_banks)*32} KB)")

# Find game header
print(f"\n{'='*60}")
print("GAME HEADER (LoROM at $00FFC0)")
print(f"{'='*60}")

# LoROM header at $00FFC0 = ROM offset 0x7FC0
hdr_offset = lorom_pc_to_rom(0x00, 0xFFC0)
if hdr_offset and hdr_offset + 64 <= len(rom):
    header = rom[hdr_offset:hdr_offset+64]
    maker = header[0x10:0x12].decode('ascii', errors='replace').strip('\x00')
    game_code = header[0x12:0x15].decode('ascii', errors='replace').strip('\x00')
    game_name = header[0x20:0x36].decode('ascii', errors='replace').strip('\x00').strip()
    rom_size_val = header[0x17]
    sram_size_val = header[0x18]
    
    rom_sizes = {0: '2Mbit/256KB', 1: '4Mbit/512KB', 2: '8Mbit/1MB', 3: '16Mbit/2MB',
                 4: '32Mbit/4MB', 5: '64Mbit/8MB', 6: '128Mbit/16MB'}
    sram_sizes = {0: 'None', 1: '16Kbit', 2: '64Kbit', 3: '256Kbit', 4: '1Mbit'}
    
    print(f"  Maker code: {maker}")
    print(f"  Game code: {game_code}")
    print(f"  Game name: {game_name}")
    print(f"  ROM size: {rom_sizes.get(rom_size_val, f'Unknown ({rom_size_val})')}")
    print(f"  SRAM size: {sram_sizes.get(sram_size_val, f'Unknown ({sram_size_val})')}")
    print(f"  Version: {header[0x1B]}")
    print(f"  Checksum: 0x{header[0x1E] | (header[0x1F] << 8):04X}")
    print(f"  Complement: 0x{header[0x1C] | (header[0x1D] << 8):04X}")

# Vector table
print(f"\n{'='*60}")
print("INTERRUPT VECTORS (LoROM $00FFE0)")
print(f"{'='*60}")
vec_offset = lorom_pc_to_rom(0x00, 0xFFE0)
if vec_offset and vec_offset + 32 <= len(rom):
    vectors = rom[vec_offset:vec_offset+32]
    vec_names = ['NMI', 'RESET', 'IRQ', 'UNUSED']
    for i, name in enumerate(vec_names):
        lo = vectors[i*2]
        hi = vectors[i*2+1]
        addr = lo | (hi << 8)
        if i < 2:
            bank = "00" if addr < 0x8000 else "00"
            full = f"${bank}:{addr:04X}"
        else:
            full = f"${addr:04X}"
        print(f"  {name:<10}: {full}")

# Data density analysis by ROM offset ranges
print(f"\n{'='*60}")
print("DATA DENSITY BY ROM RANGE")
print(f"{'='*60}")

ranges = []
step = 0x10000  # 64KB chunks
for start in range(0, rom_size, step):
    end = min(start + step, rom_size)
    block = rom[start:end]
    e = byte_entropy(block)
    z = sum(1 for b in block if b == 0) / len(block) * 100
    ranges.append((start, end, e, z))

print(f"{'Range':>14} {'Entropy':>8} {'Zero%':>7} {'Description':>20}")
print("-" * 55)
for start, end, e, z in ranges:
    desc = "SPC700/DSP" if 0x4000 < start < 0x10000 else ("CODE" if z > 80 else ("DATA" if e > 7.0 else "CODE/MIX"))
    print(f"0x{start:06X}-0x{end:06X} {e:>7.3f} {z:>6.1f}% {desc:>20}")

# Write report
report_path = OUT / "rom_structure_report.txt"
with open(report_path, 'w', encoding='utf-8') as f:
    f.write("MMR ROM Structure Analysis\n")
    f.write("=" * 60 + "\n\n")
    f.write(f"ROM size: {len(data)} bytes ({len(data)/1024/1024:.2f} MB)\n")
    f.write(f"Header offset: {header_offset}\n\n")
    f.write(f"Code/Table banks: {len(code_banks)}\n")
    f.write(f"Data banks: {len(data_banks)}\n")
    f.write(f"Empty banks: {len(empty_banks)}\n\n")
    f.write(f"Bank details:\n")
    f.write(f"{'Bank':>4} {'ROM Addr':>10} {'Entropy':>8} {'Zero%':>7} {'FF%':>6} {'Type':>8}\n")
    f.write("-" * 50 + "\n")
    for b in bank_info:
        btype = "DATA" if b['is_data'] else ("EMPTY" if b['zero_pct'] > 90 else "CODE/TBL")
        f.write(f"${b['snes_bank']:02X}   0x{b['start']:06X}   {b['entropy']:>7.3f} {b['zero_pct']:>6.1f}% {b['ff_pct']:>5.1f}% {btype:>8}\n")

print(f"\nReport saved: {report_path}")
print(f"\nDone!")
