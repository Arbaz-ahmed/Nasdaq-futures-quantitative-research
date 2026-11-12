@echo off
setlocal
cd /d "%~dp0"
start "NQ Futures Research Dashboard" "Open_Dashboard.html"
echo Browser dashboard opened. If the data cannot load automatically,
echo download the CSV source linked in README.md, then use Import CSV.
exit /b 0
