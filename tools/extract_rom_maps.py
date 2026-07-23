#!/usr/bin/env python3
"""
ROM地图/Tilemap数据提取
从ROM中提取游戏地图tilemap数据，与VRAM tilemap对比分析
"""
import struct
import os
import json
import sys

try:
    from PIL import Image
except ImportError:
    os.system(f"{sys.executable} -m pip install Pillow --break-system-packages -q")
    from PIL import Image

ROM_PATH = "/workspace/.uploads/db23ff94-7eea-4a72-b2d6-9e125cf021b5_MMR.smc"
REPO_DIR = "/workspace/MMR-asset-extraction"
OUT_DIR = "/data/user/work/rom_maps"
os.makedirs(OUT_DIR, exist_ok=True)

def read_rom():
    with open(ROM_PATH, "rb") as f:
        return f.read()

def read_vram_sample(vram_path):
    """读取VRAM转储作为对比基准"""
    with open(vram_path, "rb") as f:
        return f.read()

def find_tilemap_patterns(rom, bank_start, bank_end):
    """
    在ROM中查找tilemap模式
    SNES tilemap条目: 2字节, bit 0-9=tile index, bit 10-15=属性
    特征: 大量连续的2字节值，tile index < 1024
    """
    results = []

    # 扫描2KB对齐的区域 (一个标准SNES tilemap = 32x32 = 2048字节)
    for base in range(bank_start, bank_end - 2048, 2):
        # 检查是否是空区域
        sample = rom[base:base+32]
        if all(b == 0xFF for b in sample) or all(b == 0x00 for b in sample):
            continue

        # 读取前16个tilemap条目
        entries = []
        valid = True
        for i in range(16):
            off = base + i * 2
            if off + 2 > len(rom):
                valid = False
                break
            entry = struct.unpack_from('<H', rom, off)[0]
            tile_idx = entry & 0x03FF
            if tile_idx > 511:  # SNES 4bpp通常最多512个tile
                valid = False
                break
            entries.append(entry)

        if not valid or len(entries) < 16:
            continue

        # 检查tile index的多样性（真正的tilemap不会全用同一个tile）
        tile_indices = [e & 0x03FF for e in entries]
        unique_tiles = len(set(tile_indices))

        if unique_tiles < 3:
            continue

        # 检查属性位的合理性（palette 0-7, priority 0-3）
        pal_groups = set()
        for e in entries:
            pal = (e >> 12) & 0x03
            pal_groups.add(pal)

        # 扩展检查 - 看这个区域有多大的tilemap
        total_entries = 16
        for i in range(16, 1024):  # 最多32x32=1024
            off = base + i * 2
            if off + 2 > bank_end:
                break
            entry = struct.unpack_from('<H', rom, off)[0]
            tile_idx = entry & 0x03FF
            if tile_idx > 511:
                break
            total_entries += 1

        if total_entries >= 64:  # 至少8x8=64个条目
            # 计算tilemap尺寸
            if total_entries >= 1024:
                map_size = "32x32"
            elif total_entries >= 512:
                map_size = "32x16"
            elif total_entries >= 256:
                map_size = "16x16"
            elif total_entries >= 128:
                map_size = "16x8"
            else:
                map_size = f"{total_entries}entries"

            results.append({
                'offset': base,
                'bank': base >> 15,
                'entries': total_entries,
                'map_size': map_size,
                'unique_tiles': unique_tiles,
                'palette_groups': sorted(pal_groups),
                'first_entries': [hex(e) for e in entries[:8]],
                'size_bytes': total_entries * 2,
            })

    # 去重重叠
    filtered = []
    last_end = 0
    for r in sorted(results, key=lambda x: x['offset']):
        if r['offset'] >= last_end:
            filtered.append(r)
            last_end = r['offset'] + r['size_bytes']

    return filtered

def render_rom_tilemap(rom, offset, width=32, height=32, out_path=None):
    """渲染ROM中的tilemap为可视化PNG"""
    entries = []
    for i in range(width * height):
        off = offset + i * 2
        if off + 2 > len(rom):
            entries.append(0)
        else:
            entry = struct.unpack_from('<H', rom, off)[0]
            entries.append(entry)

    # 创建可视化图像（显示tile index分布）
    img = Image.new('RGB', (width * 4, height * 4), (0, 0, 0))
    pixels = img.load()

    for row in range(height):
        for col in range(width):
            entry = entries[row * width + col]
            tile_idx = entry & 0x03FF
            pal = (entry >> 12) & 0x03
            x_flip = (entry >> 10) & 1
            y_flip = (entry >> 11) & 1

            # 用颜色编码tile index
            r = (tile_idx * 7) & 0xFF
            g = (tile_idx * 13) & 0xFF
            b = (tile_idx * 29) & 0xFF

            # 调色板组用亮度调整
            brightness = 128 + pal * 32

            for py in range(4):
                for px in range(4):
                    pixels[col * 4 + px, row * 4 + py] = (
                        min(r, brightness),
                        min(g, brightness),
                        min(b, brightness)
                    )

    if out_path:
        img.save(out_path)
    return img

def find_map_data_blocks(rom):
    """
    查找地图数据块
    地图数据通常包含: tilemap + collision data + object data
    在数据bank中查找连续的大型数据块
    """
    data_banks = list(range(0x04, 0x10)) + list(range(0x14, 0x18)) + \
                 list(range(0x1C, 0x20)) + list(range(0x24, 0x28))

    blocks = []

    for bank in data_banks:
        bank_off = bank * 0x8000
        bank_end = min(bank_off + 0x8000, len(rom))

        # 查找非空数据块的边界
        block_start = None
        for addr in range(bank_off, bank_end):
            is_empty = (rom[addr] == 0xFF or rom[addr] == 0x00)
            # 检查是否是连续空区域
            if addr + 4 < bank_end:
                empty_run = all(rom[addr+i] in [0x00, 0xFF] for i in range(4))
            else:
                empty_run = False

            if not empty_run and block_start is None:
                block_start = addr
            elif empty_run and block_start is not None:
                block_size = addr - block_start
                if block_size >= 256:  # 至少256字节
                    blocks.append({
                        'offset': block_start,
                        'bank': bank,
                        'size': block_size,
                        'type': 'unknown',
                    })
                block_start = None

        if block_start is not None:
            block_size = bank_end - block_start
            if block_size >= 256:
                blocks.append({
                    'offset': block_start,
                    'bank': bank,
                    'size': block_size,
                    'type': 'unknown',
                })

    return blocks

def main():
    print("=== ROM地图/Tilemap数据提取 ===\n")
    rom = read_rom()
    print(f"ROM: {len(rom)} bytes\n")

    # 1. 在数据bank中查找tilemap模式
    print("扫描数据bank中的tilemap模式...")
    all_tilemaps = []

    scan_banks = list(range(0x04, 0x10)) + list(range(0x14, 0x18)) + \
                 list(range(0x1C, 0x20)) + list(range(0x24, 0x28)) + \
                 list(range(0x2C, 0x30))

    for bank in scan_banks:
        bank_off = bank * 0x8000
        bank_end = min(bank_off + 0x8000, len(rom))

        tilemaps = find_tilemap_patterns(rom, bank_off, bank_end)
        if tilemaps:
            print(f"  Bank ${bank:02X}: {len(tilemaps)} 个tilemap候选")
            all_tilemaps.extend(tilemaps)

    print(f"\n总计找到 {len(all_tilemaps)} 个tilemap候选区域")

    # 2. 查找大型数据块
    print("\n查找大型地图数据块...")
    data_blocks = find_map_data_blocks(rom)
    print(f"找到 {len(data_blocks)} 个数据块 (>=256B)")

    # 分类数据块
    large_blocks = [b for b in data_blocks if b['size'] >= 2048]
    medium_blocks = [b for b in data_blocks if 256 <= b['size'] < 2048]
    print(f"  大型块 (>=2KB): {len(large_blocks)}")
    print(f"  中型块 (256B-2KB): {len(medium_blocks)}")

    # 3. 渲染前20个tilemap
    print("\n渲染tilemap可视化...")
    rendered = 0
    for tm in all_tilemaps[:30]:
        out_path = os.path.join(OUT_DIR, f"tilemap_0x{tm['offset']:06X}_{tm['map_size']}.png")
        render_rom_tilemap(rom, tm['offset'], 32, min(32, tm['entries'] // 32), out_path)
        rendered += 1
    print(f"渲染了 {rendered} 张tilemap可视化")

    # 4. 与VRAM tilemap对比
    print("\n对比VRAM tilemap...")
    vram_files = []
    for dirpath, dirnames, filenames in os.walk(os.path.join(REPO_DIR, "town_interior")):
        for f in filenames:
            if f.endswith('_vram.bin'):
                vram_files.append(os.path.join(dirpath, f))

    if vram_files:
        vram = read_vram_sample(vram_files[0])
        # 提取VRAM中的BG1 tilemap (0x0000-0x07FF)
        vram_bg1 = []
        for i in range(0, 0x800, 2):
            entry = struct.unpack_from('<H', vram, i)[0]
            vram_bg1.append(entry & 0x03FF)

        vram_tile_set = set(vram_bg1)
        print(f"  VRAM BG1 tilemap: {len(vram_bg1)} entries, {len(vram_tile_set)} unique tiles")
        print(f"  Tile index range: {min(vram_tile_set)}-{max(vram_tile_set)}")

        # 查找ROM中与VRAM tilemap相似的区域
        best_match = None
        best_score = 0

        for tm in all_tilemaps[:50]:
            rom_tiles = []
            for i in range(min(256, tm['entries'])):
                off = tm['offset'] + i * 2
                if off + 2 <= len(rom):
                    entry = struct.unpack_from('<H', rom, off)[0]
                    rom_tiles.append(entry & 0x03FF)

            # 计算相似度（共同tile比例）
            rom_set = set(rom_tiles)
            if len(rom_set) == 0:
                continue
            overlap = len(vram_tile_set & rom_set)
            score = overlap / len(vram_tile_set | rom_set)

            if score > best_score:
                best_score = score
                best_match = tm

        if best_match:
            print(f"  最佳匹配: 0x{best_match['offset']:06X} (相似度: {best_score:.2%})")

    # 5. 保存报告
    report = {
        'summary': {
            'total_tilemaps': len(all_tilemaps),
            'total_data_blocks': len(data_blocks),
            'large_blocks': len(large_blocks),
            'medium_blocks': len(medium_blocks),
            'rendered_images': rendered,
        },
        'tilemaps': sorted(all_tilemaps, key=lambda x: x['entries'], reverse=True)[:50],
        'data_blocks': sorted(data_blocks, key=lambda x: x['size'], reverse=True)[:50],
    }

    with open(os.path.join(OUT_DIR, "rom_maps_report.json"), "w", encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    with open(os.path.join(OUT_DIR, "rom_maps_report.txt"), "w", encoding='utf-8') as f:
        f.write("=== ROM地图/Tilemap数据提取报告 ===\n\n")
        f.write(f"Tilemap候选区域: {len(all_tilemaps)}\n")
        f.write(f"数据块总数: {len(data_blocks)}\n")
        f.write(f"大型块 (>=2KB): {len(large_blocks)}\n")
        f.write(f"中型块 (256B-2KB): {len(medium_blocks)}\n\n")

        f.write("--- Tilemap候选 (Top 30) ---\n")
        f.write(f"{'Offset':>10} {'Bank':>5} {'Entries':>8} {'Size':>8} {'MapSize':>8} {'UniqueTiles':>12} {'Palettes':>10}\n")
        for tm in sorted(all_tilemaps, key=lambda x: x['entries'], reverse=True)[:30]:
            f.write(f"0x{tm['offset']:06X}  ${tm['bank']:02X}  {tm['entries']:6d}   {tm['size_bytes']:6d}B  {tm['map_size']:>8s}  {tm['unique_tiles']:10d}  {tm['palette_groups']}\n")

        f.write(f"\n--- 大型数据块 (Top 30, >=2KB) ---\n")
        f.write(f"{'Offset':>10} {'Bank':>5} {'Size':>10}\n")
        for b in sorted(large_blocks, key=lambda x: x['size'], reverse=True)[:30]:
            f.write(f"0x{b['offset']:06X}  ${b['bank']:02X}  {b['size']:8d}B ({b['size']/1024:.1f}KB)\n")

        f.write(f"\n--- Tilemap首条目样本 ---\n")
        for tm in all_tilemaps[:10]:
            f.write(f"0x{tm['offset']:06X}: {' '.join(tm['first_entries'])}\n")

    print(f"\n报告已保存到 {OUT_DIR}/")

if __name__ == "__main__":
    main()
