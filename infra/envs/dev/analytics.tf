# Makes the raw Parquet files queryable with SQL through Athena.

locals {
  glue_prefix = replace(local.prefix, "-", "_")

  basket_line_columns = [
    { name = "basket_id", type = "string" },
    { name = "store_id", type = "string" },
    { name = "customer_id", type = "string" },
    { name = "purchased_at", type = "timestamp" },
    { name = "product_id", type = "string" },
    { name = "product_name", type = "string" },
    { name = "category", type = "string" },
    { name = "quantity", type = "int" },
    { name = "unit_price_pence", type = "int" },
  ]
}

resource "aws_glue_catalog_database" "raw" {
  name = "${local.glue_prefix}_raw"
}

resource "aws_glue_catalog_table" "basket_lines" {
  name          = "basket_lines"
  database_name = aws_glue_catalog_database.raw.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL       = "TRUE"
    classification = "parquet"

    # Partition projection: Athena derives the daily folders from the date range,
    # so no crawler or MSCK REPAIR is needed when new days arrive.
    "projection.enabled"                     = "true"
    "projection.purchase_date.type"          = "date"
    "projection.purchase_date.range"         = "2026-10-01,NOW"
    "projection.purchase_date.format"        = "yyyy-MM-dd"
    "projection.purchase_date.interval"      = "1"
    "projection.purchase_date.interval.unit" = "DAYS"
    "storage.location.template"              = "s3://${module.raw_bucket.bucket_id}/basket_lines/purchase_date=$${purchase_date}"
  }

  partition_keys {
    name = "purchase_date"
    type = "string"
  }

  storage_descriptor {
    location      = "s3://${module.raw_bucket.bucket_id}/basket_lines/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    dynamic "columns" {
      for_each = local.basket_line_columns
      content {
        name = columns.value.name
        type = columns.value.type
      }
    }
  }
}

resource "aws_athena_workgroup" "main" {
  name          = local.prefix
  force_destroy = var.force_destroy

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    # FinOps guardrail: any single query that would scan more than 1 GiB is cancelled.
    bytes_scanned_cutoff_per_query = 1073741824

    result_configuration {
      output_location = "s3://${module.curated_bucket.bucket_id}/athena-results/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }
}

# Query results are throwaway, so expire them instead of paying to store them forever.
resource "aws_s3_bucket_lifecycle_configuration" "athena_results" {
  bucket = module.curated_bucket.bucket_id

  rule {
    id     = "expire-athena-results"
    status = "Enabled"

    filter {
      prefix = "athena-results/"
    }

    expiration {
      days = 7
    }

    noncurrent_version_expiration {
      noncurrent_days = 1
    }
  }
}

output "athena_workgroup" {
  value = aws_athena_workgroup.main.name
}

output "glue_raw_database" {
  value = aws_glue_catalog_database.raw.name
}