#!/usr/bin/env python3
"""Extract SJIS text strings directly from ROM file"""
from pathlib import Path

ROM_PATH = Path("/workspace/.uploads/db23ff94-7eea-4a72-b2d6-9e125cf021b5_MMR.smc")
OUT = Path("/data/user/work/rom_text")
OUT.mkdir(exist_ok=True)

def is_sjis_lead(b):
    return (0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xEF)

def is_sjis_trail(b):
    return (0x40 <= b <= 0x7E) or (0x80 <= b <= 0xFC)

def extract_sjis_strings(data, min_len=3):
    """Extract SJIS strings from ROM data"""
    strings = []
    i = 0
    rom_size = len(data)

    while i < rom_size - 1:
        b1 = data[i]
        if is_sjis_lead(b1):
            start = i
            while i < rom_size - 1:
                b1 = data[i]
                if is_sjis_lead(b1):
                    b2 = data[i + 1]
                    if is_sjis_trail(b2):
                        i += 2
                    else:
                        break
                elif 0x20 <= b1 <= 0x7E:  # ASCII mixed in
                    i += 1
                else:
                    break
            length = (i - start) // 2
            if length >= min_len:
                try:
                    text = data[start:i].decode('shift_jis')
                    # Filter out control chars and garbage
                    if all(ord(c) >= 0x20 or c in '\n\r' for c in text):
                        strings.append((start, length, text))
                except:
                    pass
        i += 1
    return strings

def extract_ascii_strings(data, min_len=4):
    """Extract ASCII strings from ROM data"""
    strings = []
    i = 0
    while i < len(data):
        if 0x20 <= data[i] <= 0x7E:
            start = i
            while i < len(data) and 0x20 <= data[i] <= 0x7E:
                i += 1
            if i - start >= min_len:
                try:
                    text = data[start:i].decode('ascii')
                    strings.append((start, i - start, text))
                except:
                    pass
        i += 1
    return strings

# Read ROM
print("Reading ROM...")
data = ROM_PATH.read_bytes()
print(f"ROM size: {len(data)} bytes ({len(data)/1024/1024:.1f} MB)")

# Skip copier header (512 bytes if present)
offset = 512 if len(data) > 512 and data[8:12] == b'\x00\x00\x00\x00' else 0
rom_data = data[offset:]
print(f"ROM data offset: {offset}, analyzing {len(rom_data)} bytes")

# Extract SJIS strings
print("\nExtracting SJIS strings...")
sjis_strings = extract_sjis_strings(rom_data, min_len=2)
print(f"Found {len(sjis_strings)} SJIS strings")

# Write SJIS strings
with open(OUT / "sjis_strings.txt", "w", encoding="utf-8") as f:
    f.write(f"# MMR ROM SJIS Text Extraction\n")
    f.write(f"# ROM: {ROM_PATH.name}\n")
    f.write(f"# Total strings: {len(sjis_strings)}\n")
    f.write(f"# Format: ROM_OFFSET | LENGTH | TEXT\n")
    f.write("=" * 60 + "\n\n")
    for addr, length, text in sjis_strings[:2000]:
        f.write(f"0x{addr+offset:06X} | {length:3d} | {text}\n")

print(f"  Written top 2000 SJIS strings to sjis_strings.txt")

# Extract ASCII strings
print("\nExtracting ASCII strings...")
ascii_strings = extract_ascii_strings(rom_data, min_len=5)
print(f"Found {len(ascii_strings)} ASCII strings")

with open(OUT / "ascii_strings.txt", "w", encoding="utf-8") as f:
    f.write(f"# MMR ROM ASCII Text Extraction\n")
    f.write(f"# Total strings: {len(ascii_strings)}\n\n")
    for addr, length, text in ascii_strings[:1000]:
        f.write(f"0x{addr+offset:06X} | {length:3d} | {text}\n")

print(f"  Written top 1000 ASCII strings to ascii_strings.txt")

# Summary statistics
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"  ROM size: {len(data)} bytes")
print(f"  SJIS strings: {len(sjis_strings)}")
print(f"  ASCII strings: {len(ascii_strings)}")
print(f"  Output directory: {OUT}")
