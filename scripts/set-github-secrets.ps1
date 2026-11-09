# Copia las credenciales vigentes del Learner Lab a los secretos del repositorio en GitHub.
# Hay que repetirlo cada vez que se inicia una sesion nueva del laboratorio.
# Requiere GitHub CLI:  winget install GitHub.cli   y luego   gh auth login
# Uso: .\scripts\set-github-secrets.ps1
param(
  [string]$Repo = "DiegoRivas1/cloud-globalbank-aws"
)

$credFile = Join-Path $env:USERPROFILE ".aws\credentials"
if (-not (Test-Path $credFile)) { throw "No existe $credFile" }

$map = @{}
Get-Content $credFile | ForEach-Object {
  if ($_ -match '^\s*(aws_access_key_id|aws_secret_access_key|aws_session_token)\s*=\s*(.+?)\s*$') {
    $map[$Matches[1]] = $Matches[2]
  }
}
foreach ($k in "aws_access_key_id", "aws_secret_access_key", "aws_session_token") {
  if (-not $map.ContainsKey($k)) { throw "Falta $k en $credFile" }
}

gh auth status 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Ejecuta primero: gh auth login" }

gh secret set AWS_ACCESS_KEY_ID --repo $Repo --body $map["aws_access_key_id"]
if ($LASTEXITCODE -ne 0) { throw "No se pudo guardar AWS_ACCESS_KEY_ID" }
gh secret set AWS_SECRET_ACCESS_KEY --repo $Repo --body $map["aws_secret_access_key"]
if ($LASTEXITCODE -ne 0) { throw "No se pudo guardar AWS_SECRET_ACCESS_KEY" }
gh secret set AWS_SESSION_TOKEN --repo $Repo --body $map["aws_session_token"]
if ($LASTEXITCODE -ne 0) { throw "No se pudo guardar AWS_SESSION_TOKEN" }

Write-Host "Secretos actualizados en $Repo"
