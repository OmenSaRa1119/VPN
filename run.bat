@echo off
cd /d "C:\Users\ricky\Projects\vpn-app"
pip install -r requirements.txt >nul 2>&1
python vpn.py
pause