output "vpc_id" {
  value = module.vpc.vpc_id
}

output "cluster_name" {
  value = module.eks.cluster_name
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "cluster_certificate_authority_data" {
  value     = module.eks.cluster_certificate_authority_data
  sensitive = true
}

output "rds_endpoint" {
  value = module.rds.db_instance_endpoint
}

output "rds_password_secret_arn" {
  value = aws_secretsmanager_secret.rds_password.arn
}

output "redis_endpoint" {
  value = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "redis_token_secret_arn" {
  value = aws_secretsmanager_secret.redis_token.arn
}

output "media_bucket" {
  value = aws_s3_bucket.media.bucket
}

output "kubeconfig_command" {
  value = "aws eks update-kubeconfig --name ${module.eks.cluster_name} --region ${var.region}"
}
