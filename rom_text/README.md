# ROM 文本提取 (ROM Text Extraction)

## 概述

本目录包含直接从 Metal Max Returns (MMR) ROM 文件中提取的文本字符串。
通过扫描 ROM 数据中的 SJIS (Shift-JIS) 和 ASCII 编码字符串, 获得了游戏的原始文本数据。

## 提取方法

- **工具**: Python 脚本 `extract_rom_text.py`
- **ROM 文件**: `MMR.smc` (4.0 MB, LoROM, FastROM)
- **编码**: SJIS (日文) + ASCII (英文)

## 提取结果

| 类型 | 总数 | 导出数量 | 文件 |
|------|------|----------|------|
| SJIS 字符串 | 28,517 | 2,000 | `sjis_strings.txt` |
| ASCII 字符串 | 15,580 | 1,000 | `ascii_strings.txt` |

## 文本样本

### ASCII 字符串
```
0x000000 | GAME DOCTOR SF 3
0x008180 | KUSOU KAGAKU DEVELOPMENT SYSTEM VER 2.19
0x0081C0 | METAL MAX RETURNS
```

### SJIS 字符串
ROM 中包含大量日文文本, 包括:
- 对话文本
- 物品名称
- 菜单选项
- 地点名称
- 系统消息

## 文件格式

```
ROM_OFFSET | LENGTH | TEXT
```

例如:
```
0x00061E |   2 | 叫~H
0x008180 |  47 | KUSOU KAGAKU DEVELOPMENT SYSTEM VER 2.19
```

## 技术说明

- ROM 使用了 **KUSOU KAGAKU DEVELOPMENT SYSTEM VER 2.19** 开发系统
- 游戏代码: **AZMJ**
- 部分 SJIS 字符串可能是误识别 (图形数据或压缩文本被错误解码)
- 真正的游戏文本通常集中在特定的 ROM 区域, 建议结合地址分析进行筛选

## 文件结构

```
rom_text/
├── README.md            # 本文档
├── sjis_strings.txt     # SJIS 日文文本 (前 2000 条)
├── ascii_strings.txt    # ASCII 英文文本 (前 1000 条)
└── extract_rom_text.py  # 提取脚本
```
