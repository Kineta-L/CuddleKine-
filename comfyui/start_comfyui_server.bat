@echo off
chcp 65001 >nul
echo ==============================================
echo  ComfyUI API Server -- 毛绒玩具设计助手
echo ==============================================
echo.

set COMFYUI_SRC=E:\TaiShen\ComfyUI\resources\ComfyUI
set UV=E:\TaiShen\ComfyUI\resources\uv\win\uv.exe

echo [1/3] 初始化 Python 环境 (首次需下载 torch ~2.5GB，约 5-10 分钟)...
"%UV%" run --directory "%COMFYUI_SRC%" python -c "import torch; print('torch:', torch.__version__); print('cuda:', torch.cuda.is_available())"
if %ERRORLEVEL% NEQ 0 (
    echo 环境就绪，正在安装依赖...
    cd /d "%COMFYUI_SRC%"
    "%UV%" sync
)

echo.
echo [2/3] 启动 ComfyUI API 服务器...
echo       地址: http://127.0.0.1:8188
echo       按 Ctrl+C 停止
echo.

cd /d "%COMFYUI_SRC%"
"%UV%" run python main.py --listen 0.0.0.0 --port 8188
