#!/usr/bin/env python3
"""
SPC700程序代码分析
反汇编SPC700 RAM中的程序代码，分析音频引擎结构
"""
import struct
import os
import json

REPO_DIR = "/workspace/MMR-asset-extraction"
SPC_DUMP_DIR = os.path.join(REPO_DIR, "brr_extended/spc_dumps")
OUT_DIR = "/data/user/work/spc700_analysis"
os.makedirs(OUT_DIR, exist_ok=True)

# SPC700 指令集 (部分关键指令)
SPC700_MNEMONICS = {
    0x00: ("NOP", 0), 0x01: ("TCALL", 1), 0x02: ("SET1", 2), 0x03: ("BBS", 3),
    0x04: ("OR A,", 1), 0x05: ("OR A,", 1), 0x06: ("OR A,(X)", 0),
    0x07: ("OR A,(X+)", 0), 0x08: ("OR A,#", 1), 0x09: ("OR (X),(Y)", 0),
    0x0A: ("OR1 C,", 2), 0x0B: ("ASL", 0), 0x0C: ("ASL", 1), 0x0D: ("PUSH PSW", 0),
    0x0E: ("TSET1", 2), 0x0F: ("BRK", 0),
    0x10: ("BPL", 1), 0x11: ("TCALL", 1), 0x12: ("CLR1", 2), 0x13: ("BBC", 3),
    0x14: ("OR A,", 1), 0x15: ("OR A,", 1), 0x16: ("OR A,(X+)", 0),
    0x18: ("OR,", 2), 0x19: ("OR (X),(Y)", 0), 0x1A: ("DECW YA", 0),
    0x1B: ("ASL", 1), 0x1C: ("ASL", 0), 0x1D: ("DEC X", 0), 0x1E: ("CMP X,#", 1),
    0x1F: ("JMP (X+)", 0),
    0x20: ("CLRP", 0), 0x21: ("TCALL", 1), 0x22: ("SET1", 2), 0x23: ("BBS", 3),
    0x24: ("AND A,", 1), 0x25: ("AND A,", 1), 0x26: ("AND A,(X)", 0),
    0x27: ("AND A,(X+)", 0), 0x28: ("AND A,#", 1), 0x29: ("AND (X),(Y)", 0),
    0x2A: ("OR1 C,/", 2), 0x2B: ("ROL", 1), 0x2C: ("ROL", 1), 0x2D: ("PUSH A", 0),
    0x2E: ("CBNE", 2), 0x2F: ("BRA", 1),
    0x30: ("BMI", 1), 0x31: ("TCALL", 1), 0x32: ("CLR1", 2), 0x33: ("BBC", 3),
    0x34: ("AND A,", 1), 0x35: ("AND A,", 1), 0x36: ("AND A,(X+)", 0),
    0x38: ("AND,", 2), 0x39: ("AND (X),(Y)", 0), 0x3A: ("INCW YA", 0),
    0x3B: ("ROL", 1), 0x3C: ("ROL", 0), 0x3D: ("INC X", 0), 0x3E: ("CMP X,", 1),
    0x3F: ("CALL", 2),
    0x40: ("SETP", 0), 0x41: ("TCALL", 1), 0x42: ("SET1", 2), 0x43: ("BBS", 3),
    0x44: ("EOR A,", 1), 0x45: ("EOR A,", 1), 0x46: ("EOR A,(X)", 0),
    0x47: ("EOR A,(X+)", 0), 0x48: ("EOR A,#", 1), 0x49: ("EOR (X),(Y)", 0),
    0x4A: ("AND1 C,", 2), 0x4B: ("LSR", 1), 0x4C: ("LSR", 1), 0x4D: ("PUSH X", 0),
    0x4E: ("TCLR1", 2), 0x4F: ("PCALL", 1),
    0x50: ("BVC", 1), 0x51: ("TCALL", 1), 0x52: ("CLR1", 2), 0x53: ("BBC", 3),
    0x54: ("EOR A,", 1), 0x55: ("EOR A,", 1), 0x56: ("EOR A,(X+)", 0),
    0x58: ("EOR,", 2), 0x59: ("EOR (X),(Y)", 0), 0x5A: ("ADDW YA,", 1),
    0x5B: ("LSR", 1), 0x5C: ("LSR", 0), 0x5D: ("MOV X,A", 0), 0x5E: ("CMP Y,#", 1),
    0x5F: ("JMP", 2),
    0x60: ("CLRC", 0), 0x61: ("TCALL", 1), 0x62: ("SET1", 2), 0x63: ("BBS", 3),
    0x64: ("CMP A,", 1), 0x65: ("CMP A,", 1), 0x66: ("CMP A,(X)", 0),
    0x67: ("CMP A,(X+)", 0), 0x68: ("CMP A,#", 1), 0x69: ("CMP (X),(Y)", 0),
    0x6A: ("AND1 C,/", 2), 0x6B: ("ROR", 1), 0x6C: ("ROR", 1), 0x6D: ("PUSH Y", 0),
    0x6E: ("DBNZ", 2), 0x6F: ("RET", 0),
    0x70: ("BVS", 1), 0x71: ("TCALL", 1), 0x72: ("CLR1", 2), 0x73: ("BBC", 3),
    0x74: ("CMP A,", 1), 0x75: ("CMP A,", 1), 0x76: ("CMP A,(X+)", 0),
    0x78: ("CMP,", 2), 0x79: ("CMP (X),(Y)", 0), 0x7A: ("SUBW YA,", 1),
    0x7B: ("ROR", 1), 0x7C: ("ROR", 0), 0x7D: ("MOV A,X", 0), 0x7E: ("CMP Y,", 1),
    0x7F: ("RET1", 0),
    0x80: ("SETC", 0), 0x81: ("TCALL", 1), 0x82: ("SET1", 2), 0x83: ("BBS", 3),
    0x84: ("ADC A,", 1), 0x85: ("ADC A,", 1), 0x86: ("ADC A,(X)", 0),
    0x87: ("ADC A,(X+)", 0), 0x88: ("ADC A,#", 1), 0x89: ("ADC (X),(Y)", 0),
    0x8A: ("EOR1 C,", 2), 0x8B: ("DEC", 1), 0x8C: ("DEC", 1), 0x8D: ("MOV Y,#", 1),
    0x8E: ("POP PSW", 0), 0x8F: ("MOV (X+),A", 0),
    0x90: ("BCC", 1), 0x91: ("TCALL", 1), 0x92: ("CLR1", 2), 0x93: ("BBC", 3),
    0x94: ("ADC A,", 1), 0x95: ("ADC A,", 1), 0x96: ("ADC A,(X+)", 0),
    0x98: ("ADC,", 2), 0x99: ("ADC (X),(Y)", 0), 0x9A: ("MOVW YA,", 1),
    0x9B: ("DEC", 1), 0x9C: ("DEC", 0), 0x9D: ("MOV X,SP", 0), 0x9E: ("DIV YA,X", 0),
    0x9F: ("XCN A", 0),
    0xA0: ("EI", 0), 0xA1: ("TCALL", 1), 0xA2: ("SET1", 2), 0xA3: ("BBS", 3),
    0xA4: ("SBC A,", 1), 0xA5: ("SBC A,", 1), 0xA6: ("SBC A,(X)", 0),
    0xA7: ("SBC A,(X+)", 0), 0xA8: ("SBC A,#", 1), 0xA9: ("SBC (X),(Y)", 0),
    0xAA: ("MOV1 C,", 2), 0xAB: ("INC", 1), 0xAC: ("INC", 1), 0xAD: ("MOV A,#", 1),
    0xAE: ("POP A", 0), 0xAF: ("MOV (X+),A", 0),
    0xB0: ("BCS", 1), 0xB1: ("TCALL", 1), 0xB2: ("CLR1", 2), 0xB3: ("BBC", 3),
    0xB4: ("SBC A,", 1), 0xB5: ("SBC A,", 1), 0xB6: ("SBC A,(X+)", 0),
    0xB8: ("SBC,", 2), 0xB9: ("SBC (X),(Y)", 0), 0xBA: ("MOVW ", 1),
    0xBB: ("INC", 1), 0xBC: ("INC", 0), 0xBD: ("MOV SP,X", 0), 0xBE: ("DAS A", 0),
    0xBF: ("MOV A,(X)+", 0),
    0xC0: ("DI", 0), 0xC1: ("TCALL", 1), 0xC2: ("SET1", 2), 0xC3: ("BBS", 3),
    0xC4: ("MOV ", 2), 0xC5: ("MOV A,", 1), 0xC6: ("MOV (X),A", 0),
    0xC7: ("MOV (X+),A", 0), 0xC8: ("CMP X,#", 1), 0xC9: ("MOV (X),(Y)", 0),
    0xCA: ("MOV1 ", 3), 0xCB: ("MOV ", 2), 0xCC: ("MOV ", 1), 0xCD: ("MOV X,#", 1),
    0xCE: ("POP X", 0), 0xCF: ("MUL YA", 0),
    0xD0: ("BNE", 1), 0xD1: ("TCALL", 1), 0xD2: ("CLR1", 2), 0xD3: ("BBC", 3),
    0xD4: ("MOV A,", 1), 0xD5: ("MOV A,", 1), 0xD6: ("MOV A,(X+)", 0),
    0xD7: ("MOV (X+),A", 0), 0xD8: ("MOV ", 2), 0xD9: ("MOV (X),(Y)", 0),
    0xDA: ("MOVW ", 1), 0xDB: ("MOV ", 2), 0xDC: ("MOV Y,", 1), 0xDD: ("MOV Y,#", 1),
    0xDE: ("POP Y", 0), 0xDF: ("DAA A", 0),
    0xE0: ("CLRV", 0), 0xE1: ("TCALL", 1), 0xE2: ("SET1", 2), 0xE3: ("BBS", 3),
    0xE4: ("MOV A,", 1), 0xE5: ("MOV A,", 1), 0xE6: ("MOV A,(X)", 0),
    0xE7: ("MOV A,(X+)", 0), 0xE8: ("MOV A,#", 1), 0xE9: ("MOV (X),(Y)", 0),
    0xEA: ("NOT1 C", 0), 0xEB: ("MOV ", 2), 0xEC: ("MOV ", 1), 0xED: ("MOV X,", 1),
    0xEE: ("SLEEP", 0), 0xEF: ("STOP", 0),
    0xF0: ("BEQ", 1), 0xF1: ("TCALL", 1), 0xF2: ("CLR1", 2), 0xF3: ("BBC", 3),
    0xF4: ("MOV A,", 1), 0xF5: ("MOV A,", 1), 0xF6: ("MOV A,(X+)", 0),
    0xF7: ("MOV (X+),A", 0), 0xF8: ("MOV ", 2), 0xF9: ("MOV (X),(Y)", 0),
    0xFA: ("MOV ", 2), 0xFB: ("MOV ", 2), 0xFC: ("INC Y", 0), 0xFD: ("MOV Y,", 1),
    0xFE: ("DEC Y", 0), 0xFF: ("MOV A,(X)+", 0),
}

def disassemble_spc700(data, start, end):
    """反汇编SPC700代码"""
    instructions = []
    addr = start

    while addr < end and addr < len(data):
        opcode = data[addr]
        if opcode in SPC700_MNEMONICS:
            mnemonic, operand_len = SPC700_MNEMONICS[opcode]
            operands = []
            raw_bytes = [opcode]

            for i in range(operand_len):
                if addr + 1 + i < len(data):
                    operands.append(data[addr + 1 + i])
                    raw_bytes.append(data[addr + 1 + i])

            # 格式化操作数
            operand_str = ""
            if operand_len == 1:
                if "#" in mnemonic or "A,#" in mnemonic:
                    operand_str = f"#${operands[0]:02X}"
                elif "BPL" in mnemonic or "BMI" in mnemonic or "BRA" in mnemonic or \
                     "BVC" in mnemonic or "BVS" in mnemonic or "BCC" in mnemonic or \
                     "BCS" in mnemonic or "BNE" in mnemonic or "BEQ" in mnemonic:
                    # 相对跳转
                    offset = operands[0]
                    if offset > 127:
                        offset -= 256
                    target = addr + 2 + offset
                    operand_str = f"${target:04X}"
                else:
                    operand_str = f"${operands[0]:02X}"
            elif operand_len == 2:
                val = operands[0] | (operands[1] << 8)
                if "CALL" in mnemonic or "JMP" in mnemonic:
                    operand_str = f"${val:04X}"
                else:
                    operand_str = f"${val:04X}"
            elif operand_len == 3:
                operand_str = f"${operands[0]:02X},${operands[1]:02X}"

            full_mnemonic = mnemonic + operand_str
            hex_bytes = " ".join(f"{b:02X}" for b in raw_bytes)

            instructions.append({
                'addr': addr,
                'hex': hex_bytes,
                'mnemonic': full_mnemonic,
                'opcode': opcode,
            })

            addr += 1 + operand_len
        else:
            instructions.append({
                'addr': addr,
                'hex': f"{opcode:02X}",
                'mnemonic': f"DB ${opcode:02X}",
                'opcode': opcode,
            })
            addr += 1

    return instructions

def analyze_spc_program(spc_ram, label):
    """分析SPC700程序"""
    results = {
        'label': label,
        'reset_vector': None,
        'entry_point': None,
        'code_regions': [],
        'subroutines': [],
        'instruction_count': 0,
    }

    # 读取复位向量 (0xFFFE-0xFFFF)
    if len(spc_ram) >= 0x10000:
        reset_vec = spc_ram[0xFFFE] | (spc_ram[0xFFFF] << 8)
        results['reset_vector'] = reset_vec
        results['entry_point'] = reset_vec
        print(f"  Reset vector: ${reset_vec:04X}")

    # 分析代码区域
    # SPC700程序通常在0x0000-0x03FF (sample directory之前) 和其他区域
    # 扫描整个RAM，找高密度代码区域

    # 反汇编入口点附近的代码
    if reset_vec and reset_vec < len(spc_ram):
        print(f"  Disassembling from entry point ${reset_vec:04X}...")
        instructions = disassemble_spc700(spc_ram, reset_vec, min(reset_vec + 512, len(spc_ram)))
        results['entry_disasm'] = instructions[:100]
        results['instruction_count'] += len(instructions)

        # 查找CALL指令目标（子程序）
        call_targets = set()
        for inst in instructions:
            if 'CALL' in inst['mnemonic'] and '$' in inst['mnemonic']:
                try:
                    target = int(inst['mnemonic'].split('$')[-1], 16)
                    if target < len(spc_ram):
                        call_targets.add(target)
                except:
                    pass

        # 反汇编每个子程序的前64条指令
        for target in sorted(call_targets)[:20]:
            sub_insts = disassemble_spc700(spc_ram, target, min(target + 128, len(spc_ram)))
            # 查找RET指令
            ret_found = False
            for si in sub_insts:
                if si['mnemonic'] in ['RET', 'RET1']:
                    ret_found = True
                    break

            results['subroutines'].append({
                'addr': target,
                'num_instructions': len(sub_insts),
                'has_ret': ret_found,
                'first_instructions': [f"${i['addr']:04X}: {i['hex']:12s} {i['mnemonic']}" for i in sub_insts[:10]],
            })

    # 分析DSP寄存器写入 (MOV $F2, #xx; MOV $F3, #xx 模式)
    dsp_writes = []
    for i in range(len(spc_ram) - 3):
        # 查找 MOV $F2, #reg; MOV $F3, #val 模式
        # SPC700: 8D xx F2 (MOV $F2,#imm) 8D yy F3 (MOV $F3,#imm)
        if spc_ram[i] == 0x8F and spc_ram[i+2] == 0xF2 and \
           spc_ram[i+3] == 0x8F and i + 5 < len(spc_ram) and spc_ram[i+5] == 0xF3:
            reg = spc_ram[i+1]
            val = spc_ram[i+4]
            dsp_writes.append({
                'addr': i,
                'reg': f"${reg:02X}",
                'val': f"${val:02X}",
            })

    results['dsp_writes'] = dsp_writes[:50]
    results['dsp_write_count'] = len(dsp_writes)

    # 分析端口通信 (MOV $F4-$F7, SNES <-> SPC 通信端口)
    port_reads = []
    for i in range(len(spc_ram) - 2):
        # MOV A, $F4-F7 (读取SNES端口)
        if spc_ram[i] == 0xE4 or spc_ram[i] == 0xF4:
            if i + 1 < len(spc_ram) and 0xF4 <= spc_ram[i+1] <= 0xF7:
                port_reads.append(i)

    results['port_comm_count'] = len(port_reads)

    return results

def main():
    print("=== SPC700程序代码分析 ===\n")

    spc_files = sorted([f for f in os.listdir(SPC_DUMP_DIR) if f.endswith('_spcRam.bin')])
    print(f"找到 {len(spc_files)} 个SPC RAM转储\n")

    all_results = []

    for spc_file in spc_files[:4]:  # 只分析前4个（足够代表性）
        label = spc_file.replace('_spcRam.bin', '')
        spc_path = os.path.join(SPC_DUMP_DIR, spc_file)

        with open(spc_path, "rb") as f:
            spc_ram = f.read()

        print(f"--- {label} ---")
        result = analyze_spc_program(spc_ram, label)
        all_results.append(result)

        print(f"  指令数: {result['instruction_count']}")
        print(f"  子程序数: {len(result['subroutines'])}")
        print(f"  DSP寄存器写入: {result['dsp_write_count']}")
        print(f"  端口通信: {result['port_comm_count']}")

        # 显示入口点反汇编
        if 'entry_disasm' in result:
            print(f"\n  入口点反汇编 (前20条):")
            for inst in result['entry_disasm'][:20]:
                print(f"    ${inst['addr']:04X}: {inst['hex']:12s} {inst['mnemonic']}")

        # 显示子程序
        if result['subroutines']:
            print(f"\n  子程序 (前10个):")
            for sub in result['subroutines'][:10]:
                print(f"    ${sub['addr']:04X}: {sub['num_instructions']}条指令, RET={'Y' if sub['has_ret'] else 'N'}")
                for line in sub['first_instructions'][:3]:
                    print(f"      {line}")

        print()

    # 保存报告
    with open(os.path.join(OUT_DIR, "spc700_analysis_report.txt"), "w", encoding='utf-8') as f:
        f.write("=== SPC700程序代码分析报告 ===\n\n")

        for r in all_results:
            f.write(f"--- {r['label']} ---\n")
            f.write(f"  Reset vector: ${r['reset_vector']:04X}\n" if r['reset_vector'] else "  Reset vector: N/A\n")
            f.write(f"  指令数: {r['instruction_count']}\n")
            f.write(f"  子程序数: {len(r['subroutines'])}\n")
            f.write(f"  DSP寄存器写入: {r['dsp_write_count']}\n")
            f.write(f"  端口通信点: {r['port_comm_count']}\n\n")

            if 'entry_disasm' in r:
                f.write(f"  入口点反汇编:\n")
                for inst in r['entry_disasm']:
                    f.write(f"    ${inst['addr']:04X}: {inst['hex']:12s} {inst['mnemonic']}\n")
                f.write("\n")

            f.write(f"  子程序列表:\n")
            for sub in r['subroutines']:
                f.write(f"    ${sub['addr']:04X}: {sub['num_instructions']}条指令, RET={'Y' if sub['has_ret'] else 'N'}\n")
                for line in sub['first_instructions'][:5]:
                    f.write(f"      {line}\n")
                f.write("\n")

            f.write(f"  DSP寄存器写入 (前30):\n")
            for dw in r.get('dsp_writes', [])[:30]:
                f.write(f"    @${dw['addr']:04X}: REG {dw['reg']} = {dw['val']}\n")
            f.write("\n")

    # JSON报告
    with open(os.path.join(OUT_DIR, "spc700_analysis_report.json"), "w", encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)

    print(f"报告已保存到 {OUT_DIR}/")

if __name__ == "__main__":
    main()
