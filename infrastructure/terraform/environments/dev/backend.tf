# Remote state lives in S3 with a DynamoDB lock table. The bucket and table
# must exist before `terraform init` — bootstrap them once with the script in
# infrastructure/terraform/bootstrap/ (Phase 1) or create them manually.
#
# To switch backends per environment, override these values via -backend-config:
#   terraform init -backend-config="key=openrouter/dev.tfstate"

terraform {
  backend "s3" {
    bucket         = "openrouter-tfstate-dev"
    key            = "openrouter/dev.tfstate"
    region         = "us-east-1"
    dynamodb_table = "openrouter-tfstate-locks"
    encrypt        = true
  }
}
