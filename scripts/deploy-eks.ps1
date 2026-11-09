# Despliega la aplicacion en el cluster EKS creado con Terraform.
# Uso: .\scripts\deploy-eks.ps1 -Tag v1
param(
  [string]$Tag = "v1",
  [string]$Region = "us-east-1",
  [string]$Cluster = "globalbank-eks"
)

function Check($msg) { if ($LASTEXITCODE -ne 0) { throw $msg } }

$account = aws sts get-caller-identity --query Account --output text
Check "Credenciales de AWS no validas: copia unas nuevas del Learner Lab"
$registry = "$account.dkr.ecr.$Region.amazonaws.com"

aws eks update-kubeconfig --region $Region --name $Cluster --alias $Cluster | Out-Null
Check "No se pudo configurar kubectl para $Cluster"
kubectl config use-context $Cluster | Out-Null
Check "No existe el contexto $Cluster"
Write-Host "Contexto de kubectl: $(kubectl config current-context)"

Write-Host "==> Almacenamiento (local-path) y metrics-server"
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.30/deploy/local-path-storage.yaml
Check "No se pudo instalar local-path-provisioner"
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
Check "No se pudo instalar metrics-server"

Write-Host "==> Namespace y secretos"
kubectl apply -f k8s/base/00-namespace.yaml
Check "No se pudo crear el namespace"
if (-not (Test-Path .env)) { throw "Falta el archivo .env con DB_PASSWORD y LOADGEN_TOKEN" }
Get-Content .env | ForEach-Object { if ($_ -match '^\s*([A-Z_]+)=(.*)$') { Set-Variable -Name $Matches[1] -Value $Matches[2] } }
kubectl -n globalbank create secret generic globalbank-secrets --from-literal=DB_PASSWORD=$DB_PASSWORD --from-literal=LOADGEN_TOKEN=$LOADGEN_TOKEN --dry-run=client -o yaml | kubectl apply -f -
Check "No se pudo crear el secreto"

Write-Host "==> Aplicacion (imagenes $registry, tag $Tag)"
$manifest = kubectl kustomize k8s/overlays/eks
Check "kustomize fallo"
$manifest = $manifest -replace "ECR_REGISTRY", $registry -replace "IMAGE_TAG", $Tag
$manifest | kubectl apply -f -
Check "kubectl apply fallo"

kubectl -n globalbank rollout status statefulset/postgres --timeout=300s
Check "Postgres no quedo listo"
foreach ($d in "backend", "loadgen", "clusterview", "frontend") {
  kubectl -n globalbank rollout status deployment/$d --timeout=300s
  Check "El despliegue $d no quedo listo"
}

Write-Host "==> Esperando el LoadBalancer (puede tardar 2-3 minutos)"
$lb = ""
for ($i = 0; $i -lt 36 -and -not $lb; $i++) {
  $lb = kubectl -n globalbank get svc frontend -o jsonpath="{.status.loadBalancer.ingress[0].hostname}"
  if (-not $lb) { Start-Sleep -Seconds 5 }
}
if ($lb) { Write-Host "URL: http://$lb  (el DNS puede tardar unos minutos mas en resolver)" }
else { Write-Host "El LoadBalancer aun no tiene direccion: revisa con kubectl -n globalbank get svc frontend" }
