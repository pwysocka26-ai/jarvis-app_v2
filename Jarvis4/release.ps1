param(
  [string]$CommitMessage = ""
)

$ErrorActionPreference = "Stop"

# --- Config (fixed workflow) ---
$WorkBranch = "work"
$MainBranch = "main"
$TagPrefix  = "v"  # date tags: vYYYY-MM-DD

function Assert-Git {
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git nie jest dostępny w PATH. Otwórz nowe okno PowerShell po instalacji Gita."
  }
}

function Ensure-Branches {
  if (-not (Test-Path ".git")) { throw "Brak .git w tym folderze. Uruchom w katalogu projektu (Jarvis4)." }

  $branches = git branch --list | ForEach-Object { $_.Trim().TrimStart('*').Trim() }

  if ($branches -notcontains $MainBranch) {
    if ($branches -contains "master") {
      git branch -M "master" $MainBranch | Out-Null
    } else {
      git branch -M $MainBranch | Out-Null
    }
  }

  $branches = git branch --list | ForEach-Object { $_.Trim().TrimStart('*').Trim() }
  if ($branches -notcontains $WorkBranch) {
    git checkout -b $WorkBranch | Out-Null
  }
}

function Get-TodayTag {
  return "$TagPrefix$((Get-Date).ToString('yyyy-MM-dd'))"
}

function Get-NextTag([string]$baseTag) {
  $existing = git tag --list "$baseTag*" | ForEach-Object { $_.Trim() }
  if ($existing -notcontains $baseTag) { return $baseTag }
  $i = 1
  while ($true) {
    $cand = "$baseTag-$i"
    if ($existing -notcontains $cand) { return $cand }
    $i++
  }
}

function Ensure-Clean-Commit {
  git add -A | Out-Null
  $status = git status --porcelain
  if ($status) {
    if (-not $CommitMessage) {
      $CommitMessage = "checkpoint: $((Get-Date).ToString('yyyy-MM-dd HH:mm'))"
    }
    git commit -m $CommitMessage | Out-Null
  }
}

function Merge-Work-Into-Main {
  $current = (git rev-parse --abbrev-ref HEAD).Trim()
  if ($current -ne $WorkBranch) {
    git checkout $WorkBranch | Out-Null
  }

  Ensure-Clean-Commit

  git checkout $MainBranch | Out-Null
  git merge --no-ff $WorkBranch -m "merge: $WorkBranch -> $MainBranch" | Out-Null
}

function Tag-Release {
  $baseTag = Get-TodayTag
  $tag = Get-NextTag $baseTag
  git tag $tag
  Write-Host "✅ Utworzono tag wersji: $tag"
}

Assert-Git
Ensure-Branches
Merge-Work-Into-Main
Tag-Release

Write-Host ""
Write-Host "Ostatnie commity:"
git log --oneline --decorate -8
Write-Host ""
Write-Host "Gotowe. Teraz możesz dalej pracować na branchu 'work' (git checkout work)."
