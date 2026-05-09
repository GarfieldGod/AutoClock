#!/bin/bash

# Docker打包脚本 - 在Ubuntu 20.04容器中打包，确保兼容性

APT_MIRROR=""

for arg in "$@"; do
    case "$arg" in
        --aliyun)
            APT_MIRROR="mirrors.aliyun.com"
            ;;
        -h|--help)
            echo "用法: $0 [--aliyun]"
            echo "  --aliyun   使用阿里云APT镜像源构建Docker镜像"
            exit 0
            ;;
        *)
            echo "错误: 未知参数 $arg"
            echo "可用参数: --aliyun"
            exit 1
            ;;
    esac
done

echo "================================"
echo "Docker环境打包 Auto-Clock"
echo "================================"
echo ""

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: 未找到Docker"
    echo "请先安装Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

# 构建Docker镜像
echo "步骤1: 构建Docker镜像..."
if [ -n "${APT_MIRROR}" ]; then
    echo "使用APT镜像源: ${APT_MIRROR}"
    docker build --build-arg APT_MIRROR=${APT_MIRROR} -f Dockerfile.build -t auto-clock-builder .
else
    echo "使用默认APT官方源"
    docker build --build-arg APT_MIRROR= -f Dockerfile.build -t auto-clock-builder .
fi

if [ $? -ne 0 ]; then
    echo "Docker镜像构建失败"
    exit 1
fi

# 在容器中打包
echo ""
echo "步骤2: 在Docker容器中打包应用..."
HOST_UID=$(id -u)
HOST_GID=$(id -g)
docker run --rm \
  -e HOST_UID=${HOST_UID} \
  -e HOST_GID=${HOST_GID} \
  -v "$(pwd)/dist:/build/dist" \
  auto-clock-builder

if [ $? -ne 0 ]; then
    echo "打包失败"
    exit 1
fi

# 检查结果 (onedir)
if [ -f "dist/auto_clock/auto_clock" ]; then
    echo ""
    echo "================================"
    echo "打包成功！"
    echo "================================"
    echo ""
    echo "可执行文件: dist/auto_clock/auto_clock"
    echo "Runner: dist/auto_clock/auto-clock-runner"
    echo ""
    echo "检查GLIBC依赖:"
    ldd dist/auto_clock/auto_clock | grep GLIBC || echo "  (无GLIBC依赖显示)"
    echo ""
    echo "此版本应该可以在 Ubuntu 20.04+ 系统上运行"
else
    echo "打包失败，未找到可执行文件 dist/auto_clock/auto_clock"
    exit 1
fi
