# SRAM 存档数据提取 (SRAM Save Data Extraction)

## 概述

本目录包含从 Metal Max Returns 游戏中 9 个场景捕获的 SRAM 存档数据。
SRAM 为 8KB (带电池备份), 用于保存游戏进度。

## 采集方法

- **工具**: Mesen2 2.1.1, Lua 脚本自动化
- **脚本**: `extract_sram.lua`
- **SRAM 大小**: 8192 字节 (8KB)
- **采集数据**: SRAM (8KB) + 屏幕缓冲区 + CGRAM + WRAM 零页 (256B)

## 场景列表

| 场景 | 帧号 | 说明 |
|------|------|------|
| sram_00_boot | 1000 | 启动 (未加载) |
| sram_01_title | 3000 | 标题画面 |
| sram_02_town | 7200 | 城镇 |
| sram_03_worldmap | 11000 | 世界地图 |
| sram_04_wm_walk1 | 12000 | 世界地图行走1 |
| sram_05_wm_walk2 | 13000 | 世界地图行走2 |
| sram_06_before_config | 14000 | 配置菜单前 |
| sram_07_config_open | 14050 | 配置菜单打开 |
| sram_08_final | 14500 | 最终状态 |

## 分析结果

### SRAM 内容

**所有 9 个场景的 SRAM 数据完全为零 (全 0x00)。**

这表明:
1. 游戏从未保存过 - 没有创建存档文件
2. SRAM 在游戏运行期间不会被初始化 (仅在保存时写入)
3. 要获取有效的 SRAM 数据, 需要在配置菜单中执行保存操作

### 如何获取有效 SRAM 数据

根据之前的发现, 配置菜单中 "PRESS START : SAVE" 表示:
1. 按 Select 打开配置菜单
2. 在配置菜单中按 Start 保存游戏
3. 保存后 SRAM 将包含游戏进度数据

## 文件结构

```
sram_data/
├── README.md                    # 本文档
├── XX_sram.bin                  # 8KB SRAM 转储 (9个)
├── XX_sb.bin                    # 屏幕缓冲区 (9个)
├── XX_cg.bin                    # CGRAM (9个)
└── XX_wram_page0.bin            # WRAM 零页 256B (9个)
```
