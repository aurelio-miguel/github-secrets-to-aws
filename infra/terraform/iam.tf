resource "aws_iam_role" "role-sync-github-secrets" {
  name = "role-sync-github-secrets"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRoleWithWebIdentity"

      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }

      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub" = var.github_oidc_subject
        }
      }
    }]
  })

  tags = {
    service = "github-secrets-to-aws"
  }
}

resource "aws_iam_role_policy" "write_secret" {
  name = "write-github-secret"
  role = aws_iam_role.role-sync-github-secrets.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "secretsmanager:PutSecretValue"
      Resource = aws_secretsmanager_secret.github.arn
    }]
  })
}