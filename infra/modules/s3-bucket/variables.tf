variable "bucket_name" {
  description = "Globally unique name of the bucket."
  type        = string
}

variable "force_destroy" {
  description = "Allow terraform destroy to delete a non-empty bucket (use true in dev only)."
  type        = bool
  default     = false
}