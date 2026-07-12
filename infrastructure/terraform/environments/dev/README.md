# Terraform — dev environment

Phase 0 baseline: VPC + EKS + RDS Postgres + ElastiCache Redis + S3.

## Prerequisites

- Terraform `>= 1.9.0`
- AWS credentials with permission to create the listed resources
- An S3 bucket and DynamoDB table for state — bootstrap once:
  ```bash
  aws s3 mb s3://openrouter-tfstate-dev --region us-east-1
  aws dynamodb create-table --table-name openrouter-tfstate-locks \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST --region us-east-1
  ```

## Apply

```bash
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan -out=plan.tfplan
terraform apply plan.tfplan
```

After apply, wire kubectl:

```bash
$(terraform output -raw kubeconfig_command)
kubectl get nodes
```

## What this is, and what it isn't

**Is:** a working dev cluster you can `helm upgrade --install` the OpenRouter chart onto.

**Isn't:** production-grade. Specifically:

- Single-AZ NAT (cost), single-AZ RDS (no failover), `deletion_protection=false` on RDS, public EKS endpoint, no PrivateLink, no KMS CMK (uses AES256 default).
- Phase 1 will introduce wrapper modules under `../../modules/` that codify the production guardrails — see [ARCHITECTURE.md §5](../../../../ARCHITECTURE.md).

## Destroy

```bash
terraform destroy
```
S3 buckets with versioning may need objects removed first.
