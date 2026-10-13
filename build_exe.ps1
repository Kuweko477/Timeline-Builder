$ErrorActionPreference = "Stop"
python make_icon.py
python -m PyInstaller --noconfirm --clean --windowed `
  --name "Timeline Builder" `
  --icon assets\icon.ico `
  --add-data "assets;assets" `
  --collect-all pycapcut `
  --collect-submodules PIL `
  --exclude-module tkinter `
  main.py
Write-Host "Done: dist\Timeline Builder\Timeline Builder.exe"
