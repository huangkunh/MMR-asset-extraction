# 扩展 BRR 音频提取 (Extended BRR Audio Extraction)

## 概述

本目录包含从 12 个游戏场景中提取的 SPC700 音频子系统的完整状态数据。
每次捕获包含 SPC RAM、SPC ROM 和 DSP 寄存器，以及对应的 VRAM/CGRAM/屏幕缓冲区用于场景关联。

## 采集方法

- **工具**: Mesen2 2.1.1, Lua 脚本自动化
- **脚本**: `extract_brr_extended.lua`
- **采集数据**: SPC RAM (64KB) + SPC ROM (64KB) + DSP 寄存器 (128B) + VRAM (64KB) + CGRAM (512B) + 屏幕缓冲区

## 场景列表

| 场景 | 帧号 | 说明 |
|------|------|------|
| spc_00_title | 3000 | 标题画面 |
| spc_01_intro_end | 6800 | 片头结束 |
| spc_02_town | 7200 | 城镇内部 |
| spc_03_wm_entry | 11000 | 世界地图入口 |
| spc_04_wm_walk1 | 11700 | 世界地图行走 |
| spc_05_before_config | 12400 | 配置菜单前 |
| spc_06_config_open | 12450 | 配置菜单打开 |
| spc_07_config_nav | 12550 | 配置菜单导航 |
| spc_08_config_closed | 12620 | 配置菜单关闭 |
| spc_09_wm_terrain1 | 13200 | 世界地图地形 |
| spc_10_after_start | 14040 | Start 按钮后 |
| spc_11_final | 14200 | 最终状态 |

## 分析结果

### SPC RAM 跨场景变化

| 场景 | 差异字节数 | 差异百分比 |
|------|-----------|-----------|
| spc_00_title | 0 | 0.00% (基准) |
| spc_01-04 (城镇/世界地图) | ~5545-5555 | ~8.46-8.48% |
| spc_06-11 (配置菜单/后续) | ~5608-5619 | ~8.56-8.57% |

### DSP 状态

所有 12 个场景的 KON 寄存器均为 0，表示无活跃音频通道。
这是因为 Mesen2 在 `SDL_AUDIODRIVER=dummy` 模式下不驱动音频输出，DSP 处于静音状态。

### SPC RAM 活跃区域

| 地址范围 | 变化程度 | 可能用途 |
|----------|---------|---------|
| 0x4000-0x4FFF (12KB) | 所有场景最高活跃 | BRR 采样缓冲区 |
| 0x0C00-0x0DFF (512B) | 高活跃 | SPC700-CPU DSP 通信区 |
| 0x0700-0x0BFF (1.5KB) | 中等活跃 | SPC700 音频驱动程序 |
| 0x0000-0x0300 (768B) | 中等活跃 | SPC700 零页/堆栈区 |

## 文件结构

```
brr_extended/
├── README.md                    # 本文档
├── spc_dumps/                   # 二进制数据 (72 个文件)
│   ├── XX_spcRam.bin           # SPC RAM (64KB)
│   ├── XX_spcRom.bin           # SPC ROM (64KB)
│   ├── XX_dspRegs.bin          # DSP 寄存器 (128B)
│   ├── XX_vram.bin             # VRAM (64KB)
│   ├── XX_cg.bin               # CGRAM (512B)
│   └── XX_sb.bin               # 屏幕缓冲区
└── tools/
    ├── extract_brr_extended.lua  # Lua 提取脚本
    └── analyze_brr_extended.py   # Python 分析脚本
```

## 技术说明

- Mesen2 的 `snesSpcRom` 返回的数据与 `snesSpcRam` 存在关联，可能是同一内存映射
- 在 `SDL_AUDIODRIVER=dummy` 模式下 DSP KON=0，无法获取活跃通道信息
- SPC RAM 的 `0x4000-0x4FFF` 区域是 BRR 采样数据的主要活动区域
