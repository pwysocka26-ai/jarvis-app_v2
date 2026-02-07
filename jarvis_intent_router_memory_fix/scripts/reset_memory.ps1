# Reset pamięci Jarvisa (Windows PowerShell)
$mem = "app\data\memory.json"
if (Test-Path $mem) {
  Remove-Item $mem -Force
  Write-Host "Usunięto $mem"
} else {
  Write-Host "Nie znaleziono $mem (OK)"
}
