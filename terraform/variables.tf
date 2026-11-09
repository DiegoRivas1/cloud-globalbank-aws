variable "region" {
  description = "Región de AWS (el Learner Lab usa us-east-1)"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Prefijo para repositorios ECR y etiquetas"
  type        = string
  default     = "globalbank"
}

variable "cluster_name" {
  description = "Nombre del clúster EKS"
  type        = string
  default     = "globalbank-eks"
}

variable "kubernetes_version" {
  description = "Versión de Kubernetes. null = la última disponible al crear el clúster (la versión usada se ve en la salida)"
  type        = string
  default     = null
}

variable "availability_zones" {
  description = "Zonas de disponibilidad para los nodos (se evita us-east-1e, que EKS no soporta)"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "node_instance_type" {
  description = "Tipo de instancia de los nodos (el Learner Lab limita los tamaños grandes)"
  type        = string
  default     = "t3.medium"
}

variable "node_count" {
  description = "Número de nodos (el máximo del grupo es node_count + 1)"
  type        = number
  default     = 2
}

variable "ecr_repositories" {
  description = "Repositorios ECR a crear (uno por componente)"
  type        = list(string)
  default     = ["backend", "frontend", "loadgen", "clusterview"]
}
