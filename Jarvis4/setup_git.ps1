param(
  [string]$RepoName = "Jarvis4",
  [string]$DefaultBranch = "main"
)

$ErrorActionPreference = "Stop"

function Ensure-Git {
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Nie widzę Gita w PATH. Zamknij/otwórz PowerShell po instalacji albo zainstaluj Git for Windows."
  }
}

function Write-Gitignore {
  $content = @"
# ========================
# Python
# ========================
__pycache__/
*.py[cod]
*.pyo
*.pyd
*.so
*.egg-info/
.eggs/

# ========================
# Virtual environments
# ========================
.venv/
venv/
ENV/
env/

# ========================
# Runtime / local data
# ========================
*.db
*.sqlite
*.log
logs/
data/memory/**
data/users/**
!data/**/.gitkeep

# ========================
# Secrets / env
# ========================
.env
.env.*
*.secret
*.key

# ========================
# OS
# ========================
.DS_Store
Thumbs.db

# ========================
# IDE / Editors
# ========================
.vscode/
.idea/
*.swp
*.swo

# ========================
# Test / coverage
# ========================
.coverage
htmlcov/
.pytest_cache/

# ========================
# Build / dist
# ========================
build/
dist/
"@

  $path = Join-Path (Get-Location) ".gitignore"
  $content | Out-File -Encoding utf8 $path
}

function Ensure-Gitkeep {
  $paths = @("data\users", "data\memory")
  foreach ($p in $paths) {
    if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force $p | Out-Null }
    $keep = Join-Path $p ".gitkeep"
    if (-not (Test-Path $keep)) { New-Item -ItemType File -Force $keep | Out-Null }
  }
}

function Ensure-Repo {
  if (-not (Test-Path ".git")) {
    git init | Out-Null
  }
  git config --global init.defaultBranch $DefaultBranch | Out-Null
  $branch = (git rev-parse --abbrev-ref HEAD 2>$null)
  if ($branch -eq "master") {
    git branch -M $DefaultBranch | Out-Null
  }
}

function Ensure-Identity {
  $name = (git config user.name)
  $email = (git config user.email)
  if (-not $name)  { git config user.name "Paulina" | Out-Null }
  if (-not $email) { git config user.email "paulina@local" | Out-Null }
}

function Ensure-InitialCommit {
  $hasCommits = $true
  try { git rev-parse HEAD | Out-Null } catch { $hasCommits = $false }

  if (-not $hasCommits) {
    git add . | Out-Null
    git commit -m "chore: initial baseline" | Out-Null
  }
}

function Ensure-Tag {
  param([string]$Tag = "v0.1.0")
  $tags = git tag
  if ($tags -notcontains $Tag) {
    git tag $Tag
  }
}

Ensure-Git
Write-Gitignore
Ensure-Gitkeep
Ensure-Repo
Ensure-Identity

git add .gitignore data\users\.gitkeep data\memory\.gitkeep 2>$null | Out-Null
git commit -m "chore: add .gitignore and keep local data dirs" 2>$null | Out-Null

Ensure-InitialCommit
Ensure-Tag "v0.1.0"

Write-Host "✅ Git gotowy. Sprawdź:"
git log --oneline --decorate -5
git status
