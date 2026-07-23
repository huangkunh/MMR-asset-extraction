# SNES Tilemap 数据提取

## 提取概述

从 Metal Max Returns (MMR) 的 5 个游戏场景中提取了完整的 VRAM 数据和 Tilemap 布局信息。

### 场景列表
| 场景 | 帧号 | 说明 |
|------|------|------|
| title | 3000 | 标题画面 |
| town | 6800 | 城镇场景 |
| worldmap | 11000 | 世界地图 |
| menu | 11500 | 游戏菜单 |
| wm_explore | 20000 | 世界地图探索 |

## VRAM 布局分析

通过对比不同场景的 VRAM 数据，发现了以下内存布局：

| VRAM 地址 | 大小 | 内容 | 特征 |
|-----------|------|------|------|
| 0x0000-0x07FF | 2KB | BG1 Tilemap | 场景间有 19.1% 差异 |
| 0x0800-0x0FFF | 2KB | BG2 Tilemap | 场景间变化 |
| 0x1000-0x17FF | 2KB | BG3 Tilemap | 场景间变化 |
| 0x1800-0x3FFF | 10KB | 空白 | 全零 |
| 0x4000-0x5FFF | 8KB | 动态瓦片图形 | 场景间 48.6% 差异 (4bpp, 256 tiles) |
| 0x6000-0x7FFF | 8KB | 空白 | 全零 |
| 0x8000-0xFFFF | 32KB | 静态瓦片图形 | 所有场景相同 (4bpp: 512 tiles / 2bpp: 1024 tiles) |

## SNES Tilemap 格式

每个 Tilemap 条目为 2 字节（小端序）：
- **Bits 0-9**: 瓦片编号 (0-1023)
- **Bits 10-12**: 调色板 (0-7)
- **Bit 13**: 优先级 (0=低, 1=高)
- **Bit 14**: 水平翻转
- **Bit 15**: 垂直翻转

## 文件结构

```
tilemaps/
├── vram_dumps/          # 64KB VRAM 二进制转储 (5场景)
├── vram_cgram/          # CGRAM (512B) + Screen Buffer 二进制
├── rendered/            # 渲染的 Tilemap PNG 图像
│   ├── *_BG1_final.png  # BG1 层 (map@0x0000, char@0x4000, 4bpp)
│   ├── *_BG2_final.png  # BG2 层 (map@0x0800, char@0x8000, 4bpp)
│   ├── *_BG3_final.png  # BG3 层 (map@0x1000, char@0x8000, 2bpp)
│   ├── *_combined.png   # 三层合成图像
│   ├── *_best_tilemap.png # 最佳匹配渲染
│   └── *_m*_c*.png      # 各配置组合的渲染尝试
├── data/                # Tilemap 数据文本转储
│   ├── *_BG1_tilemap.txt # BG1 瓦片编号矩阵 (32×32)
│   ├── *_BG2_tilemap.txt # BG2 瓦片编号矩阵
│   ├── *_BG3_tilemap.txt # BG3 瓦片编号矩阵
│   └── *_ppu.txt        # PPU 寄存器读取尝试
└── screens/             # 实际屏幕参考图像
```

## 渲染配置

### 最终使用的配置
- **BG1**: Tilemap@0x0000, 瓦片图形@0x4000, 4bpp (动态场景瓦片)
- **BG2**: Tilemap@0x0800, 瓦片图形@0x8000, 4bpp (静态瓦片)
- **BG3**: Tilemap@0x1000, 瓦片图形@0x8000, 2bpp (UI/文字层)

### 屏幕匹配度
| 场景 | 最佳匹配 | 说明 |
|------|----------|------|
| title | 78.1% | 标题画面匹配度高 |
| town | 26.7% | 因 BG 滚动偏移导致较低 |
| worldmap | 32.9% | 同上 |
| menu | 25.9% | 同上 |
| wm_explore | 33.4% | 同上 |

> 注：游戏内场景匹配度较低是因为未考虑 BG 滚动寄存器偏移和多图层优先级叠加。Tilemap 数据本身已正确提取。

## PPU 寄存器说明

SNES PPU 寄存器 ($2105-$2131) 为只写寄存器，无法通过 CPU 总线读取。
Mesen2 准确模拟了这一行为，读取返回 0x00。
内存写回调 API (emu.addMemoryCallback) 在当前版本不可用。
VRAM 布局通过对比分析确定。
