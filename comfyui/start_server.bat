@echo off
chcp 65001 >nul
set UV=E:\TaiShen\ComfyUI\resources\uv\win\uv.exe
set DIR=E:\TaiShen\ComfyUI\resources\ComfyUI

echo ==============================================
echo  ComfyUI API Server -- 毛绒玩具设计助手
echo  GPU: RTX 5080 (Blackwell) → CUDA 12.6
echo ==============================================
echo.

echo [1/2] 安装 CUDA 12.6 版 PyTorch (适配 RTX 5080)...
"%UV%" pip install --reinstall torch torchvision torchaudio ^
    --index-url https://download.pytorch.org/whl/cu126 ^
    --directory "%DIR%"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 安装失败，请检查网络后重试。
    pause
    exit /b 1
)

echo.
echo [2/2] 验证 GPU...
"%UV%" run --directory "%DIR%" python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"

echo.
echo ==============================================
echo  启动服务器 → http://127.0.0.1:8188
echo  按 Ctrl+C 停止
echo ==============================================
echo.

"%UV%" run --directory "%DIR%" python main.py --listen 0.0.0.0 --port 8188
pause
