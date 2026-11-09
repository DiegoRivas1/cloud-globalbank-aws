resource "aws_ecr_repository" "app" {
  for_each = toset(var.ecr_repositories)

  name                 = "${var.project}/${each.key}"
  image_tag_mutability = "MUTABLE"
  force_delete         = true # permite destruir el repositorio aunque tenga imágenes

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Conserva solo las últimas 10 imágenes para no acumular almacenamiento
resource "aws_ecr_lifecycle_policy" "app" {
  for_each   = aws_ecr_repository.app
  repository = each.value.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Conservar las ultimas 10 imagenes"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}
