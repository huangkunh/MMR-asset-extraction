#!/usr/bin/env python3
"""
ROM数据表提取工具
扫描ROM数据bank中的结构化数据表：敌人属性、道具数据、装备数据等
"""
import struct
import os
import json
import sys

ROM_PATH = "/workspace/.uploads/db23ff94-7eea-4a72-b2d6-9e125cf021b5_MMR.smc"
OUT_DIR = "/data/user/work/rom_tables"
os.makedirs(OUT_DIR, exist_ok=True)

# 数据bank范围（从之前的熵分析得知）
DATA_BANKS = list(range(0x04, 0x10)) + list(range(0x14, 0x18)) + list(range(0x1C, 0x20)) + \
             list(range(0x24, 0x28)) + list(range(0x2C, 0x30)) + list(range(0x38, 0x3A))

def read_rom():
    with open(ROM_PATH, "rb") as f:
        return f.read()

def bank_to_offset(bank, addr_in_bank=None):
    """LoROM: bank * 0x8000 + (addr & 0x7FFF) for $8000-$FFFF"""
    return bank * 0x8000

def find_repeated_records(rom, start, end, min_recs=4, max_rec_len=64):
    """
    在ROM数据中查找重复记录结构
    返回: list of (offset, record_len, num_records, score)
    """
    results = []
    
    for rec_len in range(4, max_rec_len + 1):
        # 在范围内每隔rec_len字节检查模式重复
        for base in range(start, end - rec_len * min_recs, rec_len):
            if base + rec_len * min_recs > end:
                break
            
            # 取第一条记录
            rec0 = rom[base:base+rec_len]
            
            # 检查后续记录的相似度
            matches = 0
            total_diff = 0
            for i in range(1, min_recs + 2):  # 检查多一条确认
                off = base + i * rec_len
                if off + rec_len > len(rom):
                    break
                rec_n = rom[off:off+rec_len]
                
                # 计算字节级相似度
                same_pos = sum(1 for a, b in zip(rec0, rec_n) if a == b)
                similarity = same_pos / rec_len
                
                if similarity > 0.3:  # 30%以上相似度认为是同类型记录
                    matches += 1
                    total_diff += (rec_len - same_pos)
                else:
                    break
            
            if matches >= min_recs:
                # 扩展检查，看有多少连续记录
                total_recs = matches + 1
                for i in range(matches + 1, 200):
                    off = base + i * rec_len
                    if off + rec_len > len(rom):
                        break
                    rec_n = rom[off:off+rec_len]
                    same_pos = sum(1 for a, b in zip(rec0, rec_n) if a == b)
                    if same_pos / rec_len > 0.3:
                        total_recs += 1
                    else:
                        break
                
                avg_diff = total_diff / matches if matches > 0 else 0
                score = total_recs * (1 - avg_diff / rec_len)
                
                results.append({
                    'offset': base,
                    'rec_len': rec_len,
                    'num_recs': total_recs,
                    'score': score,
                    'avg_similarity': 1 - avg_diff / rec_len,
                    'sample': rec0[:16].hex()
                })
    
    # 去重：同offset只保留最高分的
    best_by_offset = {}
    for r in results:
        off = r['offset']
        if off not in best_by_offset or r['score'] > best_by_offset[off]['score']:
            best_by_offset[off] = r
    
    return sorted(best_by_offset.values(), key=lambda x: x['score'], reverse=True)

def find_pointer_tables(rom, start, end, min_ptrs=4):
    """
    查找指针表（LoROM地址指针）
    LoROM指针格式: 2字节 little-endian, bank隐含或跟随
    """
    results = []
    
    for base in range(start, end - min_ptrs * 2, 2):
        # 读取连续指针
        ptrs = []
        valid = True
        for i in range(min_ptrs):
            off = base + i * 2
            if off + 2 > len(rom):
                valid = False
                break
            ptr = struct.unpack_from('<H', rom, off)[0]
            # LoROM地址范围: $8000-$FFFF
            if ptr < 0x8000 or ptr > 0xFFFF:
                valid = False
                break
            ptrs.append(ptr)
        
        if not valid:
            continue
        
        # 检查指针是否指向不同地址（如果是数据表，指针应该分散）
        unique_ptrs = len(set(ptrs))
        if unique_ptrs < min_ptrs // 2:
            continue
        
        # 扩展检查
        total_ptrs = len(ptrs)
        for i in range(min_ptrs, 100):
            off = base + i * 2
            if off + 2 > len(rom):
                break
            ptr = struct.unpack_from('<H', rom, off)[0]
            if ptr < 0x8000 or ptr > 0xFFFF:
                break
            total_ptrs += 1
            ptrs.append(ptr)
        
        # 检查是否有对应的bank字节（3字节指针）
        bank_byte = rom[base + total_ptrs * 2] if base + total_ptrs * 2 < len(rom) else 0
        
        results.append({
            'offset': base,
            'num_ptrs': total_ptrs,
            'unique_ptrs': len(set(ptrs)),
            'ptr_range': (min(ptrs), max(ptrs)),
            'bank_hint': bank_byte,
            'first_ptrs': [hex(p) for p in ptrs[:8]]
        })
    
    return results

def find_string_tables(rom, start, end):
    """
    查找字符串表（游戏文本数据）
    SJIS编码的日文文本通常以特定字节开头
    """
    results = []
    
    # Metal Max Returns使用SJIS编码
    # 日文文本通常包含0x82xx (ひらがな), 0x83xx (カタカナ) 等范围
    i = start
    while i < end - 4:
        # 检查是否是文本起始
        b0 = rom[i]
        b1 = rom[i + 1] if i + 1 < len(rom) else 0
        
        is_text = False
        text_len = 0
        
        # SJIS日文文本检测
        if b0 >= 0x81 and b0 <= 0x9F or b0 >= 0xE0 and b0 <= 0xEF:
            # 可能是SJIS双字节字符
            if (b1 >= 0x40 and b1 <= 0xFC and b1 != 0x7F):
                is_text = True
        elif b0 >= 0x82 and b0 <= 0x83:
            if b1 >= 0x40 and b1 <= 0xFC and b1 != 0x7F:
                is_text = True
        
        if not is_text:
            i += 1
            continue
        
        # 尝试解码字符串
        text_start = i
        text_bytes = []
        while i < end and i < len(rom):
            b = rom[i]
            if b == 0x00:  # null终止
                break
            if b >= 0x81 and b <= 0x9F or b >= 0xE0 and b <= 0xEF:
                if i + 1 < len(rom):
                    text_bytes.append(rom[i])
                    text_bytes.append(rom[i+1])
                    i += 2
                    text_len += 1
                else:
                    break
            elif b >= 0x20 and b <= 0x7E:  # ASCII
                text_bytes.append(b)
                i += 1
                text_len += 1
            elif b >= 0xA0 and b <= 0xDF:  # 半角カタカナ
                text_bytes.append(b)
                i += 1
                text_len += 1
            else:
                break
        
        if text_len >= 3:
            try:
                text = bytes(text_bytes).decode('sjis', errors='replace')
                if len(text) >= 3 and any(ord(c) > 0x80 for c in text):
                    results.append({
                        'offset': text_start,
                        'length': i - text_start,
                        'text': text[:60]
                    })
            except:
                pass
        
        i += 1
    
    return results

def find_numeric_tables(rom, start, end, min_recs=8):
    """
    查找数值数据表（属性值、等级表等）
    特征：大量小数值(0-255)组成的连续区域
    """
    results = []
    
    for base in range(start, end - min_recs, 1):
        # 检查连续16字节的值范围
        if base + 16 > len(rom):
            break
        
        vals = rom[base:base+16]
        
        # 数值表特征：大部分值在0-100之间（属性值范围）
        small_vals = sum(1 for v in vals if v <= 100)
        zero_vals = sum(1 for v in vals if v == 0)
        
        if small_vals >= 12 and zero_vals <= 8:
            # 扩展检查
            ext_len = 16
            for j in range(16, 256):
                if base + j >= len(rom):
                    break
                v = rom[base + j]
                if v <= 100:
                    ext_len += 1
                else:
                    break
            
            if ext_len >= min_recs:
                results.append({
                    'offset': base,
                    'length': ext_len,
                    'sample': vals.hex()
                })
    
    # 去重重叠区域
    filtered = []
    last_end = 0
    for r in sorted(results, key=lambda x: x['offset']):
        if r['offset'] >= last_end:
            filtered.append(r)
            last_end = r['offset'] + r['length']
    
    return filtered

def extract_enemy_data(rom, candidates):
    """
    从候选数据表中提取可能的敌人属性数据
    SNES RPG敌人数据通常包含：HP, 攻击力, 防御力, 速度, 经验值, 金币等
    """
    enemy_tables = []
    
    for c in candidates:
        off = c['offset']
        rec_len = c['rec_len']
        num = min(c['num_recs'], 50)  # 限制数量
        
        # 读取记录
        records = []
        for i in range(num):
            rec_start = off + i * rec_len
            if rec_start + rec_len > len(rom):
                break
            rec = rom[rec_start:rec_start + rec_len]
            records.append(rec)
        
        # 分析记录特征
        if len(records) < 4:
            continue
        
        # 检查是否有16位值（HP/经验值等）
        has_16bit = False
        for rec in records[:5]:
            for j in range(0, len(rec) - 1, 2):
                val16 = struct.unpack_from('<H', rec, j)[0]
                if val16 > 100 and val16 < 30000:
                    has_16bit = True
                    break
        
        # 检查值范围合理性
        byte_ranges = []
        for j in range(rec_len):
            vals = [r[j] for r in records if j < len(r)]
            if vals:
                byte_ranges.append((min(vals), max(vals), sum(vals) / len(vals)))
        
        enemy_tables.append({
            'offset': hex(off),
            'bank': off >> 15,
            'rec_len': rec_len,
            'num_recs': num,
            'has_16bit_values': has_16bit,
            'byte_ranges': [(r[0], r[1], round(r[2], 1)) for r in byte_ranges],
            'first_record_hex': records[0].hex() if records else '',
            'second_record_hex': records[1].hex() if len(records) > 1 else '',
            'third_record_hex': records[2].hex() if len(records) > 2 else '',
        })
    
    return enemy_tables

def main():
    print("=== ROM数据表提取工具 ===")
    rom = read_rom()
    print(f"ROM大小: {len(rom)} bytes ({len(rom)/1024:.0f}KB)")
    
    all_tables = []
    all_ptrs = []
    all_strings = []
    all_numerics = []
    
    # 只扫描前几个数据bank来避免过多结果
    scan_banks = DATA_BANKS[:8]
    print(f"扫描 {len(scan_banks)} 个数据bank...")
    
    for bank in scan_banks:
        bank_off = bank_to_offset(bank)
        bank_end = bank_off + 0x8000
        if bank_end > len(rom):
            bank_end = len(rom)
        
        print(f"  Bank ${bank:02X} (offset 0x{bank_off:06X}-0x{bank_end:06X})...")
        
        # 1. 查找重复记录结构
        tables = find_repeated_records(rom, bank_off, bank_end, min_recs=4, max_rec_len=48)
        # 只保留高分的
        tables = [t for t in tables if t['score'] > 3.0 and t['num_recs'] >= 5]
        all_tables.extend(tables)
        
        # 2. 查找指针表
        ptrs = find_pointer_tables(rom, bank_off, bank_end, min_ptrs=6)
        ptrs = [p for p in ptrs if p['num_ptrs'] >= 8]
        all_ptrs.extend(ptrs)
        
        # 3. 查找字符串表
        strings = find_string_tables(rom, bank_off, bank_end)
        strings = [s for s in strings if s['length'] >= 5]
        all_strings.extend(strings)
        
        # 4. 查找数值表
        numerics = find_numeric_tables(rom, bank_off, bank_end, min_recs=16)
        all_numerics.extend(numerics)
    
    print(f"\n找到 {len(all_tables)} 个重复记录表")
    print(f"找到 {len(all_ptrs)} 个指针表")
    print(f"找到 {len(all_strings)} 个字符串")
    print(f"找到 {len(all_numerics)} 个数值表")
    
    # 提取可能的敌人数据表
    enemy_candidates = [t for t in all_tables if t['rec_len'] >= 8 and t['rec_len'] <= 32]
    enemy_data = extract_enemy_data(rom, enemy_candidates[:50])
    print(f"可能的敌人/角色数据表: {len(enemy_data)}")
    
    # 保存结果
    report = {
        'summary': {
            'rom_size': len(rom),
            'banks_scanned': len(scan_banks),
            'repeated_record_tables': len(all_tables),
            'pointer_tables': len(all_ptrs),
            'string_entries': len(all_strings),
            'numeric_tables': len(all_numerics),
            'potential_enemy_tables': len(enemy_data),
        },
        'repeated_record_tables': sorted(all_tables, key=lambda x: x['score'], reverse=True)[:30],
        'pointer_tables': sorted(all_ptrs, key=lambda x: x['num_ptrs'], reverse=True)[:30],
        'enemy_data_candidates': enemy_data[:20],
        'numeric_tables': all_numerics[:30],
    }
    
    # 保存字符串到文本文件
    with open(os.path.join(OUT_DIR, "rom_strings.txt"), "w", encoding='utf-8') as f:
        f.write("=== ROM数据Bank字符串提取 ===\n\n")
        for s in all_strings:
            f.write(f"0x{s['offset']:06X} [{s['length']:3d}B] {s['text']}\n")
    
    # 保存JSON报告
    with open(os.path.join(OUT_DIR, "rom_tables_report.json"), "w", encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    
    # 保存人类可读报告
    with open(os.path.join(OUT_DIR, "rom_tables_report.txt"), "w", encoding='utf-8') as f:
        f.write("=== ROM数据表提取报告 ===\n\n")
        f.write(f"ROM大小: {len(rom)} bytes\n")
        f.write(f"扫描bank数: {len(scan_banks)}\n\n")
        
        f.write(f"--- 重复记录表 (Top 20) ---\n")
        f.write(f"{'Offset':>10} {'Len':>4} {'Recs':>5} {'Score':>6} {'Sim':>5} {'Sample':>20}\n")
        for t in sorted(all_tables, key=lambda x: x['score'], reverse=True)[:20]:
            f.write(f"0x{t['offset']:06X}   {t['rec_len']:3d}  {t['num_recs']:4d}  {t['score']:5.1f}  {t['avg_similarity']:.2f}  {t['sample']}\n")
        
        f.write(f"\n--- 指针表 (Top 20) ---\n")
        f.write(f"{'Offset':>10} {'Ptrs':>5} {'Unique':>7} {'Range':>20} {'First ptrs':>40}\n")
        for p in sorted(all_ptrs, key=lambda x: x['num_ptrs'], reverse=True)[:20]:
            f.write(f"0x{p['offset']:06X}   {p['num_ptrs']:4d}  {p['unique_ptrs']:5d}    ${p['ptr_range'][0]:04X}-${p['ptr_range'][1]:04X}  {' '.join(p['first_ptrs'][:4])}\n")
        
        f.write(f"\n--- 可能的敌人/角色数据表 ---\n")
        for e in enemy_data[:15]:
            f.write(f"\nOffset: {e['offset']} (Bank ${e['bank']:02X})\n")
            f.write(f"  记录长度: {e['rec_len']}B, 记录数: {e['num_recs']}, 含16位值: {e['has_16bit_values']}\n")
            f.write(f"  字节范围: {e['byte_ranges'][:8]}\n")
            f.write(f"  Record 0: {e['first_record_hex']}\n")
            f.write(f"  Record 1: {e['second_record_hex']}\n")
            f.write(f"  Record 2: {e['third_record_hex']}\n")
        
        f.write(f"\n--- 数值数据表 (Top 20) ---\n")
        f.write(f"{'Offset':>10} {'Length':>6} {'Sample':>40}\n")
        for n in all_numerics[:20]:
            f.write(f"0x{n['offset']:06X}   {n['length']:4d}   {n['sample']}\n")
        
        f.write(f"\n--- 字符串 (Top 50) ---\n")
        for s in all_strings[:50]:
            f.write(f"0x{s['offset']:06X} [{s['length']:3d}B] {s['text']}\n")
    
    print(f"\n报告已保存到 {OUT_DIR}/")
    print(f"  rom_tables_report.txt")
    print(f"  rom_tables_report.json")
    print(f"  rom_strings.txt")

if __name__ == "__main__":
    main()
