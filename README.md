# CDM Jupyterhub dockerfiles (Prototype)

This prototype establishes a Docker container configuration for JupyterHub, designed to furnish a multi-user 
environment tailored for executing Spark jobs via Jupyter notebooks.

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
	    --master spark://spark-master:7077 \
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

## Racher Deployment

### Environment Variables
- `SPARK_MASTER_URL`: `spark://spark-master:7077`
- `NOTEBOOK_PORT`: 4041
- `SPARK_DRIVER_HOST`: `notebook` (the hostname of the Jupyter notebook container).
- `SPARK_DRIVER_PORT`: 7075
- `SPARK_BLOCKMANAGER_PORT`: 7076

### Spark Session/Context Configuration

Ensure to configure `spark.driver.host` for the Spark driver to bind to the Jupyter notebook container's hostname

```python
spark = SparkSession.builder \
    .master(os.environ['SPARK_MASTER_URL']) \
    .appName("TestSparkJob") \
    .config("spark.driver.host", os.environ['SPARK_DRIVER_HOST']) \
    .getOrCreate()
```
```python
conf = SparkConf(). \
    setMaster( os.environ['SPARK_MASTER_URL']). \
    setAppName("TestSparkJob"). \
    set("spark.driver.host", os.environ['SPARK_DRIVER_HOST'])
sc = SparkContext(conf=conf)
```

```bash
/opt/bitnami/spark/bin/spark-submit \
    --master $SPARK_MASTER_URL \
    --conf spark.driver.host=$SPARK_DRIVER_HOST \
    /opt/bitnami/spark/examples/src/main/python/pi.py 10 \
    2>/dev/null
```







