# WRAM 场景提取 (WRAM Scene Extraction)

## 概述

本目录包含从 Metal Max Returns (MMR) 游戏中 17 个不同场景捕获的 WRAM (工作 RAM) 数据。
WRAM 是 SNES 的 128KB 工作内存, 包含游戏状态变量、角色数据、临时缓冲区等。

## 采集方法

- **工具**: Mesen2 2.1.1, Lua 脚本自动化
- **脚本**: `extract_wram_scenes.lua`
- **WRAM 大小**: 131072 字节 (128KB)
- **采集数据**: WRAM (128KB) + VRAM (64KB) + CGRAM (512B) + 屏幕缓冲区 (61KB)

## 场景列表

| 场景 | 帧号 | 说明 |
|------|------|------|
| scene_00_title | 3000 | 标题画面 (基准) |
| scene_01_intro_end | 6800 | 片头结束 |
| scene_02_town | 7200 | 城镇 |
| scene_03_wm_entry | 11000 | 世界地图入口 |
| scene_04_wm_north | 11400 | 世界地图向北 |
| scene_05_wm_east | 11800 | 世界地图向东 |
| scene_06_wm_south | 12200 | 世界地图向南 |
| scene_07_before_config | 12400 | 配置菜单前 |
| scene_08_config_open | 12450 | 配置菜单打开 |
| scene_09_config_nav1 | 12500 | 配置菜单导航1 |
| scene_10_config_nav2 | 12550 | 配置菜单导航2 |
| scene_11_config_closed | 12620 | 配置菜单关闭 |
| scene_12_wm_after_config | 12800 | 配置菜单后世界地图 |
| scene_13_terrain1 | 13200 | 地形1 |
| scene_14_terrain2 | 13600 | 地形2 |
| scene_15_after_start | 14040 | Start按钮后 |
| scene_16_final | 14200 | 最终状态 |

## WRAM 差异分析

以标题画面 (scene_00_title) 为基准:

| 场景 | 差异字节 | 差异百分比 |
|------|----------|------------|
| scene_00_title | 0 | 0.00% |
| scene_01_intro_end | ~11.2KB | 8.48% |
| scene_02_town | ~11.1KB | 8.46% |
| scene_03-06_wm | ~11.1KB | 8.46-8.47% |
| scene_07-12_config | ~11.1-11.3KB | 8.48-8.56% |
| scene_13-16_final | ~11.2-11.3KB | 8.54-8.58% |

### 高波动内存区域

以下 1KB 块在 **所有** 非标题场景中都会变化 (16/16 场景):

| 地址范围 | 说明 |
|----------|------|
| 0x00000-0x017FF | 游戏引擎状态、音频缓冲区 |
| 0x04000-0x04FFF | 动画计数器、临时数据 |
| 0x10000-0x117FF | 游戏逻辑状态 |
| 0x14000-0x14FFF | 场景数据、滚动缓冲 |

## 文件结构

```
wram_scenes/
├── README.md                    # 本文档
├── contact_sheet.png            # 17 个场景的缩略图总览
├── screens/                     # 17 个屏幕截图 PNG
├── wram_dumps/                  # 二进制数据
│   ├── XX_wram.bin             # 128KB WRAM 转储
│   ├── XX_vram.bin             # 64KB VRAM 转储
│   ├── XX_cg.bin               # 512B CGRAM 转储
│   └── XX_sb.bin               # 61KB 屏幕缓冲区转储
└── tools/                       # 提取脚本
    ├── extract_wram_scenes.lua # Lua 提取脚本
    └── process_wram_scenes.py  # Python 处理脚本
```
