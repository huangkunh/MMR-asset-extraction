#!/usr/bin/env python3
"""
VRAM瓦片全彩渲染工具
将VRAM转储中的4bpp瓦片用CGRAM调色板渲染为全彩PNG
"""
import os
import sys
import struct
import json
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    os.system(f"{sys.executable} -m pip install Pillow --break-system-packages -q")
    from PIL import Image

# VRAM转储目录（按场景）
SCENE_DIRS = [
    "full_extract",
    "town_interior",
    "battle_vram",
    "menu_system",
    "wm_menu",
]

REPO_DIR = "/workspace/MMR-asset-extraction"
OUT_DIR = "/data/user/work/vram_color"
os.makedirs(OUT_DIR, exist_ok=True)

ROM_PATH = "/workspace/.uploads/db23ff94-7eea-4a72-b2d6-9e125cf021b5_MMR.smc"

def read_cgram(cgram_path):
    """读取CGRAM (512字节 = 256色 x 2字节, BGR555格式)"""
    with open(cgram_path, "rb") as f:
        data = f.read()
    
    colors = []
    for i in range(0, min(len(data), 512), 2):
        if i + 1 >= len(data):
            break
        val = struct.unpack_from('<H', data, i)[0]
        # SNES BGR555: bbbbb ggggg rrrrr
        r = (val & 0x1F) << 3 | (val & 0x1F) >> 2
        g = ((val >> 5) & 0x1F) << 3 | ((val >> 5) & 0x1F) >> 2
        b = ((val >> 10) & 0x1F) << 3 | ((val >> 10) & 0x1F) >> 2
        colors.append((r, g, b))
    
    return colors

def decode_4bpp_tile(vram_data, tile_index):
    """解码4bpp 8x8瓦片 (32字节)"""
    offset = tile_index * 32
    if offset + 32 > len(vram_data):
        return None
    
    tile = [[0] * 8 for _ in range(8)]
    
    # 4bpp: 4个bitplane, 每个plane 8字节 (2字节/行 x 4行 = 8行)
    # Plane 0-1: bytes 0-15 (interleaved)
    # Plane 2-3: bytes 16-31 (interleaved)
    for row in range(8):
        bp0 = vram_data[offset + row * 2]
        bp1 = vram_data[offset + row * 2 + 1]
        bp2 = vram_data[offset + 16 + row * 2]
        bp3 = vram_data[offset + 16 + row * 2 + 1]
        
        for col in range(8):
            bit = 7 - col
            pixel = ((bp0 >> bit) & 1) | (((bp1 >> bit) & 1) << 1) | \
                    (((bp2 >> bit) & 1) << 2) | (((bp3 >> bit) & 1) << 3)
            tile[row][col] = pixel
    
    return tile

def decode_2bpp_tile(vram_data, tile_index):
    """解码2bpp 8x8瓦片 (16字节)"""
    offset = tile_index * 16
    if offset + 16 > len(vram_data):
        return None
    
    tile = [[0] * 8 for _ in range(8)]
    for row in range(8):
        bp0 = vram_data[offset + row * 2]
        bp1 = vram_data[offset + row * 2 + 1]
        for col in range(8):
            bit = 7 - col
            pixel = ((bp0 >> bit) & 1) | (((bp1 >> bit) & 1) << 1)
            tile[row][col] = pixel
    
    return tile

def render_tile_sheet(tiles, palette, cols=16, scale=2):
    """渲染瓦片表为PNG"""
    if not tiles:
        return None
    
    num_tiles = len(tiles)
    rows = (num_tiles + cols - 1) // cols
    
    img_w = cols * 8 * scale
    img_h = rows * 8 * scale
    
    img = Image.new('RGB', (img_w, img_h), (0, 0, 0))
    pixels = img.load()
    
    for i, tile in enumerate(tiles):
        tx = (i % cols) * 8 * scale
        ty = (i // cols) * 8 * scale
        
        for row in range(8):
            for col in range(8):
                if tile is None:
                    continue
                color_idx = tile[row][col]
                # 调色板: 每组16色, color_idx 0-15
                pal_idx = color_idx & 0x0F
                if pal_idx < len(palette):
                    color = palette[pal_idx]
                else:
                    color = (0, 0, 0)
                
                for sy in range(scale):
                    for sx in range(scale):
                        px = tx + col * scale + sx
                        py = ty + row * scale + sy
                        if px < img_w and py < img_h:
                            pixels[px, py] = color
    
    return img

def render_full_scene(vram_data, palette, cols=16, scale=2, max_tiles=256):
    """渲染VRAM中的所有瓦片"""
    tiles = []
    num_possible = min(len(vram_data) // 32, max_tiles)
    
    for i in range(num_possible):
        tile = decode_4bpp_tile(vram_data, i)
        tiles.append(tile)
    
    return render_tile_sheet(tiles, palette, cols, scale)

def find_scene_files(scene_dir):
    """在场景目录中查找VRAM和CGRAM文件"""
    vram_files = []
    cgram_files = []
    
    for root, dirs, files in os.walk(scene_dir):
        for f in files:
            fpath = os.path.join(root, f)
            if f.endswith('_vram.bin') or f.endswith('_vram_4bpp.bin'):
                vram_files.append(fpath)
            elif f.endswith('_cg.bin') or f.endswith('_cgram.bin'):
                cgram_files.append(fpath)
    
    return vram_files, cgram_files

def match_vram_cgram(vram_files, cgram_files):
    """匹配VRAM和CGRAM文件（按场景标签）"""
    pairs = []
    
    for vf in vram_files:
        # 提取场景标签
        vname = os.path.basename(vf)
        # 尝试匹配同场景的CGRAM
        best_cg = None
        best_score = 0
        
        for cf in cgram_files:
            cname = os.path.basename(cf)
            # 简单的字符串匹配
            vparts = vname.replace('_vram.bin', '').replace('_vram_4bpp.bin', '')
            cparts = cname.replace('_cg.bin', '').replace('_cgram.bin', '')
            
            # 计算共同前缀
            common = 0
            for a, b in zip(vparts, cparts):
                if a == b:
                    common += 1
                else:
                    break
            
            if common > best_score:
                best_score = common
                best_cg = cf
        
        if best_cg:
            pairs.append((vf, best_cg))
    
    return pairs

def render_vram_region(vram_data, palette, start_tile, num_tiles, region_name, out_path, cols=16, scale=2):
    """渲染VRAM特定区域的瓦片"""
    tiles = []
    for i in range(start_tile, start_tile + num_tiles):
        tile = decode_4bpp_tile(vram_data, i)
        tiles.append(tile)
    
    img = render_tile_sheet(tiles, palette, cols, scale)
    if img:
        img.save(out_path)
        return True
    return False

def render_screen_from_tilemap(vram_data, cgram_data, tilemap_offset, bg_w=32, bg_h=32):
    """
    从VRAM中的tilemap数据渲染屏幕
    SNES tilemap条目: 2字节/entry
    bit 0-9: tile index, bit 10: Y flip, bit 11: X flip, 
    bit 12-13: priority, bit 14-15: palette group
    """
    colors = read_cgram_from_bytes(cgram_data)
    
    img = Image.new('RGB', (bg_w * 8, bg_h * 8), (0, 0, 0))
    pixels = img.load()
    
    for row in range(bg_h):
        for col in range(bg_w):
            entry_off = tilemap_offset + (row * bg_w + col) * 2
            if entry_off + 2 > len(vram_data):
                continue
            
            entry = struct.unpack_from('<H', vram_data, entry_off)[0]
            tile_idx = entry & 0x03FF
            x_flip = (entry >> 10) & 1
            y_flip = (entry >> 11) & 1
            pal_group = (entry >> 12) & 0x03  # 通常0-7, 对应palette offset
            
            tile = decode_4bpp_tile(vram_data, tile_idx)
            if tile is None:
                continue
            
            # 调色板偏移: 每组16色
            pal_offset = pal_group * 16
            
            for ty in range(8):
                for tx in range(8):
                    src_y = (7 - ty) if y_flip else ty
                    src_x = (7 - tx) if x_flip else tx
                    color_idx = tile[src_y][src_x]
                    pal_idx = pal_offset + (color_idx & 0x0F)
                    
                    if pal_idx < len(colors):
                        color = colors[pal_idx]
                    else:
                        color = (0, 0, 0)
                    
                    px = col * 8 + tx
                    py = row * 8 + ty
                    if px < bg_w * 8 and py < bg_h * 8:
                        pixels[px, py] = color
    
    return img

def read_cgram_from_bytes(data):
    """从字节数据读取CGRAM颜色"""
    colors = []
    for i in range(0, min(len(data), 512), 2):
        if i + 1 >= len(data):
            break
        val = struct.unpack_from('<H', data, i)[0]
        r = (val & 0x1F) << 3 | (val & 0x1F) >> 2
        g = ((val >> 5) & 0x1F) << 3 | ((val >> 5) & 0x1F) >> 2
        b = ((val >> 10) & 0x1F) << 3 | ((val >> 10) & 0x1F) >> 2
        colors.append((r, g, b))
    return colors

def main():
    print("=== VRAM瓦片全彩渲染工具 ===")
    
    all_rendered = 0
    scenes_processed = []
    
    for scene_name in SCENE_DIRS:
        scene_dir = os.path.join(REPO_DIR, scene_name)
        if not os.path.isdir(scene_dir):
            print(f"  跳过 {scene_name} (目录不存在)")
            continue
        
        vram_files, cgram_files = find_scene_files(scene_dir)
        
        if not vram_files:
            print(f"  跳过 {scene_name} (无VRAM文件)")
            continue
        
        if not cgram_files:
            print(f"  跳过 {scene_name} (无CGRAM文件)")
            continue
        
        pairs = match_vram_cgram(vram_files, cgram_files)
        print(f"  {scene_name}: {len(vram_files)} VRAM, {len(cgram_files)} CGRAM, {len(pairs)} 配对")
        
        scene_out = os.path.join(OUT_DIR, scene_name)
        os.makedirs(scene_out, exist_ok=True)
        
        scene_count = 0
        for vf, cf in pairs[:10]:  # 每个场景最多处理10个配对
            try:
                with open(vf, "rb") as f:
                    vram = f.read()
                with open(cf, "rb") as f:
                    cgram = f.read()
                
                palette = read_cgram_from_bytes(cgram)
                
                # 提取标签
                tag = os.path.basename(vf).replace('_vram.bin', '').replace('_vram_4bpp.bin', '')
                
                # 渲染全部瓦片 (4bpp, 从0x4000开始 = tile 512)
                # 动态瓦片区域: 0x4000-0x7FFF = 512 tiles
                for region_name, start, count in [
                    ("dyn_tiles", 0x4000 // 32, 512),  # 0x4000-0x7FFF
                    ("static_tiles_lo", 0x8000 // 32, 512),  # 0x8000-0xBFFF
                    ("static_tiles_hi", 0xC000 // 32, 512),  # 0xC000-0xFFFF
                ]:
                    if start * 32 + 32 > len(vram):
                        continue
                    
                    actual_count = min(count, (len(vram) - start * 32) // 32)
                    if actual_count < 1:
                        continue
                    
                    # 使用不同调色板组渲染
                    for pal_group in range(8):
                        pal_offset = pal_group * 16
                        if pal_offset + 16 > len(palette):
                            break
                        
                        sub_palette = palette[pal_offset:pal_offset + 16]
                        
                        # 检查调色板是否非空（不是全黑）
                        if all(c == (0, 0, 0) for c in sub_palette[:1]):
                            continue
                        
                        tiles = []
                        for i in range(start, start + actual_count):
                            tile = decode_4bpp_tile(vram, i)
                            tiles.append(tile)
                        
                        img = render_tile_sheet(tiles, sub_palette, cols=16, scale=2)
                        if img:
                            fname = f"{tag}_{region_name}_pal{pal_group}.png"
                            img.save(os.path.join(scene_out, fname))
                            scene_count += 1
                            all_rendered += 1
                
                # 渲染tilemap屏幕 (BG1: 0x0000, BG2: 0x0800, BG3: 0x1000)
                for bg_name, tm_off in [("BG1", 0x0000), ("BG2", 0x0800), ("BG3", 0x1000)]:
                    if tm_off + 32 * 32 * 2 > len(vram):
                        continue
                    
                    for pal_group in [0, 1, 2, 3]:
                        # 创建使用特定调色板组的渲染
                        screen_img = render_screen_from_tilemap(vram, cgram, tm_off, 32, 32)
                        if screen_img:
                            fname = f"{tag}_{bg_name}_screen.png"
                            screen_img.save(os.path.join(scene_out, fname))
                            scene_count += 1
                            all_rendered += 1
                            break  # 每个BG只渲染一次（使用默认调色板）
                
            except Exception as e:
                print(f"    错误 {vf}: {e}")
        
        scenes_processed.append((scene_name, scene_count))
        print(f"    渲染 {scene_count} 张PNG")
    
    print(f"\n总计渲染: {all_rendered} 张全彩PNG")
    print(f"处理的场景: {len(scenes_processed)}")
    for name, count in scenes_processed:
        print(f"  {name}: {count} 张")
    
    # 保存汇总报告
    with open(os.path.join(OUT_DIR, "render_report.txt"), "w") as f:
        f.write("=== VRAM瓦片全彩渲染报告 ===\n\n")
        f.write(f"总计渲染: {all_rendered} 张PNG\n\n")
        for name, count in scenes_processed:
            f.write(f"{name}: {count} 张\n")
    
    print(f"\n报告已保存到 {OUT_DIR}/render_report.txt")

if __name__ == "__main__":
    main()
