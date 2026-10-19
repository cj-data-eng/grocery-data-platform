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

# The provider tells AWS to trust tokens issued by GitHub.
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

data "aws_iam_policy_document" "plan_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub" # sub condition is the security control. Only workflows running for a pull request in your repo can assume this role. Without it, any GitHub repo could.
      values   = ["repo:${var.github_owner}@${var.github_owner_id}/${var.github_repo_name}@${var.github_repo_id}:pull_request"]
    }
  }
}

resource "aws_iam_role" "plan" {
  name               = "gh-actions-terraform-plan"
  assume_role_policy = data.aws_iam_policy_document.plan_trust.json
}

resource "aws_iam_role_policy_attachment" "plan_read_only" {
  role       = aws_iam_role.plan.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess" # ReadOnlyAccess is enough for plan, which only reads. The role can’t create or change anything.
}

output "plan_role_arn" {
  value = aws_iam_role.plan.arn
}


data "aws_iam_policy_document" "apply_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_owner}@${var.github_owner_id}/${var.github_repo_name}@${var.github_repo_id}:ref:refs/heads/main"]
    }
  }
}

resource "aws_iam_role" "apply" {
  name               = "gh-actions-terraform-apply"
  assume_role_policy = data.aws_iam_policy_document.apply_trust.json
}

# Known technical debt: broad permissions for now. To be narrowed to least privilege once the platform's resources are settled.
resource "aws_iam_role_policy_attachment" "apply_admin" {
  role       = aws_iam_role.apply.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

output "apply_role_arn" {
  value = aws_iam_role.apply.arn
}