# Role assumed by the scheduled ingest workflow. It can do exactly one thing:
# write objects under basket_lines/ in the raw bucket.

data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

data "aws_iam_policy_document" "ingest_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
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

data "aws_iam_policy_document" "ingest_permissions" {
  statement {
    sid       = "WriteRawBasketLines"
    actions   = ["s3:PutObject"]
    resources = ["${module.raw_bucket.bucket_arn}/basket_lines/*"]
  }
}

resource "aws_iam_role" "ingest" {
  name               = "${local.prefix}-gh-ingest"
  assume_role_policy = data.aws_iam_policy_document.ingest_trust.json
}

resource "aws_iam_role_policy" "ingest" {
  name   = "write-raw-basket-lines"
  role   = aws_iam_role.ingest.id
  policy = data.aws_iam_policy_document.ingest_permissions.json
}

output "ingest_role_arn" {
  value = aws_iam_role.ingest.arn
}