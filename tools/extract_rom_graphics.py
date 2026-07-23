#!/usr/bin/env python3
"""Extract and decompress graphics from ROM high-entropy data banks.
SNES games commonly use LZSS, LZ77, or custom compression.
This script:
1. Scans ROM data banks for compressed graphics
2. Tries common SNES decompression algorithms
3. Renders decompressed tiles as PNG sheets
"""
import struct
from pathlib import Path
from PIL import Image
import math

ROM_PATH = Path("/workspace/.uploads/db23ff94-7eea-4a72-b2d6-9e125cf021b5_MMR.smc")
OUT = Path("/data/user/work/rom_graphics")
OUT.mkdir(exist_ok=True)

# Read ROM
data = ROM_PATH.read_bytes()
header = 0
# Check for SMC header (512 bytes)
if len(data) > 512:
    # SMC header detection: if size is multiple of 0x8000 + 512
    if (len(data) - 512) % 0x8000 == 0:
        header = 512
        rom = data[header:]
    else:
        rom = data
else:
    rom = data

print(f"ROM: {len(rom)} bytes (header={header})")

# SNES 3bpp/4bpp tile rendering
def decode_4bpp_tile(tile_data, offset=0):
    """Decode 8x8 4bpp tile (32 bytes)"""
    pixels = []
    for row in range(8):
        base = offset + row * 2
        if base + 17 >= len(tile_data):
            pixels.extend([0] * 8)
            continue
        bp0 = tile_data[base]
        bp1 = tile_data[base + 1]
        bp2 = tile_data[base + 16]
        bp3 = tile_data[base + 17]
        for col in range(8):
            bit = 7 - col
            pixel = ((bp0 >> bit) & 1)
            pixel |= ((bp1 >> bit) & 1) << 1
            pixel |= ((bp2 >> bit) & 1) << 2
            pixel |= ((bp3 >> bit) & 1) << 3
            pixels.append(pixel)
    return pixels

def decode_3bpp_tile(tile_data, offset=0):
    """Decode 8x8 3bpp tile (24 bytes)"""
    pixels = []
    for row in range(8):
        base = offset + row * 2
        if base + 1 >= len(tile_data):
            pixels.extend([0] * 8)
            continue
        bp0 = tile_data[base]
        bp1 = tile_data[base + 1]
        for col in range(8):
            bit = 7 - col
            pixel = ((bp0 >> bit) & 1)
            pixel |= ((bp1 >> bit) & 1) << 1
            pixels.append(pixel)
    # Add 3rd bitplane
    for row in range(8):
        base = offset + 16 + row
        if base >= len(tile_data):
            continue
        bp2 = tile_data[base]
        for col in range(8):
            bit = 7 - col
            pixels[row * 8 + col] |= ((bp2 >> bit) & 1) << 2
    return pixels

def decode_2bpp_tile(tile_data, offset=0):
    """Decode 8x8 2bpp tile (16 bytes)"""
    pixels = []
    for row in range(8):
        base = offset + row * 2
        if base + 1 >= len(tile_data):
            pixels.extend([0] * 8)
            continue
        bp0 = tile_data[base]
        bp1 = tile_data[base + 1]
        for col in range(8):
            bit = 7 - col
            pixel = ((bp0 >> bit) & 1)
            pixel |= ((bp1 >> bit) & 1) << 1
            pixels.append(pixel)
    return pixels

def try_lzss_decompress(data, start, max_out=65536):
    """Try LZSS decompression from a given offset.
    Common SNES LZSS format:
    - Read control byte (8 flags)
    - For each bit: 1=literal, 0=back-reference
    - Back-ref: 2 bytes (offset+length)
    """
    out = bytearray()
    pos = start
    
    while pos < len(data) and len(out) < max_out:
        control = data[pos]
        pos += 1
        
        for bit in range(8):
            if len(out) >= max_out or pos >= len(data):
                break
            
            if control & (0x80 >> bit):
                # Literal byte
                out.append(data[pos])
                pos += 1
            else:
                # Back-reference
                if pos + 1 >= len(data):
                    break
                b1 = data[pos]
                b2 = data[pos + 1]
                pos += 2
                
                # Common LZSS: offset = ((b1 & 0xF) << 8 | b2) + 1, length = (b1 >> 4) + 3
                offset = ((b1 & 0x0F) << 8 | b2) + 1
                length = (b1 >> 4) + 3
                
                if offset > len(out):
                    break
                
                for j in range(length):
                    if len(out) >= max_out:
                        break
                    out.append(out[len(out) - offset])
    
    return bytes(out)

def try_rle_decompress(data, start, max_out=65536):
    """Try RLE decompression"""
    out = bytearray()
    pos = start
    
    while pos < len(data) and len(out) < max_out:
        b = data[pos]
        pos += 1
        
        if b & 0x80:
            # Run of same byte
            count = (b & 0x7F) + 1
            if pos >= len(data):
                break
            val = data[pos]
            pos += 1
            out.extend([val] * count)
        else:
            # Literal run
            count = b + 1
            for _ in range(count):
                if pos >= len(data) or len(out) >= max_out:
                    break
                out.append(data[pos])
                pos += 1
    
    return bytes(out)

def render_tilesheet(data, bpp=4, palette=None, max_tiles=256):
    """Render raw tile data as PNG"""
    tile_size = {2: 16, 3: 24, 4: 32}[bpp]
    num_tiles = min(len(data) // tile_size, max_tiles)
    if num_tiles == 0:
        return None
    
    cols = 16
    rows = (num_tiles + cols - 1) // cols
    
    img = Image.new('RGB', (cols * 8, rows * 8), (0, 0, 0))
    px = img.load()
    
    if palette is None:
        # Default grayscale palette
        palette = [(i * 17, i * 17, i * 17) for i in range(16)]
    
    for t in range(num_tiles):
        offset = t * tile_size
        if bpp == 4:
            tile = decode_4bpp_tile(data, offset)
        elif bpp == 3:
            tile = decode_3bpp_tile(data, offset)
        else:
            tile = decode_2bpp_tile(data, offset)
        
        tx = (t % cols) * 8
        ty = (t // cols) * 8
        for r in range(8):
            for c in range(8):
                val = tile[r * 8 + c]
                if val < len(palette):
                    px[tx + c, ty + r] = palette[val]
    
    return img

# Default palette (grayscale for visibility)
default_palette = [(i * 17, i * 17, i * 17) for i in range(16)]

# === Step 1: Scan ROM for tile data patterns ===
print("=" * 60)
print("Step 1: Scanning ROM for tile data patterns")
print("=" * 60)

# High-entropy data banks from previous analysis
data_banks = [
    (0x048000, 0x050000),  # Bank $09-$0A
    (0x090000, 0x098000),  # Bank $12
    (0x0D8000, 0x100000),  # Bank $1B-1D
    (0x100000, 0x130000),  # Bank $20-25
    (0x150000, 0x1A0000),  # Bank $2A-34
    (0x200000, 0x2C0000),  # Bank $40-5B (large data region)
]

# Try raw tile rendering on each data bank
print("\nRendering raw tiles from data banks...")
for start, end in data_banks:
    bank_data = rom[start:end]
    bank_label = f"0x{start:06X}"
    
    # Try 4bpp rendering
    img = render_tilesheet(bank_data, bpp=4, palette=default_palette, max_tiles=512)
    if img:
        img.save(OUT / f"raw_4bpp_{bank_label}.png")
        print(f"  {bank_label}: 4bpp -> {img.size}")
    
    # Try 2bpp rendering
    img2 = render_tilesheet(bank_data, bpp=2, palette=default_palette[:4], max_tiles=512)
    if img2:
        img2.save(OUT / f"raw_2bpp_{bank_label}.png")
        print(f"  {bank_label}: 2bpp -> {img2.size}")

# === Step 2: Try LZSS decompression on data banks ===
print("\n" + "=" * 60)
print("Step 2: Trying LZSS decompression")
print("=" * 60)

best_results = []
for start, end in data_banks:
    # Try decompression at various offsets within the bank
    for try_offset in range(0, min(end - start, 0x8000), 0x1000):
        abs_offset = start + try_offset
        decompressed = try_lzss_decompress(rom, abs_offset, max_out=32768)
        
        if len(decompressed) > 256:
            # Check if decompressed data looks like tile data
            # (varied byte values, not all same)
            unique = len(set(decompressed[:256]))
            if unique > 10:
                bank_label = f"0x{abs_offset:06X}"
                img = render_tilesheet(decompressed, bpp=4, palette=default_palette, max_tiles=256)
                if img:
                    fname = f"lzss_4bpp_{bank_label}.png"
                    img.save(OUT / fname)
                    best_results.append({
                        'offset': abs_offset,
                        'decompressed_size': len(decompressed),
                        'unique_bytes': unique,
                        'file': fname
                    })
                    if len(best_results) <= 20:
                        print(f"  {bank_label}: {len(decompressed)} bytes, {unique} unique -> {fname}")

# === Step 3: Try RLE decompression ===
print("\n" + "=" * 60)
print("Step 3: Trying RLE decompression")
print("=" * 60)

rle_results = []
for start, end in data_banks:
    for try_offset in range(0, min(end - start, 0x8000), 0x2000):
        abs_offset = start + try_offset
        decompressed = try_rle_decompress(rom, abs_offset, max_out=32768)
        
        if len(decompressed) > 256:
            unique = len(set(decompressed[:256]))
            if unique > 10:
                bank_label = f"0x{abs_offset:06X}"
                img = render_tilesheet(decompressed, bpp=4, palette=default_palette, max_tiles=256)
                if img:
                    fname = f"rle_4bpp_{bank_label}.png"
                    img.save(OUT / fname)
                    rle_results.append({
                        'offset': abs_offset,
                        'decompressed_size': len(decompressed),
                        'unique_bytes': unique,
                        'file': fname
                    })
                    if len(rle_results) <= 10:
                        print(f"  {bank_label}: {len(decompressed)} bytes, {unique} unique -> {fname}")

# === Step 4: Scan for known SNES graphics signatures ===
print("\n" + "=" * 60)
print("Step 4: Scanning for graphics patterns")
print("=" * 60)

# Look for sequences that look like SNES 4bpp tile data
# 4bpp tiles have a characteristic pattern: 32-byte blocks with
# interleaved bitplanes
tile_sequences = []
scan_start = 0x0E0000  # Start of high-entropy region
scan_end = min(0x2C0000, len(rom))

for offset in range(scan_start, scan_end - 32, 32):
    # Check if this 32-byte block looks like a valid tile
    block = rom[offset:offset + 32]
    
    # Heuristic: not all zeros, not all same byte, reasonable value range
    if all(b == 0 for b in block):
        continue
    if all(b == block[0] for b in block):
        continue
    
    # Check if it could be a tile (bytes in 0x00-0xFF range, some structure)
    non_zero = sum(1 for b in block if b != 0)
    if non_zero > 4:  # At least 5 non-zero bytes
        tile_sequences.append(offset)

# Group consecutive tiles
if tile_sequences:
    groups = []
    group_start = tile_sequences[0]
    group_end = tile_sequences[0]
    
    for offset in tile_sequences[1:]:
        if offset == group_end + 32:
            group_end = offset
        else:
            tile_count = (group_end - group_start) // 32 + 1
            if tile_count >= 16:  # At least 16 consecutive tiles
                groups.append((group_start, group_end + 32, tile_count))
            group_start = offset
            group_end = offset
    
    tile_count = (group_end - group_start) // 32 + 1
    if tile_count >= 16:
        groups.append((group_start, group_end + 32, tile_count))
    
    print(f"Found {len(groups)} tile data regions (>= 16 consecutive tiles):")
    for gs, ge, tc in groups[:20]:
        print(f"  0x{gs:06X}-0x{ge:06X}: {tc} tiles ({(ge-gs)//1024} KB)")
        # Render these tiles
        tile_data = rom[gs:ge]
        img = render_tilesheet(tile_data, bpp=4, palette=default_palette, max_tiles=512)
        if img:
            fname = f"tiles_0x{gs:06X}.png"
            img.save(OUT / fname)
    
    if len(groups) > 20:
        print(f"  ... and {len(groups) - 20} more regions")

# === Summary ===
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"  Raw tile sheets: {len(list(OUT.glob('raw_*.png')))}")
print(f"  LZSS decompressed: {len(best_results)}")
print(f"  RLE decompressed: {len(rle_results)}")
print(f"  Tile regions found: {len(groups) if tile_sequences else 0}")
print(f"  Total PNGs: {len(list(OUT.glob('*.png')))}")
print(f"  Output: {OUT}")
