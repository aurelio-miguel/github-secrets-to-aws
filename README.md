# GitHub Secrets to AWS

Sync selected GitHub Actions secrets to AWS Secrets Manager using OpenID Connect (OIDC), IAM roles, and Terraform.

> **Status: under development.** The initial Terraform infrastructure has been applied successfully. The manually triggered GitHub Actions workflow and Python synchronization script are implemented; end-to-end OIDC authentication and secret synchronization have not yet been validated.

## Why this project?

Applications running on AWS may need secrets that are initially maintained in GitHub. This project demonstrates a controlled, one-way synchronization from a GitHub Actions workflow to AWS Secrets Manager, without storing long-lived AWS access keys in GitHub.

The repository will contain both the infrastructure as code and the workflow, making the example reproducible and documenting the permissions required at each stage.

## Scope and limitations

This project copies **explicitly selected secrets available to the workflow** through the GitHub Actions `secrets` context. The GitHub REST API returns secret metadata, not their stored values; this is not a tool for downloading arbitrary repository secrets.

OIDC authenticates the workflow to AWS. The IAM role grants access to the destination in AWS; it does not grant access to secrets in other GitHub repositories.

The initial example will use repository secrets and a manually triggered workflow. It will not provide bidirectional synchronization, automatic credential rotation, or automatic detection of GitHub secret changes.

## Intended architecture

1. Terraform provisions the destination secret container, IAM role, and permissions, and configures the GitHub OIDC provider. Reusing an existing provider requires explicit import or configuration changes.
2. A maintainer starts the synchronization workflow with `workflow_dispatch`.
3. GitHub Actions obtains an OIDC token and exchanges it for temporary AWS credentials through AWS STS.
4. The workflow passes an explicit selection of GitHub secrets to the synchronization script.
5. The script writes a JSON payload as a new version of the destination secret in AWS Secrets Manager.

Terraform manages the infrastructure and secret metadata. The workflow manages secret values, keeping those values out of Terraform configuration and state.

## Repository structure

The current Terraform files are:

| Path | Purpose |
| --- | --- |
| `infra/terraform/providers.tf` | AWS provider configuration and version requirements, if configured here |
| `infra/terraform/oidc.tf` | GitHub OIDC identity provider |
| `infra/terraform/iam.tf` | IAM role, OIDC trust policy, and inline Secrets Manager permissions |
| `infra/terraform/secrets.tf` | Destination secret container, without a secret value |
| `infra/terraform/variables.tf` | Input variable declarations |
| `infra/terraform/outputs.tf` | Terraform outputs, including `secret_arn` |
| `infra/terraform/terraform.tfvars` | Local input values; excluded from version control |
| `infra/terraform/.terraform.lock.hcl` | Provider dependency lock file; committed to version control |
| `.gitignore` | Excludes generated files and local configuration |
| `README.md` | Project documentation |

Synchronization files:

- `.github/workflows/sync-secrets.yml`: manually triggered synchronization workflow.
- `scripts/sync-secrets.py`: input validation and secret upload.
- `scripts/requirements.txt`: pinned boto3 dependency.
- `infra/terraform/terraform.tfvars.example`: reusable non-secret configuration example.

All Terraform configuration files belong in `infra/terraform/`. Terraform evaluates the `.tf` files in that directory as one module; filenames organize resources rather than determine execution order.

### Terraform input

Declare `github_oidc_subject` in `variables.tf` and assign its value in the local `terraform.tfvars` file:

```hcl
# terraform.tfvars
github_oidc_subject = "repo:aurelio-miguel@19332546/github-secrets-to-aws@1398887255:ref:refs/heads/main"
```

This is the configured subject for this project. Confirm it against the actual OIDC token's `sub` claim when running the workflow. If copying this example, replace it with your own exact subject. An environment-based workflow may require a different subject.

The subject is not a secret. Keep a portable example in `terraform.tfvars.example` using the included example. Any other required variables without defaults also need values. The current secret name is defined in `secrets.tf` as `github-secrets-to-aws/demo`; configure the AWS region in `providers.tf` according to its existing configuration.

### Generated local files

Terraform also produces `.terraform/`, `terraform.tfstate`, and potentially `terraform.tfstate.backup`. These are local working files and must not be committed. Keep `.terraform.lock.hcl` tracked.

## Initial configuration contract

The workflow and script use the following configuration.

### GitHub Actions variables

| Variable | Purpose | Example |
| --- | --- | --- |
| `AWS_REGION` | AWS region containing the destination secret | `us-east-1` |
| `AWS_ROLE_ARN` | ARN of the IAM role assumed through OIDC | `arn:aws:iam::123456789012:role/role-sync-github-secrets` |
| `AWS_SECRET_ARN` | ARN of the destination secret created by Terraform | Terraform output |

These settings are configuration values, not AWS access credentials.

### GitHub Actions secrets

| Source secret | Destination JSON key |
| --- | --- |
| `DEMO_API_TOKEN` | `api_token` |
| `DEMO_DB_PASSWORD` | `db_password` |

Use fictional values while building and demonstrating the project.

The initial design stores both values in a single JSON secret. Each synchronization replaces the complete JSON payload; it does not merge with existing keys. Missing or empty required inputs must fail validation before any write.

## Infrastructure setup

The initial infrastructure has been applied. The following steps describe how to provision it in another AWS account; configure the workflow after provisioning as described below.

1. Clone this repository.
2. Authenticate locally to an AWS sandbox account using your preferred AWS profile or SSO session.
3. Review `providers.tf`, `secrets.tf`, and the exact GitHub subject in `terraform.tfvars`. Confirm the target AWS account with `aws sts get-caller-identity`.
4. Check whether the account already has the GitHub OIDC provider. The current `oidc.tf` defines a provider resource; automatic reuse is not implemented. Import an existing provider into the appropriate Terraform resource, or deliberately adapt the configuration to reference it, before applying.
5. Review and apply the Terraform plan.
6. Configure the GitHub Actions variables listed above. Retrieve the secret ARN with `terraform output -raw secret_arn`; retrieve the role ARN with `aws iam get-role --role-name role-sync-github-secrets --query Role.Arn --output text`, or add a role ARN output.
7. Add the example source secrets in the repository settings.
8. Run the workflow manually from the authorized branch.
9. Verify the destination version in AWS using an identity with read permissions. Do not print secret values in workflow logs.

Run the infrastructure commands from the Terraform directory:

```bash
cd infra/terraform
# Create or edit terraform.tfvars with your exact github_oidc_subject.
# Use terraform.tfvars.example as a template for your local configuration.
terraform init
terraform fmt -check
terraform validate
terraform plan
terraform apply
terraform output -raw secret_arn
```

Local Terraform credentials are required for the initial setup. The synchronization role cannot bootstrap itself before it exists.

## Run the synchronization workflow

1. In **Settings → Secrets and variables → Actions → Variables**, create `AWS_REGION`, `AWS_ROLE_ARN`, and `AWS_SECRET_ARN`. The region must match the destination secret. Retrieve the ARNs using the commands in the setup section above.
2. In the **Secrets** tab, create repository secrets `DEMO_API_TOKEN` and `DEMO_DB_PASSWORD` with fictional values for the first run.
3. Merge the workflow, script, and requirements into the repository's default branch so that GitHub exposes the manual trigger.
4. Open **Actions → Sync secrets to AWS → Run workflow** and select the branch authorized by `github_oidc_subject`. The workflow uses no GitHub Environment; the actual OIDC subject must match the Terraform trust policy exactly.
5. Confirm that the synchronization step reports success. An authorized AWS identity can inspect the destination in the Secrets Manager console; the workflow role has write permission only.

The uploaded JSON contains `api_token` and `db_password`. Each successful run replaces the complete payload and creates a new version. Additional destination keys are not preserved. To add another source, update both the workflow step's `env` mapping and `SECRET_FIELDS` in the script.

Missing or blank inputs stop the upload. Quotes, newlines, Unicode, and surrounding whitespace in nonempty values are preserved. The script rejects JSON larger than 65,536 UTF-8 bytes and never prints secret values or AWS exception details. Concurrent runs targeting the same configured ARN are serialized.

For a missing-variable error, check the Actions variables and secrets above. For an OIDC failure, check the selected branch and exact IAM trust subject. For an upload failure, check the destination region, ARN, and role permissions. See the [AWS PutSecretValue reference](https://docs.aws.amazon.com/boto3/latest/reference/services/secretsmanager/client/put_secret_value.html) for version behavior and API limits.

## Authentication and permissions

The synchronization job requests `id-token: write` to obtain an OIDC token and `contents: read` to check out the script.

The IAM trust policy restricts the token audience to `sts.amazonaws.com` and the subject to the intended repository and branch. If GitHub Environments are added later, the subject restriction must match the environment-based token format.

The runtime IAM policy grants `secretsmanager:PutSecretValue` only for the destination secret. Additional permissions should be added only when an implemented operation requires them. A customer-managed KMS key may require additional KMS permissions; the initial example will use the service's default encryption key.

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

- [x] Create the initial Terraform configuration for the OIDC provider, IAM role, and destination secret.
- [x] Apply the initial infrastructure successfully.
- [x] Add the destination `secret_arn` output.
- [ ] Support reuse of an existing OIDC provider.
- [ ] Add a role ARN output and a non-secret `terraform.tfvars.example`.
- [x] Implement input validation and JSON serialization.
- [x] Implement the Secrets Manager write operation.
- [x] Create the manually triggered GitHub Actions workflow.
- [ ] Validate OIDC authentication in an AWS sandbox.
- [ ] Verify that unauthorized branches cannot assume the role.
- [ ] Run the workflow twice and verify the expected secret version behavior.
- [ ] Document setup, troubleshooting, costs, and cleanup with verified examples.

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