@echo off
REM One-click wrapper to run the PowerShell script even when execution policy blocks unsigned .ps1
REM Run from repo root:  scripts\set_postgres_env.cmd

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0set_postgres_env.ps1"
