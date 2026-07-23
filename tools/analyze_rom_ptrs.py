#!/usr/bin/env python3
"""
深度分析ROM数据表 - 过滤空数据，深入指针表分析
"""
import struct
import os
import json

ROM_PATH = "/workspace/.uploads/db23ff94-7eea-4a72-b2d6-9e125cf021b5_MMR.smc"
OUT_DIR = "/data/user/work/rom_tables"

def read_rom():
    with open(ROM_PATH, "rb") as f:
        return f.read()

def is_empty_region(rom, offset, length):
    """检查是否是空数据区域(全0xFF或全0x00)"""
    sample = rom[offset:offset+min(length, 32)]
    if all(b == 0xFF for b in sample):
        return True
    if all(b == 0x00 for b in sample):
        return True
    return False

def analyze_pointer_table(rom, offset, num_ptrs):
    """深入分析指针表 - 跟踪指针指向的数据"""
    ptrs = []
    for i in range(num_ptrs):
        if offset + i * 2 + 2 > len(rom):
            break
        ptr = struct.unpack_from('<H', rom, offset + i * 2)[0]
        ptrs.append(ptr)
    
    # 假设bank = offset >> 15 (LoROM)
    bank = offset >> 15
    
    # 将LoROM地址转换为ROM偏移
    targets = []
    for ptr in ptrs:
        if ptr >= 0x8000:
            rom_off = bank * 0x8000 + (ptr & 0x7FFF)
            if rom_off < len(rom):
                # 读取目标处的数据
                target_data = rom[rom_off:rom_off+16]
                targets.append({
                    'ptr': hex(ptr),
                    'rom_offset': hex(rom_off),
                    'data': target_data.hex(),
                    'is_empty': is_empty_region(rom, rom_off, 16)
                })
    
    return ptrs, targets

def find_real_data_tables(rom, start_bank=0x04, end_bank=0x0C):
    """查找真实数据表（非空区域）"""
    tables = []
    
    for bank in range(start_bank, end_bank):
        bank_off = bank * 0x8000
        bank_end = min(bank_off + 0x8000, len(rom))
        
        # 扫描不同的记录长度
        for rec_len in [8, 12, 16, 20, 24, 28, 32]:
            for base in range(bank_off, bank_end - rec_len * 8, rec_len):
                if is_empty_region(rom, base, rec_len):
                    continue
                
                # 检查第一条记录
                rec0 = rom[base:base+rec_len]
                if all(b == 0xFF for b in rec0) or all(b == 0x00 for b in rec0):
                    continue
                
                # 检查连续记录
                matches = 0
                non_empty_recs = 0
                for i in range(1, 10):
                    off = base + i * rec_len
                    if off + rec_len > bank_end:
                        break
                    rec_n = rom[off:off+rec_len]
                    
                    # 跳过空记录
                    if all(b == 0xFF for b in rec_n) or all(b == 0x00 for b in rec_n):
                        continue
                    
                    non_empty_recs += 1
                    
                    # 相似度检查
                    same_pos = sum(1 for a, b in zip(rec0, rec_n) if a == b)
                    similarity = same_pos / rec_len
                    if similarity > 0.2:
                        matches += 1
                
                if matches >= 3 and non_empty_recs >= 4:
                    # 扩展
                    total = matches + 1
                    for i in range(10, 200):
                        off = base + i * rec_len
                        if off + rec_len > bank_end:
                            break
                        rec_n = rom[off:off+rec_len]
                        if all(b == 0xFF for b in rec_n) or all(b == 0x00 for b in rec_n):
                            break
                        same_pos = sum(1 for a, b in zip(rec0, rec_n) if a == b)
                        if same_pos / rec_len > 0.2:
                            total += 1
                        else:
                            break
                    
                    if total >= 5:
                        # 分析记录内容
                        records = []
                        for i in range(min(total, 10)):
                            off = base + i * rec_len
                            rec = rom[off:off+rec_len]
                            records.append(rec.hex())
                        
                        # 检查16位值
                        has_16bit = False
                        for rec_hex in records[:5]:
                            rec = bytes.fromhex(rec_hex)
                            for j in range(0, len(rec)-1, 2):
                                val = struct.unpack_from('<H', rec, j)[0]
                                if 100 < val < 60000:
                                    has_16bit = True
                                    break
                        
                        # 字节范围分析
                        byte_stats = []
                        for j in range(rec_len):
                            vals = []
                            for i in range(min(total, 20)):
                                off = base + i * rec_len
                                if off + j < len(rom):
                                    vals.append(rom[off + j])
                            if vals:
                                byte_stats.append({
                                    'byte': j,
                                    'min': min(vals),
                                    'max': max(vals),
                                    'avg': round(sum(vals)/len(vals), 1),
                                    'unique': len(set(vals))
                                })
                        
                        tables.append({
                            'offset': base,
                            'bank': bank,
                            'rec_len': rec_len,
                            'num_recs': total,
                            'has_16bit': has_16bit,
                            'records': records[:5],
                            'byte_stats': byte_stats,
                        })
    
    # 去重 - 同一offset只保留最大记录数的
    best = {}
    for t in tables:
        off = t['offset']
        if off not in best or t['num_recs'] > best[off]['num_recs']:
            best[off] = t
    
    return sorted(best.values(), key=lambda x: x['num_recs'], reverse=True)

def main():
    rom = read_rom()
    print(f"ROM: {len(rom)} bytes")
    
    # 1. 查找真实数据表
    print("查找真实数据表（过滤空数据）...")
    real_tables = find_real_data_tables(rom, 0x04, 0x0C)
    print(f"找到 {len(real_tables)} 个真实数据表")
    
    # 2. 深入分析指针表 0x029BE4
    print("\n分析指针表 @ 0x029BE4...")
    ptrs, targets = analyze_pointer_table(rom, 0x029BE4, 100)
    valid_targets = [t for t in targets if not t['is_empty']]
    print(f"  100个指针, {len(valid_targets)} 个指向非空数据")
    
    # 3. 分析指针表0x029BE4指向的数据
    # 跟踪前20个非空目标
    print(f"\n前20个非空目标:")
    for t in valid_targets[:20]:
        print(f"  ptr={t['ptr']} -> offset={t['rom_offset']} data={t['data']}")
    
    # 4. 扫描更多bank的指针表
    print("\n扫描所有数据bank的指针表...")
    all_ptr_tables = []
    for bank in range(0x04, 0x20):
        bank_off = bank * 0x8000
        bank_end = min(bank_off + 0x8000, len(rom))
        
        for base in range(bank_off, bank_end - 20, 2):
            if is_empty_region(rom, base, 20):
                continue
            
            # 读取前6个指针
            ptrs = []
            valid = True
            for i in range(6):
                if base + i * 2 + 2 > bank_end:
                    valid = False
                    break
                ptr = struct.unpack_from('<H', rom, base + i * 2)[0]
                if ptr < 0x8000 or ptr > 0xFFFF:
                    valid = False
                    break
                ptrs.append(ptr)
            
            if not valid:
                continue
            
            # 指针应该分散
            if len(set(ptrs)) < 3:
                continue
            
            # 扩展
            total = 6
            for i in range(6, 200):
                if base + i * 2 + 2 > bank_end:
                    break
                ptr = struct.unpack_from('<H', rom, base + i * 2)[0]
                if ptr < 0x8000 or ptr > 0xFFFF:
                    break
                total += 1
                ptrs.append(ptr)
            
            if total >= 8:
                # 检查指向的数据是否非空
                bank_for_ptrs = base >> 15
                non_empty = 0
                for ptr in ptrs[:10]:
                    rom_off = bank_for_ptrs * 0x8000 + (ptr & 0x7FFF)
                    if rom_off < len(rom) and not is_empty_region(rom, rom_off, 8):
                        non_empty += 1
                
                if non_empty >= 3:
                    all_ptr_tables.append({
                        'offset': base,
                        'bank': bank_for_ptrs,
                        'num_ptrs': total,
                        'unique': len(set(ptrs)),
                        'non_empty_targets': non_empty,
                        'ptr_range': (min(ptrs), max(ptrs)),
                        'first_ptrs': [hex(p) for p in ptrs[:8]],
                    })
    
    # 去重
    best_ptrs = {}
    for p in all_ptr_tables:
        off = p['offset']
        if off not in best_ptrs or p['num_ptrs'] > best_ptrs[off]['num_ptrs']:
            best_ptrs[off] = p
    
    all_ptr_tables = sorted(best_ptrs.values(), key=lambda x: x['num_ptrs'], reverse=True)
    print(f"找到 {len(all_ptr_tables)} 个有效指针表")
    
    # 保存报告
    with open(os.path.join(OUT_DIR, "rom_tables_deep_analysis.txt"), "w", encoding='utf-8') as f:
        f.write("=== ROM数据表深度分析报告 ===\n\n")
        
        f.write(f"ROM大小: {len(rom)} bytes\n")
        f.write(f"真实数据表: {len(real_tables)}\n")
        f.write(f"有效指针表: {len(all_ptr_tables)}\n\n")
        
        f.write("--- 真实数据表 (Top 30) ---\n")
        f.write(f"{'Offset':>10} {'Bank':>5} {'Len':>4} {'Recs':>5} {'16bit':>5} {'Record 0':>40}\n")
        for t in real_tables[:30]:
            f.write(f"0x{t['offset']:06X}  ${t['bank']:02X}  {t['rec_len']:3d}  {t['num_recs']:4d}  {'Y' if t['has_16bit'] else 'N':>4}  {t['records'][0]}\n")
        
        f.write(f"\n--- 数据表详细分析 (Top 10) ---\n")
        for t in real_tables[:10]:
            f.write(f"\nOffset: 0x{t['offset']:06X} (Bank ${t['bank']:02X})\n")
            f.write(f"  记录长度: {t['rec_len']}B, 记录数: {t['num_recs']}, 16位值: {t['has_16bit']}\n")
            f.write(f"  前5条记录:\n")
            for i, r in enumerate(t['records']):
                f.write(f"    [{i}] {r}\n")
            f.write(f"  字节统计:\n")
            for bs in t['byte_stats']:
                f.write(f"    Byte {bs['byte']:2d}: min={bs['min']:3d} max={bs['max']:3d} avg={bs['avg']:6.1f} unique={bs['unique']}\n")
        
        f.write(f"\n--- 有效指针表 (Top 30) ---\n")
        f.write(f"{'Offset':>10} {'Bank':>5} {'Ptrs':>5} {'Unique':>7} {'Valid':>5} {'Range':>20}\n")
        for p in all_ptr_tables[:30]:
            f.write(f"0x{p['offset']:06X}  ${p['bank']:02X}  {p['num_ptrs']:4d}  {p['unique']:5d}  {p['non_empty_targets']:4d}  ${p['ptr_range'][0]:04X}-${p['ptr_range'][1]:04X}\n")
        
        f.write(f"\n--- 指针表0x029BE4详细分析 ---\n")
        f.write(f"指针数: {len(ptrs)}, 非空目标: {len(valid_targets)}\n")
        f.write(f"前30个目标:\n")
        for t in valid_targets[:30]:
            f.write(f"  ptr={t['ptr']} -> offset={t['rom_offset']} data={t['data']}\n")
    
    print(f"\n报告已保存到 {OUT_DIR}/rom_tables_deep_analysis.txt")

if __name__ == "__main__":
    main()
