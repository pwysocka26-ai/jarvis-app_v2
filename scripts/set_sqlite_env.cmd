@echo off
REM Switch DATABASE_URL back to SQLite (local file) in .env.local
REM Run from repo root:  scripts\set_sqlite_env.cmd

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0set_sqlite_env.ps1"
