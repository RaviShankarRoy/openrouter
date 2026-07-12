variable "region" {
  description = "AWS region for the dev cluster."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment label applied to every resource."
  type        = string
  default     = "dev"
}

variable "cluster_name" {
  description = "EKS cluster name."
  type        = string
  default     = "openrouter-dev"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "kubernetes_version" {
  description = "EKS control-plane version."
  type        = string
  default     = "1.30"
}

variable "node_instance_types" {
  description = "Worker-node instance types for the default node group."
  type        = list(string)
  default     = ["t3.large"]
}

variable "node_min_size" {
  type    = number
  default = 2
}

variable "node_max_size" {
  type    = number
  default = 6
}

variable "rds_instance_class" {
  description = "Postgres instance class. Dev defaults to a small burstable size."
  type        = string
  default     = "db.t4g.medium"
}

variable "redis_node_type" {
  type    = string
  default = "cache.t4g.small"
}

variable "common_tags" {
  description = "Tags applied to every taggable resource."
  type        = map(string)
  default     = {}
}
