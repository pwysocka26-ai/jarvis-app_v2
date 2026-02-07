@echo off
REM Helper for Windows users with restrictive PowerShell execution policy.
REM Runs start_local.ps1 with ExecutionPolicy Bypass.
powershell -ExecutionPolicy Bypass -File "%~dp0start_local.ps1"
