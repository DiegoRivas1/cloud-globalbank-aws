# GlobalBank Cluster Lab

Aplicación bancaria de demostración, cloud-native, desplegada en **Amazon EKS** con un panel web para
generar tráfico, ver el balanceo entre pods, el escalado automático (HPA) y la recuperación ante fallos.

Proyecto Integrador de Cloud Computing (UNSA).

## Arquitectura

| Componente    | Tecnología              | Función                                                    |
|---------------|-------------------------|------------------------------------------------------------|
| `frontend`    | nginx + JS (Chart.js)   | Panel web y proxy hacia los demás servicios                |
| `backend`     | Flask + gunicorn        | API bancaria (`/api/cuenta`, `/api/transfer`, `/api/work`) |
| `postgres`    | PostgreSQL (StatefulSet)| Persistencia                                               |
| `loadgen`     | aiohttp                 | Generador de carga dentro del clúster                      |
| `clusterview` | aiohttp                 | Estado de pods/HPA/eventos; elimina pods del backend       |

Flujo de entrega: rama + PR → CI → merge a `master` → CD (build, push a ECR con tag = SHA, deploy a EKS).

## Estructura

```
app/            backend, loadgen, clusterview, frontend (cada uno con Dockerfile y tests)
k8s/            base/ y overlays/ (kind, eks) con Kustomize
terraform/      ECR y EKS
scripts/        push-images.ps1, deploy-eks.ps1, set-github-secrets.ps1
.github/        workflows ci.yml y cd.yml
docs/           evidencias (salidas de kubectl, ECR, etc.)
```

## Requisitos

Python 3.12, Docker, kubectl, kind, Terraform >= 1.5, AWS CLI, GitHub CLI (`gh`), PowerShell.

## Ejecución local con Docker Compose

```powershell
Copy-Item .env.example .env     # edita DB_PASSWORD y LOADGEN_TOKEN
docker compose up -d --build
```

Panel en http://localhost:8080 (3 réplicas del backend).

## Pruebas

```powershell
cd app\backend
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest
```

Lo mismo en `app\loadgen` y `app\clusterview`. Las pruebas de PostgreSQL se ejecutan en el CI
(servicio `postgres`). Análisis estático: `ruff check app`.

## Kubernetes local (kind)

```powershell
kind create cluster --name globalbank --config k8s\kind-config.yaml
kubectl apply -k k8s\overlays\kind
```

Panel en http://localhost:8090. Para metrics-server se usa `k8s/metrics-server-patch.json`.

## Despliegue en AWS (Learner Lab)

1. Iniciar el Lab y configurar credenciales en `~/.aws/credentials` (incluye `aws_session_token`).
2. Crear la infraestructura:

```powershell
terraform -chdir=terraform init
terraform -chdir=terraform plan -out tfplan
terraform -chdir=terraform apply tfplan
```

3. Publicar imágenes y desplegar:

```powershell
.\scripts\push-images.ps1
.\scripts\deploy-eks.ps1      # crea el Secret desde .env, aplica el overlay eks y muestra la URL del LB
```

4. Destruir al terminar (evita costos):

```powershell
kubectl delete -k k8s\overlays\eks   # libera el balanceador
terraform -chdir=terraform destroy
```

## CI/CD

- **CI** (`ci.yml`): ruff, pruebas (backend con PostgreSQL, loadgen, clusterview), build de las 4 imágenes,
  validación de Terraform y Kustomize. Se ejecuta en cada PR y es requisito para fusionar a `master`.
- **CD** (`cd.yml`): en cada push a `master` ejecuta el CI, publica las imágenes en ECR (tag = SHA corto),
  actualiza el clúster y verifica rollout y disponibilidad.

Los secretos de AWS se guardan en GitHub Actions. Con cada reinicio del Learner Lab hay que renovarlos:

```powershell
.\scripts\set-github-secrets.ps1
```

## Seguridad

- Sin credenciales en el repositorio (`.env`, `*.tfvars`, `tfplan` ignorados).
- Endpoints de control protegidos con token (`LOADGEN_TOKEN`) y con límites de carga.
- RBAC acotado para `clusterview`; Secrets de Kubernetes para contraseña y token.

## Demostración rápida

1. Cambiar código y abrir un PR; ver el CI.
2. Fusionar a `master`; ver el CD publicar y desplegar.
3. Abrir la URL del balanceador; la versión mostrada coincide con el SHA.
4. Generar carga desde el panel y observar el HPA (2 → 8 réplicas).
5. Eliminar un pod del backend y ver la recuperación sin errores.