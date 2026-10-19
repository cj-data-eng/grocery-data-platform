variable "region" {
  type    = string
  default = "eu-west-2"
}

variable "project" {
  type    = string
  default = "grocery-data-platform"
}

variable "environment" {
  type = string
}

variable "force_destroy" {
  type    = bool
  default = false
}

variable "github_owner" {
  type    = string
  default = "cj-data-eng"
}

variable "github_repo_name" {
  type    = string
  default = "grocery-data-platform"
}

variable "github_owner_id" {
  type = string
}

variable "github_repo_id" {
  type = string
}