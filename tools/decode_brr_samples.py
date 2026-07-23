#!/usr/bin/env python3
"""
BRR音频样本深度解码器
从SPC700 RAM中通过DSP DIR寄存器定位样本目录，解码所有BRR样本为WAV
"""
import struct
import os
import sys
import json
import wave

REPO_DIR = "/workspace/MMR-asset-extraction"
SPC_DUMP_DIR = os.path.join(REPO_DIR, "brr_extended/spc_dumps")
OUT_DIR = "/data/user/work/brr_decoded"
os.makedirs(OUT_DIR, exist_ok=True)

SAMPLE_RATE = 32000  # SPC700 native sample rate

def read_dsp_registers(dsp_path):
    """读取128字节DSP寄存器"""
    with open(dsp_path, "rb") as f:
        return f.read()

def read_spc_ram(spc_path):
    """读取64KB SPC RAM"""
    with open(spc_path, "rb") as f:
        return f.read()

def get_sample_directory(spc_ram, dir_reg):
    """从DIR寄存器值获取样本目录"""
    dir_addr = dir_reg * 256  # DIR是页对齐的
    entries = []
    for i in range(256):  # 最多256个样本槽
        ptr_off = dir_addr + i * 2
        if ptr_off + 2 > len(spc_ram):
            break
        ptr = struct.unpack_from('<H', spc_ram, ptr_off)[0]
        entries.append(ptr)
    return dir_addr, entries

def decode_brr_sample(spc_ram, start_addr, max_blocks=10000):
    """
    解码BRR样本
    每个块9字节: 1头 + 8数据(16个4位样本)
    """
    samples = []
    addr = start_addr
    blocks = 0
    loop_addr = None
    ended = False

    while blocks < max_blocks and addr + 9 <= len(spc_ram):
        header = spc_ram[addr]
        range_val = (header >> 4) & 0x0F
        filter_val = (header >> 2) & 0x03
        loop_flag = header & 0x03  # 0=continue, 1=loop, 3=end without loop, 3=end

        # 读取16个4位样本
        nibbles = []
        for i in range(8):
            byte = spc_ram[addr + 1 + i]
            nibbles.append((byte >> 4) & 0x0F)   # 高4位
            nibbles.append(byte & 0x0F)            # 低4位

        # 解码样本
        old1 = samples[-1] if len(samples) > 0 else 0
        old2 = samples[-2] if len(samples) > 1 else 0

        for nib in nibbles:
            # 符号扩展4位到16位
            if nib & 0x08:
                sample = nib - 16
            else:
                sample = nib

            # 范围移位
            sample = sample << range_val

            # 滤波器
            if filter_val == 0:
                # 无滤波
                pass
            elif filter_val == 1:
                sample += old1 + (-old1 >> 4)
            elif filter_val == 2:
                sample += (old1 << 1) + (-(old1 + (old1 << 1)) >> 5) - old2 + (old2 >> 4)
            elif filter_val == 3:
                sample += (old1 << 1) + (-(old1 + (old1 << 1) + (old1 << 2)) >> 6) - old2 + ((old2 << 1) + (old2 << 2) + (old2 << 3) >> 6)

            # 钳位到16位
            if sample > 32767:
                sample = 32767
            elif sample < -32768:
                sample = -32768

            samples.append(sample)
            old2 = old1
            old1 = sample

        blocks += 1
        addr += 9

        # 检查结束标志
        if loop_flag == 1:
            loop_addr = addr
        elif loop_flag == 3 or loop_flag == 1:
            ended = True
            break

    return samples, blocks, ended, loop_addr

def save_wav(samples, filepath, sample_rate=SAMPLE_RATE):
    """保存16位PCM WAV"""
    with wave.open(filepath, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        # 转换为unsigned 16-bit
        data = struct.pack('<' + 'h' * len(samples), *samples)
        w.writeframes(data)

def analyze_spc_dump(spc_ram, dsp_regs, label):
    """分析单个SPC转储"""
    results = {
        'label': label,
        'dir_reg': dsp_regs[0x5D],
        'esa_reg': dsp_regs[0x5E],
        'kon_l': dsp_regs[0x4C],
        'kon_h': dsp_regs[0x5C],
        'flg': dsp_regs[0x6C],  # FLG register
        'samples': []
    }

    dir_addr, entries = get_sample_directory(spc_ram, dsp_regs[0x5D])

    print(f"  DIR=0x{dsp_regs[0x5D]:02X} (dir at 0x{dir_addr:04X})")
    print(f"  KON=0x{dsp_regs[0x4C]:02X}{dsp_regs[0x5C]:02X} FLG=0x{dsp_regs[0x6C]:02X}")
    print(f"  ESA=0x{dsp_regs[0x5E]:02X} (echo at 0x{dsp_regs[0x5E]*256:04X})")

    # 检查哪些voice被key on
    kon = dsp_regs[0x4C] | (dsp_regs[0x5C] << 8)
    active_voices = [i for i in range(8) if kon & (1 << i)]
    print(f"  Active voices: {active_voices}")

    # 读取每个voice的SRCN (样本编号)
    for v in active_voices:
        srcn_reg = 0x06 + v * 0x10  # Vx_SRCN
        pitch_l = 0x04 + v * 0x10
        pitch_h = 0x05 + v * 0x10
        if srcn_reg < len(dsp_regs):
            srcn = dsp_regs[srcn_reg]
            pitch = dsp_regs[pitch_l] | (dsp_regs[pitch_h] << 8)
            print(f"  Voice {v}: SRCN={srcn} pitch=0x{pitch:04X}")

    # 解码所有有效的样本
    decoded_count = 0
    unique_ptrs = set()

    for i, ptr in enumerate(entries):
        if ptr == 0 or ptr >= len(spc_ram) - 9:
            continue

        # 检查是否是有效的BRR头
        header = spc_ram[ptr]
        range_val = (header >> 4) & 0x0F
        filter_val = (header >> 2) & 0x03
        loop_flag = header & 0x03

        # 跳过明显无效的指针（指向0x0000附近或太接近末尾）
        if ptr < 0x0100:
            continue

        # 避免重复解码同一个指针
        if ptr in unique_ptrs:
            continue
        unique_ptrs.add(ptr)

        try:
            samples, blocks, ended, loop_addr = decode_brr_sample(spc_ram, ptr, max_blocks=5000)

            if len(samples) < 16:
                continue

            # 检查样本是否全零（静音）
            non_zero = sum(1 for s in samples[:100] if abs(s) > 100)
            if non_zero == 0 and len(samples) < 100:
                continue

            sample_info = {
                'slot': i,
                'ptr': ptr,
                'header': header,
                'range': range_val,
                'filter': filter_val,
                'loop': loop_flag,
                'num_samples': len(samples),
                'num_blocks': blocks,
                'ended': ended,
                'duration_ms': len(samples) * 1000 / SAMPLE_RATE,
                'has_audio': non_zero > 0,
            }
            results['samples'].append(sample_info)

            # 保存WAV
            wav_path = os.path.join(OUT_DIR, f"{label}_slot{i:02d}_ptr0x{ptr:04X}.wav")
            save_wav(samples, wav_path)

            decoded_count += 1
            if decoded_count <= 20:
                print(f"    Slot {i:3d}: ptr=0x{ptr:04X} blocks={blocks:4d} samples={len(samples):6d} "
                      f"({len(samples)/SAMPLE_RATE:.2f}s) range={range_val} filter={filter_val} loop={loop_flag} "
                      f"audio={'Y' if non_zero > 0 else 'N'}")

        except Exception as e:
            pass

    results['total_decoded'] = decoded_count
    results['unique_ptrs'] = len(unique_ptrs)
    print(f"  解码完成: {decoded_count} 个样本")

    return results

def main():
    print("=== BRR音频样本深度解码器 ===\n")

    # 查找所有SPC转储
    spc_files = sorted([f for f in os.listdir(SPC_DUMP_DIR) if f.endswith('_spcRam.bin')])

    print(f"找到 {len(spc_files)} 个SPC RAM转储\n")

    all_results = []

    for spc_file in spc_files:
        label = spc_file.replace('_spcRam.bin', '')

        spc_path = os.path.join(SPC_DUMP_DIR, spc_file)
        dsp_path = os.path.join(SPC_DUMP_DIR, spc_file.replace('_spcRam.bin', '_dspRegs.bin'))

        if not os.path.exists(dsp_path):
            print(f"跳过 {label} (无DSP寄存器)")
            continue

        spc_ram = read_spc_ram(spc_path)
        dsp_regs = read_dsp_registers(dsp_path)

        print(f"--- {label} ---")
        result = analyze_spc_dump(spc_ram, dsp_regs, label)
        all_results.append(result)
        print()

    # 汇总
    total_samples = sum(r['total_decoded'] for r in all_results)
    total_wavs = len([f for f in os.listdir(OUT_DIR) if f.endswith('.wav')])

    print(f"\n=== 汇总 ===")
    print(f"处理的SPC转储: {len(all_results)}")
    print(f"解码的BRR样本总数: {total_samples}")
    print(f"生成的WAV文件: {total_wavs}")

    # 保存报告
    report = {
        'summary': {
            'spc_dumps_processed': len(all_results),
            'total_samples_decoded': total_samples,
            'wav_files_generated': total_wavs,
            'sample_rate': SAMPLE_RATE,
        },
        'dumps': all_results,
    }

    with open(os.path.join(OUT_DIR, "brr_decode_report.json"), "w", encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # 人类可读报告
    with open(os.path.join(OUT_DIR, "brr_decode_report.txt"), "w", encoding='utf-8') as f:
        f.write("=== BRR音频样本深度解码报告 ===\n\n")
        f.write(f"SPC转储数: {len(all_results)}\n")
        f.write(f"解码样本总数: {total_samples}\n")
        f.write(f"WAV文件数: {total_wavs}\n")
        f.write(f"采样率: {SAMPLE_RATE} Hz\n\n")

        for r in all_results:
            f.write(f"--- {r['label']} ---\n")
            f.write(f"  DIR=0x{r['dir_reg']:02X} KON=0x{r['kon_l']:02X}{r['kon_h']:02X} FLG=0x{r['flg']:02X}\n")
            f.write(f"  解码样本: {r['total_decoded']}\n")
            for s in r['samples'][:10]:
                f.write(f"    Slot {s['slot']:3d} ptr=0x{s['ptr']:04X} "
                       f"{s['num_samples']:6d} samples ({s['duration_ms']:.0f}ms) "
                       f"range={s['range']} filter={s['filter']} loop={s['loop']} "
                       f"audio={'Y' if s['has_audio'] else 'N'}\n")
            f.write("\n")

    print(f"\n报告已保存到 {OUT_DIR}/")

if __name__ == "__main__":
    main()
