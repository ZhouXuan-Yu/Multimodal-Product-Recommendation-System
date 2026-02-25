@echo off
chcp 65001 >nul
call D:\Anaconda\condabin\activate.bat jin
echo Installing PyTorch with CUDA 12.8 for RTX 5060...
pip install --force-reinstall --index-url https://download.pytorch.org/whl/nightly/cu128 torch torchvision
pause

