resource "aws_secretsmanager_secret" "github"{
    name = "github-secrets-to-aws/demo"
    description = "Demo secrets synchronized from GitHub Actions"
    recovery_window_in_days = 7

    tags = {
        service = "github-secrets-to-aws"
    }
}