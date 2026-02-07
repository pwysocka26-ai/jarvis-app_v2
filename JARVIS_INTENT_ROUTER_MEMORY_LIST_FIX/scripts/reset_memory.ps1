# Reset pamięci Jarvisa (usuwa plik memory.json jeśli istnieje)
$paths = @(
  ".\\app\\data\\memory.json",
  ".\\data\\memory.json",
  ".\\memory.json"
)
foreach($p in $paths){
  if(Test-Path $p){
    Write-Host "Usuwam $p" -ForegroundColor Yellow
    Remove-Item $p -Force
  }
}
Write-Host "OK" -ForegroundColor Green
