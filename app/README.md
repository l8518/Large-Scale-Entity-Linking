# App

Run everything in the `app` folder.

## Setup Development Enviroment

1. `docker-compose build` to load images and build dependet images.
2. Load the Trident store
   1. Download the yago2s file and move to `yago2s_input`
   2. Run `docker-compose run trident ./build/trident load -i /data/kb/trident -f /data/kb/yago2s_input`
   Notice: You might need to increase the memory size for the Docker VM (Windows + MacOs), was tested with 8192MB on Win10
3. `docker-compose up`
4. Test the Trident Store
   - On Windows:

      ```powershell
      $KB_NODE="localhost"
      $KB_PORT="9090"

      $query = " SELECT DISTINCT ?class
      WHERE {
        ?s a ?class .
      }
      LIMIT 25
      OFFSET 0"
      python sparql.py ${KB_NODE}:${KB_PORT} "$query"

      $query = "SELECT ?subject ?predicate ?object
          WHERE {?subject ?predicate ?object} 
          LIMIT 100"
      python sparql.py ${KB_NODE}:${KB_PORT} "$query"
      ```
5. Load the Elastic Search Data:
   1. Run `./elasticsearch/load_sample_data.sh` to load all data
6. Test Elastic Search Instance with `curl "http://localhost:9200/freebase/label/_search?q=obama"`

## Run Spark Jobs

### Run a Python application on dockerized Spark standalone cluster

```shell
docker-compose run spark-submit sh /submit.sh
```

### Run Spark Jobs on DAS4

Probably need to use yarn?

## Utils

- Recursive copy from DAS-4 to local storage:  
  `scp -rp -oProxyJump=PERSONALUSERID@ssh.data.vu.nl USERID@fs0.das4.cs.vu.nl:/filepath ./target/`