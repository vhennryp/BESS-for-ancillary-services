python -m venv .venv; 
.\.venv\Scripts\python.exe -m pip install --upgrade pip; 
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

If you run the code in PowerShell:

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1