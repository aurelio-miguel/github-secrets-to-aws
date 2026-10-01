# GitHub Secrets to AWS

Sync selected GitHub Actions secrets to AWS Secrets Manager using OpenID Connect (OIDC), IAM roles, and Terraform.

> **Status: planned / under development.** This README describes the intended implementation. The Terraform configuration, workflow, and synchronization script still need to be created and tested.

## Why this project?

Applications running on AWS may need secrets that are initially maintained in GitHub. This project demonstrates a controlled, one-way synchronization from a GitHub Actions workflow to AWS Secrets Manager, without storing long-lived AWS access keys in GitHub.

The repository will contain both the infrastructure as code and the workflow, making the example reproducible and documenting the permissions required at each stage.

## Scope and limitations

This project copies **explicitly selected secrets available to the workflow** through the GitHub Actions `secrets` context. The GitHub REST API returns secret metadata, not their stored values; this is not a tool for downloading arbitrary repository secrets.

OIDC authenticates the workflow to AWS. The IAM role grants access to the destination in AWS; it does not grant access to secrets in other GitHub repositories.

The initial example will use repository secrets and a manually triggered workflow. It will not provide bidirectional synchronization, automatic credential rotation, or automatic detection of GitHub secret changes.

## Intended architecture

1. Terraform provisions the destination secret container, IAM role, and permissions, and creates or reuses the GitHub OIDC provider.
2. A maintainer starts the synchronization workflow with `workflow_dispatch`.
3. GitHub Actions obtains an OIDC token and exchanges it for temporary AWS credentials through AWS STS.
4. The workflow passes an explicit selection of GitHub secrets to the synchronization script.
5. The script writes a JSON payload as a new version of the destination secret in AWS Secrets Manager.

Terraform manages the infrastructure and secret metadata. The workflow manages secret values, keeping those values out of Terraform configuration and state.

## Planned repository structure

```text
.github/workflows/
  sync-secrets.yml
infra/terraform/
  versions.tf
  providers.tf
  main.tf
  variables.tf
  outputs.tf
  terraform.tfvars.example
scripts/
  sync-secrets.py
tests/
  test_sync_secrets.py
.gitignore
README.md
```

The paths above are planned and may change during implementation.

## Initial configuration contract

The following names are proposed for the first implementation.

### GitHub Actions variables

| Variable | Purpose | Example |
| --- | --- | --- |
| `AWS_REGION` | AWS region containing the destination secret | `us-east-1` |
| `AWS_ROLE_ARN` | ARN of the IAM role assumed through OIDC | `arn:aws:iam::123456789012:role/github-secrets-sync` |
| `AWS_SECRET_ARN` | ARN of the destination secret created by Terraform | Terraform output |

These settings are configuration values, not AWS access credentials.

### GitHub Actions secrets

| Source secret | Destination JSON key |
| --- | --- |
| `DEMO_API_TOKEN` | `api_token` |
| `DEMO_DB_PASSWORD` | `db_password` |

Use fictional values while building and demonstrating the project.

The initial design stores both values in a single JSON secret. Each synchronization replaces the complete JSON payload; it does not merge with existing keys. Missing or empty required inputs must fail validation before any write.

## Planned setup

These steps describe the future setup process. They are not executable until the corresponding files have been implemented.

1. Clone this repository.
2. Authenticate locally to an AWS sandbox account using your preferred AWS profile or SSO session.
3. Configure Terraform with your AWS region, GitHub repository, allowed branch, and destination secret name.
4. Create or reuse the account's GitHub OIDC provider. Do not attempt to create a duplicate provider if one already exists.
5. Review and apply the Terraform plan.
6. Copy the role ARN and destination secret ARN from Terraform outputs into GitHub Actions variables.
7. Add the example source secrets in the repository settings.
8. Run the workflow manually from the authorized branch.
9. Verify the destination version in AWS using an identity with read permissions. Do not print secret values in workflow logs.

Example Terraform commands, once the files exist:

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your non-secret configuration.
terraform init
terraform fmt -check
terraform validate
terraform plan
terraform apply
```

Local Terraform credentials are required for the initial setup. The synchronization role cannot bootstrap itself before it exists.

## Authentication and permissions

The synchronization job will request `id-token: write` to obtain an OIDC token and `contents: read` to check out the script.

The IAM trust policy will restrict the token audience to `sts.amazonaws.com` and the subject to the intended repository and branch. If GitHub Environments are added later, the subject restriction must match the environment-based token format.

The runtime IAM policy will grant `secretsmanager:PutSecretValue` only for the destination secret. Additional permissions should be added only when an implemented operation requires them. A customer-managed KMS key may require additional KMS permissions; the initial example will use the service's default encryption key.

The Terraform provisioning identity has separate permissions to create and manage the infrastructure.

## Implementation safeguards

- Map only the selected source secrets; do not export the entire secrets context.
- Pass source values through environment variables and serialize them with a JSON library.
- Never log values, include them in artifacts, or enable shell tracing around secret handling.
- Use a protected branch and restrict who can modify or run the synchronization workflow.
- Pin third-party actions to reviewed commit SHAs.
- Keep `.terraform/`, Terraform state, plan files, local variable files, and `.env` files out of Git.
- Do not define Terraform secret-value resources for the synchronized payload.
- Configure workflow concurrency to avoid overlapping writes to the same destination.
- Report operation status without returning the secret payload.

## Roadmap

- [ ] Create Terraform configuration for the OIDC provider, IAM role, and destination secret.
- [ ] Support reuse of an existing OIDC provider.
- [ ] Add Terraform outputs and a non-secret variables example.
- [ ] Implement input validation and JSON serialization.
- [ ] Implement the Secrets Manager write operation.
- [ ] Create the manually triggered GitHub Actions workflow.
- [ ] Test missing inputs, special characters, and AWS write failures.
- [ ] Validate OIDC authentication in an AWS sandbox.
- [ ] Verify that unauthorized branches cannot assume the role.
- [ ] Run the workflow twice and verify the expected secret version behavior.
- [ ] Document setup, troubleshooting, costs, and cleanup with actual tested examples.

## Costs and cleanup

AWS Secrets Manager storage and API calls may incur charges. Review current AWS pricing before deploying.

The final cleanup guide must document the secret recovery window and the effect of removing Terraform-managed resources. Deleting the example infrastructure should not be treated as a step to run against shared or production resources.

## References

- [GitHub Actions secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
- [GitHub Actions Secrets REST API](https://docs.github.com/en/rest/actions/secrets)
- [Configuring OIDC in AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)
- [AWS credentials action](https://github.com/aws-actions/configure-aws-credentials)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html)
- [Terraform documentation](https://developer.hashicorp.com/terraform/docs)