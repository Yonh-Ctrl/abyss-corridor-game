# 发布流程 / Release Guide

## 当前版本

- 版本：`v3.5.0`
- 平台：Windows 10/11 64-bit
- 包名：`AbyssCorridor-v3.5.0-win64.zip`
- 当前本地构建 SHA256：`985D4C4AD2BE71AFE58276840067DE82B0E85C8247C699AA09BA2F011B307011`
- GitHub Actions 重新构建后，以 Release 页面显示的 SHA256 为准

## 方式一：GitHub Actions 自动构建

仓库内置 `.github/workflows/build-release.yml`。推送版本标签即可：

```powershell
git tag v3.5.0
git push origin v3.5.0
```

工作流会：

1. 在 `windows-latest` 上安装 Python 3.13；
2. 安装 `pygame` 与 `pyinstaller`；
3. 构建 onedir 包；
4. 压缩为 `AbyssCorridor-v3.5.0-win64.zip`；
5. 创建 GitHub Release 并附加 zip。

也可以在 Actions 页面手动运行 `Build Windows release`，先下载 artifact 检查，再决定是否打标签。

## 方式二：本地构建

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean --windowed --onedir --name AbyssCorridor abyss_corridor.py
Compress-Archive -Path dist\AbyssCorridor\* -DestinationPath AbyssCorridor-v3.5.0-win64.zip
```

## 发布前检查

- [ ] `python -m py_compile abyss_corridor.py` 通过
- [ ] `python abyss_corridor.py --selftest` 无 FAIL
- [ ] 解压后双击 `AbyssCorridor.exe` 能启动
- [ ] 包内没有 `saves/`、`last_start.txt`、测试截图和旧版 exe
- [ ] `LICENSE` / `NOTICE` 已随包附带
- [ ] GitHub Release 说明里写清楚版本、平台、SHA256 和已知问题
- [ ] 需要时附上 `RELEASE_NOTES.md`

## 包内建议结构

```text
AbyssCorridor-v3.5.0-win64/
├─ AbyssCorridor.exe
├─ _internal/
├─ LICENSE.txt
└─ RELEASE_NOTES.md
```

不要包含：

- `saves/`
- `last_start.txt`
- `build/`、`dist/` 中间目录
- 旧版本 exe
- 测试存档和桌面截图
