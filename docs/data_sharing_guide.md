# Data Sharing Guide: CDM JupyterHub

## Overview

The BER DataLake JupyterHub platform provides data sharing capabilities that allow users to share their datasets with other users and groups. 

All data governance functions are **✨ automatically imported** in every notebook via `startup.py` - no manual imports needed! This guide shows you how to use these pre-loaded functions for seamless data sharing and collaboration.

## Key Concepts

### Data Organization

All user data in BER DataLake is organized under personal namespaces:

- **General Data Storage**: `s3a://cdm-lake/users-general-warehouse/{username}/`
- **SQL Warehouse**: `s3a://cdm-lake/users-sql-warehouse/{username}/`

## Getting Started

### Auto-Imported Functions

All CDM JupyterHub notebooks automatically import these data governance functions at startup (via `startup.py`), so they're ready to use immediately without any imports:

**Auto-Imported Utility Functions:**
- `check_governance_health()` - Check service status
- `get_minio_credentials()` - Get your MinIO credentials (sets environment variables)
- `get_my_sql_warehouse()` - Get your SQL warehouse prefix
- `get_my_policies()` - Get detailed policy information
- `get_my_workspace()` - Get comprehensive workspace information
- `get_path_access_info(path)` - Check who has access to a path
- `make_table_private(namespace, table_name)` - Remove public access from SQL tables
- `make_table_public(namespace, table_name)` - Make SQL tables publicly accessible
- `share_table(namespace, table_name, with_users, with_groups)` - Share SQL tables
- `unshare_table(namespace, table_name, from_users, from_groups)` - Unshare SQL tables

**Pre-Initialized Client:**
- `governance` - Pre-initialized `DataGovernanceClient()` instance for advanced operations

**Other Auto-Imported Functions:**
- `get_spark_session()` - Create Spark sessions with Delta Lake support
- Plus many other utility functions for data operations

### Quick Start

```python
# Check your workspace information
workspace = get_my_workspace()
print(f"👤 Username: {workspace.username}")
print(f"🏠 Home paths: {workspace.home_paths}")
print(f"👥 Groups: {workspace.groups}")
print(f"📁 Accessible paths: {len(workspace.accessible_paths)}")

# Check service health
health = check_governance_health()
print(f"🔍 Service status: {health.status}")

# Get your credentials (automatically sets environment variables)
# NOTE: This will rotate your credentials
credentials = get_minio_credentials()
print(f"🔐 Credentials loaded for: {credentials.username}")
```

## Core Information Functions

### Service Health and Credentials

```python
# Check governance service status
health = check_governance_health()
print(f"Service status: {health.status}")

# Get MinIO credentials (automatically sets MINIO_ACCESS_KEY and MINIO_SECRET_KEY)
# NOTE: This will rotate your credentials
credentials = get_minio_credentials()
print(f"Username: {credentials.username}")
print(f"Access key: {credentials.access_key}")
print(f"Secret key: {credentials.secret_key}")

# Get your SQL warehouse prefix
sql_warehouse = get_my_sql_warehouse()
print(f"SQL warehouse prefix: {sql_warehouse.sql_warehouse_prefix}")

# The pre-initialized governance client is also available
print(f"Governance client ready: {governance is not None}")
```

### Workspace and Policy Information

```python
# Get comprehensive workspace information
workspace = get_my_workspace()
print(f"Username: {workspace.username}")
print(f"Home paths: {workspace.home_paths}")
print(f"Groups: {workspace.groups}")
print(f"Total accessible paths: {len(workspace.accessible_paths)}")

# Get detailed policy information
policies = get_my_policies()
print(f"Home policy: {policies.user_home_policy.policy_name}")
print(f"System policy: {policies.user_system_policy.policy_name}")
print(f"Group policies: {len(policies.group_policies)}")
```

## Sharing SQL Warehouse Tables

### Share Tables with Users

```python
# Share a table with specific users
response = share_table(
    namespace="research",
    table_name="climate_data",
    with_users=["bob", "alice"]  # kbase usernames
)

print(f"Shared with users: {response.shared_with_users}")
print(f"Success count: {response.success_count}")
if response.errors:
    print(f"Errors: {response.errors}")
```

### Share Tables with Groups

```python
# Share a table with groups
response = share_table(
    namespace="analytics", 
    table_name="user_metrics",
    with_groups=["data-science-team", "research-group"]
)

print(f"Shared with groups: {response.shared_with_groups}")
```

### Share with Both Users and Groups

```python
# Share with combination of users and groups
response = share_table(
    namespace="experiments",
    table_name="results_2024",
    with_users=["researcher1", "analyst2"],
    with_groups=["biology-lab"]
)

print(f"Successfully shared with {response.success_count} recipients")
```

## Unsharing SQL Warehouse Tables

### Remove Access from Users

```python
# Remove access from specific users
response = unshare_table(
    namespace="research",
    table_name="climate_data",
    from_users=["bob"]  # Remove bob's access, alice keeps access
)

print(f"Removed access from: {response.unshared_from_users}")
```

### Remove Access from Groups

```python
# Remove group access
response = unshare_table(
    namespace="analytics",
    table_name="user_metrics", 
    from_groups=["data-science-team"]
)

print(f"Removed group access from: {response.unshared_from_groups}")
```

### Unshare from Both Users and Groups

```python
# Unshare from both users and groups
response = unshare_table(
    namespace="sensitive",
    table_name="confidential_data",
    from_users=["bob", "alice"],
    from_groups=["research-team", "data-scientists"]
)

print(f"Completely privatized table: {response.success_count} removals")
```

## Public and Private Table Access

### Make Tables Publicly Accessible

```python
# Make a table publicly accessible to all users
response = make_table_public(
    namespace="public_data",
    table_name="climate_dataset"
)

print(f"Table is now public: {response.is_public}")
print(f"Public path: {response.path}")
```

### Make Tables Private

```python
# Remove public access and make table private again
response = make_table_private(
    namespace="public_data", 
    table_name="climate_dataset"
)

print(f"Table is now private: {not response.is_public}")
```

## Managing Access Information

### Check Who Has Access to Paths

```python
# Get detailed access information for any path that in your SQL warehouse
access_info = get_path_access_info(
    path="s3a://cdm-lake/users-general-warehouse/alice/datasets/climate-analysis"
)

print(f"Path: {access_info.path}")
print(f"Users with access: {access_info.users}")
print(f"Groups with access: {access_info.groups}")
print(f"Public access: {access_info.public}")
```

### View Your Complete Workspace

```python
# Get comprehensive workspace information
workspace = get_my_workspace()

print(f"🏠 Your workspace: {workspace.username}")
print(f"📁 Home directories: {len(workspace.home_paths)}")
for path in workspace.home_paths:
    print(f"   - {path}")

print(f"👥 Group memberships: {len(workspace.groups)}")
for group in workspace.groups:
    print(f"   - {group}")

print(f"🔓 Total accessible paths: {len(workspace.accessible_paths)}")

# Show shared paths (paths not owned by you)
shared_paths = [
    path for path in workspace.accessible_paths 
    if not any(path.startswith(home) for home in workspace.home_paths)
]
print(f"🤝 Shared with you: {len(shared_paths)}")
for path in shared_paths[:5]:  # Show first 5
    print(f"   - {path}")
```

## Working with Shared Tables

### Accessing Shared Tables in Spark

When others share tables with you, you can access them directly in your Spark sessions:

```python
# get_spark_session is auto-imported, no need to import
# Create Spark session
spark = get_spark_session()

# Option 1: Access shared tables via SQL (if shared SQL warehouse)
try:
    shared_df = spark.sql("SELECT * FROM colleague_research.climate_data")
    print(f"📊 Successfully loaded shared table with {shared_df.count()} rows")
    shared_df.show(5)
except Exception as e:
    print(f"❌ Could not access shared table via SQL: {e}")

# Option 2: Access via direct path (if you know the path)
shared_table_path = "s3a://cdm-lake/users-sql-warehouse/colleague/research.db/climate_data"
try:
    shared_df = spark.read.format("delta").load(shared_table_path)
    print(f"📊 Successfully loaded shared table with {shared_df.count()} rows")
except Exception as e:
    print(f"❌ Could not access shared table: {e}")
    # Check access
    access_info = get_path_access_info(shared_table_path)
    print(f"Your access granted: {get_my_workspace().username in access_info.users}")
```

### Creating Tables from Shared Data

```python
# Copy shared data to your own tables
# All governance functions are automatically available
shared_df = spark.sql("SELECT * FROM colleague_research.raw_data")

# Create your own analysis table
analysis_df = shared_df.groupBy("category").count()

# Save to your SQL warehouse
analysis_df.write.format("delta").mode("overwrite").saveAsTable("my_analysis.category_counts")

# Share your analysis results
share_table(
    namespace="my_analysis",
    table_name="category_counts",
    with_users=["colleague"]
)
```

## Troubleshooting

### Common Issues

1. **Table Not Found**: Ensure the table exists and you have access
   ```python
   # Check if table exists in your accessible workspace
   workspace = get_my_workspace()
   sql_warehouse = get_my_sql_warehouse()
   print(f"Your SQL warehouse: {sql_warehouse.sql_warehouse_prefix}")
   print(f"Accessible paths: {workspace.accessible_paths}")
   
   # List all tables
   spark.sql("SHOW DATABASES").show()
   ```

2. **User Not Found**: Verify usernames are correct and users exist in the system

3. **Namespace Not Found**: Confirm database/namespace names are correct
    ```python
    # Check if namespace exists
    get_databases()
    ```

4. **Permission Denied**: You can only share tables that you own. **Make sure the table is stored in your SQL warehouse location.**

### Getting Help
❓ If you have any questions, feel free to reach out to the BER Platform Team (previously known as the CDM Tech Team).
