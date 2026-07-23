# ROM地图/Tilemap数据提取

## 概述

从ROM数据bank中扫描tilemap模式和大型地图数据块，提取游戏地图结构。

## 提取结果

| 类型 | 数量 | 说明 |
|------|------|------|
| Tilemap候选区域 | 121 | 连续tilemap条目(2字节/entry, tile index<512) |
| 大型数据块 (>=2KB) | 52 | 可能包含完整地图数据 |
| 中型数据块 (256B-2KB) | 128 | 可能包含小地图或地图片段 |
| 可视化PNG | 30 | tilemap tile index分布图 |

## Tilemap分布

| Bank | Tilemap数 | 说明 |
|------|-----------|------|
| $0B | 5 | 早期数据 |
| $0F | 1 | |
| $15 | 1 | |
| $16 | 1 | |
| $17 | 4 | |
| $1F | 17 | 地图数据集中区 |
| $25 | 35 | **最大地图数据bank** |
| $27 | 14 | |
| $2C | 2 | |
| $2D | 28 | **第二大地图数据bank** |
| $2F | 13 | |

## VRAM对比

与town_interior场景的VRAM BG1 tilemap对比：
- VRAM BG1: 1024 entries, 212 unique tiles, tile index range 0-1023
- 最佳ROM匹配: 0x07F600 (相似度 13.31%)
- 低相似度原因: ROM中的tilemap可能经过压缩，或tile index映射不同

## SNES Tilemap格式

每个tilemap条目为2字节(16位):
- Bit 0-9: 瓦片索引 (0-1023)
- Bit 10: Y轴翻转
- Bit 11: X轴翻转
- Bit 12-13: 优先级 (0-3)
- Bit 14-15: 调色板组 (0-3, 每组16色)

### 标准Tilemap尺寸
| 尺寸 | 条目数 | 字节数 |
|------|--------|--------|
| 32x32 | 1024 | 2048 (2KB) |
| 32x16 | 512 | 1024 (1KB) |
| 16x16 | 256 | 512 |
| 16x8 | 128 | 256 |

## 可视化说明

PNG图像使用颜色编码tile index分布：
- 每个像素代表一个tilemap条目
- 颜色基于tile index (R=tile*7, G=tile*13, B=tile*29)
- 亮度反映调色板组

## 文件说明

| 文件 | 说明 |
|------|------|
| `rom_maps_report.txt` | 完整分析报告 |
| `rom_maps_report.json` | JSON格式数据 |
| `tilemap_0x*.png` | Tilemap可视化 (30张) |
