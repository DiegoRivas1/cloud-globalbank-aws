# GlobalBank Cluster Lab

Aplicación bancaria de demostración, **cloud-native**, desplegada en **Amazon EKS**, con un panel web para
generar tráfico y ver en vivo el balanceo entre pods, el autoscaling (HPA) y la recuperación ante fallos.

Proyecto Integrador de Cloud Computing, Universidad Nacional de San Agustín (UNSA).

## Qué se hizo

- **Aplicación en 5 servicios:** `backend` (Flask/gunicorn, API bancaria con importes en centavos y transferencias
  atómicas), `postgres` (StatefulSet con PVC), `loadgen` (generador de carga dentro del clúster), `clusterview`
  (estado de pods/HPA/eventos y eliminación de pods del backend) y `frontend` (nginx + panel con Chart.js).
- **Panel interactivo:** envía ráfagas y muestra qué pod respondió cada petición, genera carga ajustable
  (tipo, RPS, duración), grafica RPS, latencia y número de pods, y muestra el estado del clúster en tiempo real.
- **Pruebas:** 91 pruebas con pytest (unitarias, API e integración contra PostgreSQL real, incluida una de
  concurrencia) y análisis estático con ruff.
- **Contenedores:** un Dockerfile por servicio; imágenes publicadas en Amazon ECR con el SHA del commit como tag.
- **Infraestructura como código:** Terraform crea los repositorios ECR y el clúster EKS (2 nodos `t3.medium`),
  usando el `LabRole` del Learner Lab.
- **Kubernetes:** Deployments, StatefulSet, Services, Secrets, sondas startup/readiness/liveness,
  requests/limits, `topologySpreadConstraints`, RBAC mínimo y HPA `autoscaling/v2`. Kustomize con
  overlays para `kind` (local) y `eks`.
- **CI/CD con GitHub Actions:** CI en cada PR (ruff, pruebas, build de imágenes, validación de Terraform y
  Kustomize); CD en cada push a `master` (publica en ECR, despliega en EKS y verifica el rollout).
  Una regla de protección de rama exige que el CI pase antes de fusionar.

## Resultados

| Prueba | Resultado |
|--------|-----------|
| Balanceo (500 peticiones, 3 pods) | Reparto prácticamente uniforme entre pods |
| HPA en EKS (carga `work`, 15 RPS) | 2 → 8 réplicas, 0 errores, latencia p50 ≈ 86 ms |
| Eliminación de un pod bajo carga | 1801 peticiones, 0 errores, pod de reemplazo listo en ≈ 8 s |
| Test roto en un PR (#9) | El CI falla y bloquea el merge |
| Lint roto en un PR | ruff falla y bloquea el merge |
| Merge a `master` | CD despliega solo; la versión del panel coincide con el SHA |

## Decisiones y problemas resueltos

- **Balanceo visible:** nginx no usa `keepalive` hacia el backend, así cada petición abre una conexión nueva y
  kube-proxy reparte entre pods sin sesgo.
- **Variables de entorno de Services:** Kubernetes inyectaba `BACKEND_PORT=tcp://...` y rompía la plantilla de nginx;
  se resolvió con `enableServiceLinks: false` y variables `*_ADDR`.
- **Concurrencia:** las transferencias usan un `UPDATE` atómico en la base de datos, con prueba de integración.
- **Learner Lab:** sin crear roles IAM; credenciales temporales renovadas en GitHub con `scripts/set-github-secrets.ps1`.
- **Costos:** 2 nodos pequeños (~0,18 USD/h) y destrucción de todo al terminar.

## Estructura

```
app/         backend, loadgen, clusterview, frontend (Dockerfile y tests en cada uno)
k8s/         base/ y overlays/ (kind, eks) con Kustomize
terraform/   ECR y EKS
scripts/     push-images.ps1, deploy-eks.ps1, set-github-secrets.ps1
.github/     workflows de CI y CD
docs/        evidencias (kubectl, ECR)
```

## Cómo ejecutarlo

**Local (Docker Compose):**

```powershell
Copy-Item .env.example .env      # define DB_PASSWORD y LOADGEN_TOKEN
docker compose up -d --build     # panel en http://localhost:8080
```

**Kubernetes local (kind):**

```powershell
kind create cluster --name globalbank --config k8s\kind-config.yaml
kubectl apply -k k8s\overlays\kind     # panel en http://localhost:8090
```

**AWS (Learner Lab):**

```powershell
terraform -chdir=terraform init
terraform -chdir=terraform apply
.\scripts\push-images.ps1
.\scripts\deploy-eks.ps1
# al terminar
kubectl delete -k k8s\overlays\eks
terraform -chdir=terraform destroy
```

## Seguridad

Sin credenciales en el repositorio (`.env`, `*.tfvars` y `tfplan` ignorados); secretos de AWS en GitHub Actions;
endpoints de control protegidos con token y límites de carga; RBAC acotado para `clusterview`.