# Construye las 4 imagenes y las publica en ECR.
# Uso: .\scripts\push-images.ps1 -Tag v1
param(
  [string]$Tag = "v1",
  [string]$Region = "us-east-1"
)

$account = aws sts get-caller-identity --query Account --output text
if ($LASTEXITCODE -ne 0) { throw "Credenciales de AWS no validas: copia unas nuevas del Learner Lab" }
$registry = "$account.dkr.ecr.$Region.amazonaws.com"

aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $registry
if ($LASTEXITCODE -ne 0) { throw "docker login en ECR fallo" }

foreach ($c in "backend", "frontend", "loadgen", "clusterview") {
  $image = "$registry/globalbank/${c}:$Tag"
  Write-Host "==> $image"
  docker build -t $image "app/$c"
  if ($LASTEXITCODE -ne 0) { throw "docker build fallo para $c" }
  docker push $image
  if ($LASTEXITCODE -ne 0) { throw "docker push fallo para $c" }
}

Write-Host "Listo: imagenes publicadas con el tag $Tag en $registry"
