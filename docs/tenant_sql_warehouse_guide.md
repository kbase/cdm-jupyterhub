# Tenant SQL Warehouse User's Guide

This guide explains how to configure your Spark session to write tables to either your personal SQL warehouse or a tenant's shared SQL warehouse.

## Overview

The CDM JupyterHub environment supports two types of SQL warehouses:

1. **User SQL Warehouse**: Your personal workspace for tables
2. **Tenant SQL Warehouse**: Shared workspace for team/organization tables

## Quick Comparison

| Configuration | Warehouse Location | Tables Location | Default Namespace |
|--------------|-------------------|----------------|-------------------|
| `get_spark_session()` | `s3a://cdm-lake/users-sql-warehouse/{username}/` | Personal workspace | `default` |
| `get_spark_session(tenant_name="kbase")` | `s3a://cdm-lake/tenant-sql-warehouse/kbase/` | Tenant workspace | `default` |

## Personal SQL Warehouse (Default)

### Usage
```python
# Default behavior - writes to your personal SQL warehouse
spark = get_spark_session()
```

### Where Your Tables Go
- **Warehouse Directory**: `s3a://cdm-lake/users-sql-warehouse/tgu2/`
- **Default Namespace**: `default` (no username prefix by default)
- **Table Location**: `s3a://cdm-lake/users-sql-warehouse/tgu2/default.db/your_table/`

### Example
```python
from spark.utils import get_spark_session
from db_ops.spark_db_utils import create_namespace_if_not_exists

# Create personal Spark session
spark = get_spark_session("MyPersonalApp")

# Create default namespace (just "default", no username prefix)
create_namespace_if_not_exists(spark)

# Create a DataFrame and save as table
df = spark.createDataFrame([(1, "Alice"), (2, "Bob")], ["id", "name"])
df.write.format("delta").saveAsTable("default.my_personal_table")

# Table will be stored at:
# s3a://cdm-lake/users-sql-warehouse/tgu2/default.db/my_personal_table/
```

## Tenant SQL Warehouse

### Usage
```python
# Writes to tenant's shared SQL warehouse
spark = get_spark_session(tenant_name="kbase")
```

### Where Your Tables Go
- **Warehouse Directory**: `s3a://cdm-lake/tenant-sql-warehouse/kbase/`
- **Default Namespace**: `default` (no tenant prefix by default)
- **Table Location**: `s3a://cdm-lake/tenant-sql-warehouse/kbase/default.db/your_table/`

### Requirements
- You must be a member of the specified tenant/group
- The system validates your membership before allowing access

### Example
```python
from spark.utils import get_spark_session
from db_ops.spark_db_utils import create_namespace_if_not_exists

# Create tenant Spark session (validates membership)
spark = get_spark_session("TeamAnalysis", tenant_name="kbase")

# Create default namespace (just "default", no tenant prefix)
create_namespace_if_not_exists(spark)

# Create a DataFrame and save as table
df = spark.createDataFrame([(1, "Dataset A"), (2, "Dataset B")], ["id", "dataset"])
df.write.format("delta").saveAsTable("default.shared_analysis")

# Table will be stored at:
# s3a://cdm-lake/tenant-sql-warehouse/kbase/default.db/shared_analysis/
```

## Advanced Namespace Management

### Custom Namespaces (Default Behavior)
```python
# Personal warehouse with custom namespace (no prefix by default)
spark = get_spark_session()
create_namespace_if_not_exists(spark, "experiments")  # Creates "experiments"

# Tenant warehouse with custom namespace (no prefix by default)
spark = get_spark_session(tenant_name="kbase")
create_namespace_if_not_exists(spark, "research_data")  # Creates "research_data"
```

### Enable Target Prefixing
```python
# Add username/tenant prefix to namespace
spark = get_spark_session()
create_namespace_if_not_exists(spark, "experiments", append_target=True)  # Creates "tgu2_experiments"

spark = get_spark_session(tenant_name="kbase")
create_namespace_if_not_exists(spark, "research_data", append_target=True)  # Creates "kbase_research_data"
```

### Explicit Control
```python
# Explicitly disable prefixing (same as default)
create_namespace_if_not_exists(spark, "global_reference", append_target=False)
# Creates "global_reference" with no prefix
```