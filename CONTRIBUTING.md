# Contributing

欢迎参与《深渊回廊》。这是一个单文件 pygame 项目，改动门槛低，但也容易在一个文件里引入回归，所以请尽量小步提交。

## 开发环境

- Windows 10/11 64-bit
- Python 3.10+，推荐 3.13
- pygame 2.6.1+
- 可选：PyInstaller 6.x（只做打包时）

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python abyss_corridor.py
```

## 提交前

```powershell
python -m py_compile abyss_corridor.py
python abyss_corridor.py --selftest
```

`--selftest` 会跑 40 艘船各 900 帧，耗时较长；如果只改文本，可以只跑 `py_compile`，但在 PR 里说明未跑完整自检。

## 适合的 PR

- 新飞船：同时补 `SHIPS`、`SHIP_LOOKS`、`SHIP_IDENTITIES` 和技能分支
- 新弹道：`do_fire()` 加分支，`draw_bullets()` 加绘制
- 新层事件 / 突变 / 契约：保持 id 唯一，补中英文
- 平衡调整：写清楚改动前后数值和测试场景
- 英文翻译：优先改 `EN` 映射，避免只改界面显示而漏掉查找表
- 性能：附上改前 / 改后帧率和弹幕数量

## 内容与素材

- 不要提交测试存档、旧版构建、构建缓存或桌面截图。
- 不要提交来源不明的美术、音频、字体或语音素材。
- 如果你加入第三方素材，请在 PR 中注明来源、许可证，并确认与 Apache-2.0 兼容。
- 游戏名、飞船名和世界观文本属于项目作者；新增文本请保持同一世界观语气。

## Issue

提交 Bug 时请附：

- 版本号（如 v3.5.0）
- 操作系统和 Python / exe 运行方式
- 复现步骤
- 期望结果和实际结果
- 如有可能，附 `saves/crash.log` 或截图

## Commit

建议使用简短的英文 commit message：

```text
fix: rift base pattern uses two blades
feat: add new breakwater skill form
docs: clarify save path
```
