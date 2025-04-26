@echo off
pushd %~dp0

%1 mshta vbscript:CreateObject("Shell.Application").ShellExecute("cmd.exe","/c %~s0 ::","","runas",1)(window.close)&&exit

REM 运行主程序
py -m core.main

pause
exit 