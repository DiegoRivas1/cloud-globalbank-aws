# Infraestructura (Terraform)

Crea en AWS Academy Learner Lab:

- 4 repositorios **ECR** (`globalbank/backend`, `frontend`, `loadgen`, `clusterview`).
- Un clúster **EKS** con un grupo de nodos (`t3.medium`), reutilizando `LabRole`
  (el Learner Lab no permite crear roles IAM) y la VPC por defecto.

## Requisitos

- Terraform >= 1.5, AWS CLI y kubectl.
- Credenciales vigentes del Learner Lab en `~/.aws/credentials` (caducan al terminar la sesión).
  Verificar: `aws sts get-caller-identity`

## Crear

```powershell
cd terraform
terraform init
terraform validate
terraform plan -out tfplan
terraform apply tfplan          # el clúster tarda unos 10-15 minutos
aws eks update-kubeconfig --region us-east-1 --name globalbank-eks --alias globalbank-eks
kubectl get nodes
```

## Actualizar

Edita variables (`terraform.tfvars`) o los `.tf`, y luego `terraform plan` y `terraform apply`.

## Destruir (siempre al terminar la sesión)

```powershell
terraform destroy
```

El estado (`terraform.tfstate`) es local y está en `.gitignore`. Si se pierde antes de destruir,
hay que borrar a mano el clúster, el grupo de nodos y los repositorios en la consola de AWS.

## Costos aproximados

Plano de control de EKS (~0,10 USD/h) + 2 × t3.medium (~0,08 USD/h en total). Destruir al terminar.
