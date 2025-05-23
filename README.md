# CDM Jupyterhub dockerfiles (Prototype)

This prototype establishes a Docker container configuration for JupyterHub, designed to furnish a multi-user 
environment tailored for executing Spark jobs via Jupyter notebooks.

## User How-To Guide

[Accessing Spark Jupyter Notebook](docs/user_guide.md)

[MinIO Guide](docs/minio_guide.md)


## Using `docker-compose.yaml`

To deploy the JupyterHub container and Spark nodes locally, execute the following command:

```bash
docker-compose up --build
```

## Test Submitting a Spark Job Locally

### Submitting a Spark Job via spark-test-node
```bash
docker exec -it spark-test-node \
    sh -c '
	    /opt/bitnami/spark/bin/spark-submit \
	    --master $SPARK_MASTER_URL \
	    examples/src/main/python/pi.py 10 \
	    2>/dev/null
    '
```

### Submitting a Spark Job via Jupyter Notebook
After launching the [Jupyter Notebook](http://localhost:4041/), establish a Spark context or session with the Spark 
master set to the environment variable `SPARK_MASTER_URL` and proceed to submit your job. Once the job is submitted, 
you can monitor the job status and logs in the [Spark UI](http://localhost:8080/).

Sample code to calculate Pi using `SparkContext`:
```python
from pyspark import SparkConf, SparkContext
import random
import os

spark_master_url = os.environ['SPARK_MASTER_URL']

conf = SparkConf().setMaster(spark_master_url).setAppName("Pi")
sc = SparkContext(conf=conf)

num_samples = 100000000
def inside(p):     
  x, y = random.random(), random.random()
  return x*x + y*y < 1
count = sc.parallelize(range(0, num_samples)).filter(inside).count()
pi = 4 * count / num_samples
print(pi)
sc.stop()
```

## Development

### Running tests

Python 3.11 must be installed on the system.

```
uv sync --locked # only the first time or when uv.lock changes
PYTHONPATH=src uv run pytest tests
```

## Racher Deployment

### Environment Variables
- `SPARK_MASTER_URL`: `spark://spark-master:7077`
- `NOTEBOOK_PORT`: 4041
- `SPARK_DRIVER_HOST`: `notebook` (the hostname of the Jupyter notebook container).

### Spark Session/Context Configuration

When running Spark in the Jupyter notebook container, the default `spark.driver.host` configuration is set to 
the hostname (`SPARK_DRIVER_HOST`) of the container. 
In addition, the environment variable `SPARK_MASTER_URL` should also be configured.

#### Using Predefined SparkSession from `spark.utils.get_spark_session` method
```python
from spark.utils import get_spark_session

spark = get_spark_session(app_name)

# To build spark session for Delta Lake operations, set the delta_lake parameter to True
spark = get_spark_session(app_name, delta_lake=True)
```

#### Manually Configuring SparkSession/SparkContext

If you want to configure the SparkSession manually, you can do so as follows:

#### Example SparkSession Configuration
```python
spark = SparkSession.builder \
    .master(os.environ['SPARK_MASTER_URL']) \
    .appName("TestSparkJob") \
    .getOrCreate()
```

#### Example SparkContext Configuration
```python
conf = SparkConf() \
    .setMaster(os.environ['SPARK_MASTER_URL']) \
    .setAppName("TestSparkJob")
sc = SparkContext(conf=conf)
```

#### Submitting a Job Using Terminal
```bash
/opt/bitnami/spark/bin/spark-submit \
    --master $SPARK_MASTER_URL \
    /opt/bitnami/spark/examples/src/main/python/pi.py 10 \
    2>/dev/null
```

## Connecting to the Jupyter Notebook

### Tunneling to the Jupyter Notebook
```bash
ssh -f -N -L localhost:44041:10.58.2.201:4041 <kbase_developer_username>@login1.berkeley.kbase.us
```
where ```kbase_developer_username``` is an Argonne account, typically starting with `ac.`.

### Accessing the Jupyter Notebook
Navigate to [http://localhost:44041/](http://localhost:44041/) in your browser.

Enjoy your Spark journey!

For more information, please consult the [User Guide](docs/user_guide.md).


## Regenerate cdm-spark-cluster-manager-api-client with [openapi-python-client](https://pypi.org/project/openapi-python-client/)

### Prerequisites
1. Python 3.9+ installed on your system.
2. The `openapi-python-client` package installed. If not already installed, you can do so using pip:
    ```
    pip install openapi-python-client
    ```
3. Access to the OpenAPI specification for the [cdm-kube-spark-manager](https://github.com/kbase/cdm-kube-spark-manager), either via a URL or a local file.
    - TODO - Post the URL after deployment to Rancher2
### Generate the Client
From a URL:

```bash
openapi-python-client generate --url https://api.example.com/openapi.json --output-path cdm-spark-cluster-manager-api-client
```

From a Local File:

```bash
openapi-python-client generate --path ./openapi.yaml --output-path cdm-spark-cluster-manager-api-client 
```

Copy the generated client files to [cdm_spark_cluster_manager_api_client](src/spark/cdm_spark_cluster_manager_api_client)

```bash
cp -r path_of_openapi_ouptput_path/cdm-spark-cluster-manager-api-client/cdm_spark_cluster_manager_api_client path_of_cdm-jupyterhub/src/spark
cp path_of_openapi_ouptput_path/cdm-spark-cluster-manager-api-client/README.md path_of_cdm-jupyterhub/src/spark/cdm_spark_cluster_manager_api_client 
```
