# Tenant SQL Warehouse User's Guide

This guide explains how to configure your Spark session to write tables to either your personal SQL warehouse or a tenant's shared SQL warehouse.

## Overview

The CDM JupyterHub environment supports two types of SQL warehouses:

1. **User SQL Warehouse**: Your personal workspace for tables
2. **Tenant SQL Warehouse**: Shared workspace for team/organization tables

## Quick Comparison

| Configuration | Warehouse Location | Tables Location | Default Namespace |
|--------------|-------------------|----------------|-------------------|
| `get_spark_session()` | `s3a://cdm-lake/users-sql-warehouse/{username}/` | Personal workspace | `{username}_default` |
| `get_spark_session(tenant_name="kbase")` | `s3a://cdm-lake/tenant-sql-warehouse/kbase/` | Tenant workspace | `kbase_default` |

## Personal SQL Warehouse (Default)

### Usage
```python
# Default behavior - writes to your personal SQL warehouse
spark = get_spark_session()
```

### Where Your Tables Go
- **Warehouse Directory**: `s3a://cdm-lake/users-sql-warehouse/tgu2/`
- **Default Namespace**: `tgu2_default` (username prefix enabled by default)
- **Table Location**: `s3a://cdm-lake/users-sql-warehouse/tgu2/tgu2_default.db/your_table/`

### Example
```python
from spark.utils import get_spark_session
from db_ops.spark_db_utils import create_namespace_if_not_exists

# Create personal Spark session
spark = get_spark_session("MyPersonalApp")

# Create default namespace (creates "tgu2_default" with username prefix)
namespace = create_namespace_if_not_exists(spark)
print(f"Created namespace: {namespace}")  # Output: "Created namespace: tgu2_default"

# Or create custom namespace (creates "tgu2_analysis" with username prefix)
analysis_namespace = create_namespace_if_not_exists(spark, namespace="analysis")
print(f"Created namespace: {analysis_namespace}")  # Output: "Created namespace: tgu2_analysis"

# Create a DataFrame and save as table using returned namespace
df = spark.createDataFrame([(1, "Alice"), (2, "Bob")], ["id", "name"])
df.write.format("delta").saveAsTable(f"{namespace}.my_personal_table")

# Table will be stored at:
# s3a://cdm-lake/users-sql-warehouse/tgu2/tgu2_default.db/my_personal_table/
```

## Tenant SQL Warehouse

### Usage
```python
# Writes to tenant's shared SQL warehouse
spark = get_spark_session(tenant_name="kbase")
```

### Where Your Tables Go
- **Warehouse Directory**: `s3a://cdm-lake/tenant-sql-warehouse/kbase/`
- **Default Namespace**: `kbase_default` (tenant prefix enabled by default)
- **Table Location**: `s3a://cdm-lake/tenant-sql-warehouse/kbase/kbase_default.db/your_table/`

### Requirements
- You must be a member of the specified tenant/group
- The system validates your membership before allowing access

### Example
```python
from spark.utils import get_spark_session
from db_ops.spark_db_utils import create_namespace_if_not_exists

# Create tenant Spark session (validates membership)
spark = get_spark_session("TeamAnalysis", tenant_name="kbase")

# Create default namespace (creates "kbase_default" with tenant prefix)
namespace = create_namespace_if_not_exists(spark)
print(f"Created namespace: {namespace}")  # Output: "Created namespace: kbase_default"

# Or create custom namespace (creates "kbase_research" with tenant prefix)
research_namespace = create_namespace_if_not_exists(spark, namespace="research")
print(f"Created namespace: {research_namespace}")  # Output: "Created namespace: kbase_research"

# Create a DataFrame and save as table using returned namespace
df = spark.createDataFrame([(1, "Dataset A"), (2, "Dataset B")], ["id", "dataset"])
df.write.format("delta").saveAsTable(f"{namespace}.shared_analysis")

# Table will be stored at:
# s3a://cdm-lake/tenant-sql-warehouse/kbase/kbase_default.db/shared_analysis/
```

## Advanced Namespace Management

### Custom Namespaces (Default Behavior)
```python
# Personal warehouse with custom namespace (prefix enabled by default)
spark = get_spark_session()
exp_namespace = create_namespace_if_not_exists(spark, "experiments")  # Returns "tgu2_experiments"

# Tenant warehouse with custom namespace (prefix enabled by default)
spark = get_spark_session(tenant_name="kbase")
data_namespace = create_namespace_if_not_exists(spark, "research_data")  # Returns "kbase_research_data"

# Use returned namespace names for table operations
df.write.format("delta").saveAsTable(f"{exp_namespace}.my_experiment_table")
df.write.format("delta").saveAsTable(f"{data_namespace}.shared_dataset")
```

### Disable Target Prefixing

⚠️ **WARNING**: Creating namespaces without a prefix has significant drawbacks:
- **Global Reservation**: Once created, these namespace names become globally reserved across the entire system
- **Name Conflicts**: No other user can create a namespace with the same name
- **Namespace Pollution**: Global namespaces persist indefinitely and reduce available namespace names for all users
- **Security Concerns**: Unprefixed namespaces may create unintended access patterns or conflicts

Use this feature only when absolutely necessary for system-wide reference data or well-coordinated shared resources.

```python
# Explicitly disable username/tenant prefix
spark = get_spark_session()
global_ns = create_namespace_if_not_exists(spark, "global_reference", append_target=False)  # Returns "global_reference"

spark = get_spark_session(tenant_name="kbase")
shared_ns = create_namespace_if_not_exists(spark, "shared_data", append_target=False)  # Returns "shared_data"

# Use unprefixed namespace names
df.write.format("delta").saveAsTable(f"{global_ns}.reference_table")
df.write.format("delta").saveAsTable(f"{shared_ns}.common_dataset")
```