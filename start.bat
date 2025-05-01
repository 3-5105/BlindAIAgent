@echo off
%1 mshta vbscript:CreateObject("Shell.Application").ShellExecute("cmd.exe","/c %~s0 ::","","runas",0)(window.close)&&exit
pushd %~dp0

py -m core.main
::py -m core.monitor

pause
exit 