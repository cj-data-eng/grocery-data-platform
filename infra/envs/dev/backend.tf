terraform {
  backend "s3" {
    bucket       = "tfstate-511454199223-eu-west-2"
    key          = "dev/terraform.tfstate"
    region       = "eu-west-2"
    encrypt      = true
    use_lockfile = true
  }
}