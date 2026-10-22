FROM astrocrpublic.azurecr.io/runtime:3.3-10

# The Airflow image runs Python 3.14, and dbt-athena has a dependency (mmh3) with no prebuilt
# package for it. So dbt gets its own virtual environment on Python 3.12, which uv downloads.
ENV UV_PYTHON_INSTALL_DIR=/usr/local/airflow/uv_python
RUN python -m venv /tmp/uv_bootstrap && /tmp/uv_bootstrap/bin/pip install --no-cache-dir uv && /tmp/uv_bootstrap/bin/uv venv --python 3.12 /usr/local/airflow/dbt_venv && /tmp/uv_bootstrap/bin/uv pip install --no-cache --python /usr/local/airflow/dbt_venv/bin/python "dbt-core>=1.10,<2" "dbt-athena>=1.9,<2" && rm -rf /tmp/uv_bootstrap