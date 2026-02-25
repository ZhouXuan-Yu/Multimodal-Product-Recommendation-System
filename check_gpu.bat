@echo off
chcp 65001 >nul
call D:\Anaconda\condabin\activate.bat jin
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA version:', torch.version.cuda); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'); print('Capability:', torch.cuda.get_device_capability(0) if torch.cuda.is_available() else 'None')"
pause
