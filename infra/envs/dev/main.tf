terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = var.project
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  prefix = "${var.project}-${var.environment}"
  suffix = data.aws_caller_identity.current.account_id
}

module "raw_bucket" {
  source        = "../../modules/s3-bucket"
  bucket_name   = "${local.prefix}-raw-${local.suffix}"
  force_destroy = var.force_destroy
}

module "curated_bucket" {
  source        = "../../modules/s3-bucket"
  bucket_name   = "${local.prefix}-curated-${local.suffix}"
  force_destroy = var.force_destroy
}

output "raw_bucket" {
  value = module.raw_bucket.bucket_id
}

output "curated_bucket" {
  value = module.curated_bucket.bucket_id
}