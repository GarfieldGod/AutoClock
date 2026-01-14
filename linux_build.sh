#!/bin/bash

# Auto-Clock Linux打包脚本
# 用于在Linux系统上打包应用程序

echo "================================"
echo "Auto-Clock Linux 打包脚本"
echo "================================"
echo ""

# 检查是否安装了PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "错误: 未找到 PyInstaller"
    echo "请先安装: pip install pyinstaller"
    exit 1
fi

# 检查Python版本
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python版本: $PYTHON_VERSION"

# 检查是否安装了必要的依赖
echo "检查依赖..."
if ! python3 -c "import PyQt5" 2>/dev/null; then
    echo "警告: PyQt5 未安装，请运行: pip install -r requirements.txt"
fi

# 清理之前的构建
echo ""
echo "清理之前的构建文件..."
rm -rf build
# 清理dist目录内容，但保留目录本身（因为可能被Docker挂载）
if [ -d "dist" ]; then
    rm -rf dist/* 2>/dev/null || true
fi

# 开始打包
echo ""
echo "开始打包应用程序..."
pyinstaller --clean --noconfirm pack_linux.spec

# 检查打包是否成功
if [ -f "dist/auto_clock/auto_clock" ]; then
    echo ""
    echo "设置驱动文件执行权限..."
    # 查找并设置所有msedgedriver文件的执行权限
    find dist -name "msedgedriver" -type f -exec chmod +x {} \;

    if [ ! -f "dist/auto_clock/auto-clock-runner" ]; then
        echo ""
        echo "================================"
        echo "打包失败！"
        echo "================================"
        echo "缺少runner可执行文件: dist/auto_clock/auto-clock-runner"
        exit 1
    fi
    
    echo ""
    echo "================================"
    echo "打包成功！"
    echo "================================"
    echo ""
    echo "可执行文件位置: dist/auto_clock/auto_clock"
    echo "Runner位置: dist/auto_clock/auto-clock-runner"
    echo ""
    echo "使用方法:"
    echo "  1. 图形界面模式:"
    echo "     ./dist/auto_clock/auto_clock"
    echo ""
    echo "  2. 无头模式执行任务:"
    echo "     ./dist/auto_clock/auto_clock --headless --task_id=YOUR_TASK_ID"
    echo ""
    echo "  3. 任务模式:"
    echo "     ./dist/auto_clock/auto_clock --task_id=YOUR_TASK_ID"
    echo ""
    echo "注意事项:"
    echo "  - 首次运行需要配置 config.json"
    echo "  - 驱动文件执行权限已自动设置"
    echo "  - 某些操作可能需要 sudo 权限"
    echo ""
else
    echo ""
    echo "================================"
    echo "打包失败！"
    echo "================================"
    echo "请检查上面的错误信息"
    exit 1
fi
