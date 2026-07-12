# Dev environment composition — minimal working set:
#   VPC (3 AZs)  →  EKS  →  RDS Postgres  →  ElastiCache Redis  →  S3 bucket
#
# Phase 0 uses the upstream terraform-aws-modules directly. Phase 1+ will wrap
# them in our own modules under ../../modules/ to enforce guardrails (PrivateLink,
# KMS keys, encryption-at-rest, mandatory tagging) — see ARCHITECTURE.md §5.

locals {
  name = "${var.cluster_name}-${var.environment}"
  tags = merge(
    {
      Project     = "openrouter"
      Environment = var.environment
      ManagedBy   = "terraform"
    },
    var.common_tags,
  )
}

provider "aws" {
  region = var.region
  default_tags { tags = local.tags }
}

data "aws_availability_zones" "available" { state = "available" }

# ---------- VPC ----------

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.13"

  name = "${local.name}-vpc"
  cidr = var.vpc_cidr
  azs  = slice(data.aws_availability_zones.available.names, 0, 3)

  private_subnets = ["10.20.1.0/24", "10.20.2.0/24", "10.20.3.0/24"]
  public_subnets  = ["10.20.101.0/24", "10.20.102.0/24", "10.20.103.0/24"]
  database_subnets = ["10.20.201.0/24", "10.20.202.0/24", "10.20.203.0/24"]

  enable_nat_gateway     = true
  single_nat_gateway     = true   # dev only — prod uses one per AZ
  enable_dns_hostnames   = true
  create_database_subnet_group       = true
  create_database_subnet_route_table = true

  # EKS needs these tags on subnets for the load-balancer controller.
  public_subnet_tags  = { "kubernetes.io/role/elb" = 1 }
  private_subnet_tags = { "kubernetes.io/role/internal-elb" = 1 }
}

# ---------- EKS ----------

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.31"

  cluster_name    = var.cluster_name
  cluster_version = var.kubernetes_version

  cluster_endpoint_public_access = true   # dev convenience; prod = private only

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  enable_irsa = true

  cluster_addons = {
    coredns                = { most_recent = true }
    kube-proxy             = { most_recent = true }
    vpc-cni                = { most_recent = true }
    aws-ebs-csi-driver     = { most_recent = true }
  }

  eks_managed_node_groups = {
    default = {
      min_size       = var.node_min_size
      max_size       = var.node_max_size
      desired_size   = var.node_min_size
      instance_types = var.node_instance_types
      capacity_type  = "ON_DEMAND"
      labels         = { workload = "general" }
    }
  }
}

# ---------- RDS Postgres (with pgvector) ----------

resource "random_password" "rds" {
  length  = 32
  special = false
}

module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.10"

  identifier = "${local.name}-postgres"

  engine               = "postgres"
  engine_version       = "16.4"
  family               = "postgres16"
  major_engine_version = "16"
  instance_class       = var.rds_instance_class

  allocated_storage     = 50
  max_allocated_storage = 200
  storage_encrypted     = true

  db_name  = "openrouter"
  username = "openrouter"
  password = random_password.rds.result
  port     = 5432
  manage_master_user_password = false  # we manage via Secrets Manager below

  multi_az                    = false  # dev — single AZ; prod = true
  db_subnet_group_name        = module.vpc.database_subnet_group_name
  vpc_security_group_ids      = [aws_security_group.rds.id]
  performance_insights_enabled = true
  monitoring_interval          = 60

  backup_retention_period = 7
  deletion_protection     = false   # dev only
  skip_final_snapshot     = true    # dev only
}

resource "aws_security_group" "rds" {
  name_prefix = "${local.name}-rds-"
  vpc_id      = module.vpc.vpc_id
  description = "Allow Postgres from EKS nodes"

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }
  egress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ---------- ElastiCache Redis ----------

resource "aws_security_group" "redis" {
  name_prefix = "${local.name}-redis-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }
}

resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.name}-redis"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${local.name}-redis"
  description                = "OpenRouter dev Redis"
  node_type                  = var.redis_node_type
  num_cache_clusters         = 1
  parameter_group_name       = "default.redis7"
  engine_version             = "7.1"
  port                       = 6379
  subnet_group_name          = aws_elasticache_subnet_group.redis.name
  security_group_ids         = [aws_security_group.redis.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = random_password.redis.result
  apply_immediately          = true
}

resource "random_password" "redis" {
  length  = 32
  special = false
}

# ---------- S3 (media bucket) ----------

resource "aws_s3_bucket" "media" {
  bucket = "${local.name}-media"
}

resource "aws_s3_bucket_versioning" "media" {
  bucket = aws_s3_bucket.media.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  rule { apply_server_side_encryption_by_default { sse_algorithm = "AES256" } }
}

resource "aws_s3_bucket_public_access_block" "media" {
  bucket                  = aws_s3_bucket.media.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ---------- Secrets ----------

resource "aws_secretsmanager_secret" "rds_password" {
  name = "${local.name}/rds/password"
}

resource "aws_secretsmanager_secret_version" "rds_password" {
  secret_id     = aws_secretsmanager_secret.rds_password.id
  secret_string = random_password.rds.result
}

resource "aws_secretsmanager_secret" "redis_token" {
  name = "${local.name}/redis/auth-token"
}

resource "aws_secretsmanager_secret_version" "redis_token" {
  secret_id     = aws_secretsmanager_secret.redis_token.id
  secret_string = random_password.redis.result
}
