from pathlib import Path

import pytest
from airflow.models import DagBag

DAGS_DIR = Path(__file__).resolve().parents[2] / "dags"


@pytest.fixture(scope="module")
def dag_bag() -> DagBag:
    return DagBag(dag_folder=str(DAGS_DIR))


def test_no_import_errors(dag_bag: DagBag) -> None:
    assert dag_bag.import_errors == {}


def test_grocery_daily_structure(dag_bag: DagBag) -> None:
    dag = dag_bag.dags.get("grocery_daily")
    assert dag is not None
    assert set(dag.task_ids) == {"ingest", "dbt_build", "check_daily_sales"}
    # dbt only runs after ingest, and the check only runs after both (it also receives the date).
    assert dag.get_task("dbt_build").upstream_task_ids == {"ingest"}
    assert dag.get_task("check_daily_sales").upstream_task_ids == {
        "ingest",
        "dbt_build",
    }


def test_dag_is_safe_by_default(dag_bag: DagBag) -> None:
    dag = dag_bag.dags.get("grocery_daily")
    assert dag is not None
    assert dag.catchup is False
    assert dag.default_args["retries"] >= 1


def test_failures_are_reported(dag_bag: DagBag) -> None:
    dag = dag_bag.dags.get("grocery_daily")
    assert dag is not None
    assert callable(dag.default_args["on_failure_callback"])
