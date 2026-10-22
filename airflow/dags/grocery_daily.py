"""Daily grocery pipeline: ingest one day of baskets, build dbt models, check the result."""

from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import Param, dag, task

# Where the repo is mounted inside the local Airflow containers (see docker-compose.override.yml).
REPO_DIR = "/usr/local/airflow/repo"
DBT_BIN = "/usr/local/airflow/dbt_venv/bin/dbt"
DBT_DIR = f"{REPO_DIR}/dbt"

RAW_BUCKET = "grocery-data-platform-dev-raw-511454199223"
ANALYTICS_DATABASE = "grocery_data_platform_dev_analytics"
ATHENA_WORKGROUP = "grocery-data-platform-dev"
REGION = "eu-west-2"


@dag(
    dag_id="grocery_daily",
    description="Ingest a day of baskets to S3, run dbt build on Athena, then check the output.",
    schedule="30 7 * * *",
    start_date=datetime(2026, 10, 20),
    catchup=False,
    is_paused_upon_creation=True,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
    params={
        "date": Param(
            "",
            type="string",
            description="YYYY-MM-DD. Leave empty for yesterday (UTC).",
        ),
        "baskets": Param(5000, type="integer", minimum=1, maximum=50000),
    },
    tags=["grocery", "portfolio"],
)
def grocery_daily():
    @task
    def ingest(date_param: str, baskets_param: str) -> str:
        """Generate the day's baskets, write Parquet, and upload it to the raw bucket."""
        import sys
        from datetime import UTC, date

        sys.path.insert(0, f"{REPO_DIR}/src")
        from grocery_platform.cli import main

        if date_param:
            day = date.fromisoformat(date_param).isoformat()
        else:
            day = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()

        exit_code = main(
            [
                "--date",
                day,
                "--baskets",
                str(int(baskets_param)),
                "--out",
                "/tmp/grocery_data",
                "--bucket",
                RAW_BUCKET,
            ]
        )
        if exit_code != 0:
            raise RuntimeError(f"ingest failed with exit code {exit_code}")
        return day

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=f"{DBT_BIN} build --project-dir {DBT_DIR} --profiles-dir {DBT_DIR}",
        env={"DBT_TARGET_PATH": "/tmp/dbt_target", "DBT_LOG_PATH": "/tmp/dbt_logs"},
        append_env=True,
    )

    @task(retries=0)
    def check_daily_sales(day: str) -> None:
        """Fail loudly if the mart has no sales for the day that was just loaded."""
        import time
        from datetime import date

        import boto3

        day = date.fromisoformat(day).isoformat()  # also guards the SQL below
        athena = boto3.client("athena", region_name=REGION)
        query = athena.start_query_execution(
            QueryString=(
                "select count(*) as rows_, coalesce(sum(revenue_gbp), 0) as revenue "
                f"from daily_sales where purchase_date = date '{day}'"
            ),
            QueryExecutionContext={"Database": ANALYTICS_DATABASE},
            WorkGroup=ATHENA_WORKGROUP,
        )["QueryExecutionId"]

        for _ in range(60):
            state = athena.get_query_execution(QueryExecutionId=query)[
                "QueryExecution"
            ]["Status"]["State"]
            if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
                break
            time.sleep(2)
        if state != "SUCCEEDED":
            raise RuntimeError(f"Athena check query ended in state {state}")

        row = athena.get_query_results(QueryExecutionId=query)["ResultSet"]["Rows"][1][
            "Data"
        ]
        rows, revenue = int(row[0]["VarCharValue"]), float(row[1]["VarCharValue"])
        if rows == 0 or revenue <= 0:
            raise ValueError(
                f"daily_sales has no sales for {day} (rows={rows}, revenue={revenue})"
            )
        print(f"daily_sales for {day}: {rows} rows, revenue GBP {revenue:,.2f}")

    loaded_day = ingest("{{ params.date }}", "{{ params.baskets }}")
    loaded_day >> dbt_build >> check_daily_sales(loaded_day)


grocery_daily()