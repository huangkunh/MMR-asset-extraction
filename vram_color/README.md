# VRAM瓦片全彩渲染

## 概述

将VRAM转储中的4bpp瓦片使用CGRAM调色板渲染为全彩PNG。每个场景的VRAM数据与对应的CGRAM调色板配对，生成真实游戏色彩的瓦片表和tilemap屏幕渲染。

## 渲染结果

| 场景 | VRAM文件 | CGRAM文件 | 渲染PNG数 |
|------|----------|-----------|-----------|
| town_interior | 22 | 22 | 210 |
| battle_vram | 22 | 22 | 210 |
| menu_system | 27 | 27 | 210 |
| wm_menu | 22 | 22 | 210 |
| **总计** | **93** | **93** | **840** |

## 渲染内容

每个VRAM转储渲染以下内容：

### 瓦片表 (Tile Sheets)
- **dyn_tiles**: 动态瓦片区域 (VRAM 0x4000-0x7FFF, 512 tiles)
- **static_tiles_lo**: 静态瓦片低区域 (VRAM 0x8000-0xBFFF, 512 tiles)
- **static_tiles_hi**: 静态瓦片高区域 (VRAM 0xC000-0xFFFF, 512 tiles)
- 每个区域使用8组调色板(pal0-pal7)分别渲染

### Tilemap屏幕 (Screen Rendering)
- **BG1**: 背景层1 tilemap (VRAM 0x0000, 32x32 tiles)
- **BG2**: 背景层2 tilemap (VRAM 0x0800, 32x32 tiles)
- **BG3**: 背景层3 tilemap (VRAM 0x1000, 32x32 tiles)
- 解析tilemap条目: tile index, X/Y翻转, 调色板组, 优先级

## 技术细节

### SNES 4bpp瓦片格式
- 每个瓦片8x8像素，32字节
- 4个bitplane，plane 0-1在前16字节，plane 2-3在后16字节
- 每行2字节(bitplane 0和1)，8行

### SNES BGR555调色板
- CGRAM: 512字节 = 256色 × 2字节
- 每色16位: 5位蓝 + 5位绿 + 5位红 (BGR555)
- 转换为RGB888: 每通道左移3位 + 高3位右移2位

### Tilemap条目格式 (2字节)
- Bit 0-9: 瓦片索引 (0-1023)
- Bit 10: Y轴翻转
- Bit 11: X轴翻转
- Bit 12-13: 优先级
- Bit 14-15: 调色板组 (0-7, 每组16色)

## 文件命名

```
{场景标签}_{区域}_{调色板组}.png
{场景标签}_{BG层}_screen.png
```

示例:
- `capture_0010_dyn_tiles_pal0.png` - 动态瓦片，调色板组0
- `capture_0010_BG1_screen.png` - BG1背景层屏幕渲染
