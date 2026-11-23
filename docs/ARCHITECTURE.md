# 代码结构 / Architecture

## 设计原则

《深渊回廊》刻意保持为**单文件游戏**：`abyss_corridor.py` 同时包含数据表、运行状态、输入、更新、渲染和打包入口。这样做的好处是：

- 没有模块导入地狱，fork 后可以直接运行
- 所有数值、文本和视觉映射都在一个文件里，适合快速做玩法实验
- PyInstaller 打包简单，不依赖额外资源目录

代价是文件较大（约 1.2 万行），因此下面按系统拆分说明。

## 主要系统

### 1. 启动与显示

- `boot()`：初始化 pygame、窗口、字体、音频、手柄和存档。
- `apply_display()`：切换窗口 / 全屏。
- 逻辑分辨率固定为 `1280 × 760`，窗口可缩放。
- `asset_path()` 兼容源码运行和 PyInstaller `_MEIPASS`。

### 2. 输入

- 键盘、鼠标、手柄统一进入 `G` 状态。
- `T` 在鼠标瞄准与自动索敌之间切换。
- 主炮自动开火，玩家只需移动、瞄准和放技能。
- `Shift` / LB 用于减速穿弹。

### 3. 一局游戏的状态

- `new_run(ship_id)`：创建一局新的 `Run`。
- `Run` 保存层数、波次、分数、增幅、契约、子弹和掉落等本局数据。
- `update(dt)`：推进玩家、敌机、弹幕、碰撞、掉落和层事件。
- `draw_scene(dt)`：按世界、道具、敌机、玩家、弹幕、HUD 的顺序绘制。

### 4. 飞船数据

三张核心表：

- `SHIP_LOOKS`：40 艘船的船体、翼型、纹样、颜色和尺寸。
- `SHIP_IDENTITIES`：40 条唯一特性名与短描述。
- `SHIP_PATTERN_NAMES`：17 种基础弹道的显示名。

选船界面用同一套数据生成 34px 缩略图和 3 倍详情模型，避免“名字、模型、弹道”三者脱节。

### 5. 弹道与技能

- `do_fire()`：根据 `pat` 生成基础弹道。
- `cast_skill()`：根据 `sk['id']` 执行飞船技能。
- `draw_bullets()`：按 `kind` 绘制普通弹、激光、月刃等不同形态。

v3.5.0 的关键修正：

- `blade` 本体从“1 中心 + 2 侧射”的三条枪线，改为两道交叉小月刃。
- `rift` 技能按飞船分流：裂空 3 柄大月刃、云雀 2 柄细刃 + 冲刺、环刃 2 柄回旋刃、断潮 3 道宽刃。
- `kind='blade'` 使用多边形绘制独立刃形，普攻小刃、技能大刃。

### 6. 内容表

- `AUGS`：196 项增幅
- `LAYER_EVENTS`：73 个层事件
- `MUTS`：76 条突变
- `PACTS`：12 份契约
- `ACHIEVEMENTS`：55 个成就
- `SHIPS`：40 艘船
- BOSS / 敌机：28 / 36 种

所有内容使用稳定 `id`，启动时做唯一性检查，避免重复卡名和重复奖励。

### 7. 存档

- 绿色版：`saves/save.json`、`saves/slot1.json` ~ `slot3.json`
- 可用 `ABYSS_SAVE` 环境变量指定主存档路径
- 音频缓存：`saves/audio_cache/`
- 崩溃日志：`saves/crash.log`
- 写入采用临时文件 + 替换，避免半截 JSON

### 8. 渲染与性能

- 地图、星空、视差层和大部分 UI 都是即时绘制。
- 弹幕数量大时避免每帧创建新 Surface；重复图形尽量缓存。
- 深层地图面积增大，但控制同屏敌机和粒子上限。
- `--selftest` 会跑 40 艘船各 900 帧，用于回归弹道、场景和渲染。

## 打包

GitHub Actions 使用 PyInstaller onedir：

```powershell
pyinstaller --noconfirm --clean --windowed --onedir --name AbyssCorridor abyss_corridor.py
```

产物目录：

```text
dist/AbyssCorridor/
├─ AbyssCorridor.exe
└─ _internal/
```

不要把 `saves/`、测试截图和旧版 exe 打进发布包。

## 扩展建议

- 新飞船：同时补 `SHIPS`、`SHIP_LOOKS`、`SHIP_IDENTITIES` 和技能分支。
- 新弹道：在 `do_fire()` 加分支，在 `draw_bullets()` 加绘制。
- 新层事件：加到 `LAYER_EVENTS`，保持 id 唯一，并补中英文。
- 新 BOSS：优先复用现有行为组合，再替换弹幕和阶段阈值，避免只改血量和颜色。
