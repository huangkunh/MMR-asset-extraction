# Metal Max Returns (MMR) 素材提取项目

从 SNES 游戏 Metal Max Returns (メタルマックスリターンズ) 中全面提取游戏素材数据，包括 VRAM 图块、WRAM 状态、CGRAM 调色板、SPC700 音频、ROM 文本、ROM 图形、ROM 数据表、SRAM 存档等。

## 游戏信息

| 属性 | 值 |
|------|-----|
| 游戏名称 | Metal Max Returns (メタルマックスリターンズ) |
| 游戏代码 | AZMJ |
| 平台 | Super Nintendo (SNES/SFC) |
| ROM 大小 | 4 MB (LoROM, FastROM) |
| SRAM | 8 KB (带电池) |
| 开发工具 | 空想科学開発システム VER 2.19 |

## 提取工具

- **模拟器**: Mesen2 2.1.1 (无头模式, Xvfb 虚拟显示)
- **自动化**: Lua 脚本 (`emu.addEventCallback`, `emu.getScreenBuffer()`, `emu.read()`, `emu.setInput()`)
- **音频**: `SDL_AUDIODRIVER=dummy` (DSP 静音模式)
- **处理**: Python (PIL/Pillow 图像处理)

## 已完成提取

### VRAM 数据

| 目录 | 内容 | 场景数 |
|------|------|--------|
| `tilemaps/` | BG 图块图渲染, VRAM 布局分析 | 5 |
| `town_interior/` | 城镇建筑内部 VRAM | 22 |
| `battle_vram/` | 世界地图探索 + 场景过渡 | 22 |
| `menu_system/` | 菜单交互 + CGRAM 动画检测 | 27 |
| `wm_menu/` | **发现 Select 按钮打开配置菜单** | 22 |
| `vram_color/` | **VRAM瓦片全彩渲染 (CGRAM调色板上色)** | 840 PNG |
| `vram_catalog/` | 跨会话综合分析: 588 静态图块, 390 动态图块 | 105 dumps |

**VRAM 布局**:
- `0x0000-0x07FF`: BG1 Tilemap
- `0x0800-0x0FFF`: BG2 Tilemap
- `0x1000-0x17FF`: BG3 Tilemap
- `0x4000-0x5FFF`: 动态字符数据 (4bpp, 场景相关)
- `0x8000-0xFFFF`: 静态字符数据 (所有场景完全相同)

### WRAM 数据

| 目录 | 内容 | 场景数 |
|------|------|--------|
| `wram_scenes/` | 跨场景 WRAM (128KB) + VRAM + CGRAM | 17 |
| `wram_raw/` | 原始 WRAM 转储 | 3 |
| `wram_state/` | **游戏状态变量解析: 1104个变量** | 17 |

**关键WRAM地址**:
- `$7E0447`: 帧计数器
- `$7E07C7`: 场景ID
- `$7E0228-022C`: 玩家位置
- `$7E2000-$7E3FFF`, `$7E6000-$7EFFFF`: 完全静态区域

### 音频数据

| 目录 | 内容 | 场景数 |
|------|------|--------|
| `brr_samples/` | BRR 音频样本 (WAV) | 3 |
| `brr_extended/` | 扩展 SPC700 完整状态 | 12 |
| `spc_data/` | SPC700 RAM/ROM/DSP | - |

### ROM 数据

| 目录 | 内容 |
|------|------|
| `rom_text/` | ROM 文本: 28,517 SJIS + 15,580 ASCII 字符串 |
| `rom_analysis/` | ROM 结构: 34 数据 bank, 94 代码 bank, 熵分析 |
| `rom_graphics/` | **ROM图形: 101 PNG瓦片表, 59个瓦片区域, LZSS/RLE解压** |
| `rom_tables/` | **ROM数据表: 1213真实表, 11226指针表, 3159字符串** |

### SRAM 数据

| 目录 | 内容 |
|------|------|
| `sram_data/` | 9场景8KB SRAM转储 (均为零值, 游戏未存档) |

### 截图与视觉素材

| 目录 | 内容 |
|------|------|
| `screenshots/` | 游戏截图 |
| `layers/` | 分层渲染截图 |
| `sprite_extract/` | 精灵提取 |
| `battle_extract/` / `battle_output/` | 战斗场景截图 |
| `worldmap/` / `worldmap_extract/` | 世界地图截图 |
| `panorama/` | 全景截图 |

## 控制按钮映射

| 按钮 | 功能 |
|------|------|
| X | 调查/检视 ("眼前并没有人…") |
| Select | 打开配置菜单 (战斗模式/信息速度/动画/声道等 7 项) |
| Start | 在配置菜单中保存 |
| Select + Start | 重置设置 |
| A | 确认/交互 |
| B | 取消/关闭 |

## 配置菜单选项

| 选项 | 说明 |
|------|------|
| 戦闘モード | 战斗模式 |
| メッセージスピード | 信息速度 (SLW/MED/FST) |
| 行動方式 | 行动方式 (TURNS/ROUND) |
| 戦闘アニメ | 战斗动画 (ON/OFF) |
| 戦車−障害物降下時 | 战车遇阻行为 |
| 地名表示 | 地名显示方式 |
| サウンドチャンネル | 声道设定 (STEREO/MONO) |

## 文件统计

- 总文件数: ~2800+
- 总数据量: ~45 MB
- PNG 图片: ~2100 张
- BIN 二进制: ~600 个
- 提取脚本: 15+ Lua + Python
- 二进制数据: VRAM (64KB), WRAM (128KB), SPC RAM (64KB), CGRAM (512B), DSP (128B), SRAM (8KB)

## 技术限制

- SNES PPU 寄存器 ($2105-$2131) 为只写, 无法通过 Mesen2 读取
- `emu.addMemoryCallback` 在 Mesen2 2.1.1 中不可用
- `emu.memType.snesOam` 返回 nil, 无法读取 OAM 数据
- `SDL_AUDIODRIVER=dummy` 导致 DSP KON=0, 无活跃音频通道
- 帧数超过 ~20000 时 Mesen2 可能崩溃, 脚本限制在 19500 帧内
- SRAM 全零: 游戏从未存档, 需通过 Select→Start 在配置菜单保存
