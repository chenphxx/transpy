# -*- mode: python ; coding: utf-8 -*-
#
# 打包配置。与旧版命令行的区别:
#   1. datas 带上整个 assets 目录, 保证托盘图标在打包后也能加载;
#   2. excludes 不再排除 PIL —— 托盘图标 (pystray) 依赖它;
#   3. 显式声明 pystray 的 Windows 后端为 hiddenimports, 避免被静态分析漏掉;
#   4. 写入版本资源, 让任务栏与文件属性显示 transpy 而不是 python。

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/images/logo.ico', 'assets/images')],
    hiddenimports=[
        'pystray._win32',
        'PIL.Image',
        'PIL.ImageDraw',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PySide2', 'PySide6'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='transpy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\images\\logo.ico'],
    version='version_info.txt',
)
