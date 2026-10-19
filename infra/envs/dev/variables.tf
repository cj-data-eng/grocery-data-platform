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