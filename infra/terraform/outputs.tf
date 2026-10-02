output "secret_arn"{
    description = "ARN of the destination secret"
    value = aws_secretsmanager_secret.github.arn
}