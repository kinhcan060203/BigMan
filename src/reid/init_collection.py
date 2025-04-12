from pymilvus import MilvusClient, DataType
import os

MILVUS_SERVER = os.getenv("MILVUS_SERVER", "localhost:19530")
MILVUS_TOKEN = os.getenv("MILVUS_TOKEN", "root:anh123")
MILVUS_DB_NAME = os.getenv("MILVUS_DB_NAME", "reid")

client = MilvusClient(uri=f"http://{MILVUS_SERVER}", token=MILVUS_TOKEN, db_name=MILVUS_DB_NAME)

def create_collection_tmp():
    schema = MilvusClient.create_schema(
        auto_id=True,  
        enable_dynamic_field=True,
    )

    schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
    schema.add_field(field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=2048)
    schema.add_field(field_name="camera_id", datatype=DataType.VARCHAR, max_length=255)
    schema.add_field(field_name="timestamp", datatype=DataType.FLOAT)
    schema.add_field(field_name="event_type", datatype=DataType.VARCHAR, max_length=20)
    schema.add_field(field_name="identity", datatype=DataType.VARCHAR, max_length=20)
    schema.add_field(field_name="tracker_id", datatype=DataType.INT32)

    index_params = client.prepare_index_params()
    
    index_params.add_index(
        field_name="embedding", 
        index_type="AUTOINDEX",
        metric_type="COSINE"
    )

    index_params.add_index(
        field_name="camera_id",
        index_type="Trie"
    )


    index_params.add_index(
        field_name="identity",
        index_type="Trie"
    )
    index_params.add_index(
        field_name="tracker_id",
        index_type=""
    )


    client.drop_collection(collection_name="tmp_vehicle")
    client.create_collection( 
        collection_name="tmp_vehicle",
        schema=schema,
        index_params=index_params,
    )

    res = client.get_load_state(collection_name="tmp_vehicle")
    print(res)

def create_collection_main_vehicle():
    schema = MilvusClient.create_schema(
        auto_id=True, 
        enable_dynamic_field=True,
    )

    schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
    schema.add_field(field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=2048)
    schema.add_field(field_name="camera_id", datatype=DataType.VARCHAR, max_length=255)
    schema.add_field(field_name="timestamp", datatype=DataType.FLOAT)
    schema.add_field(field_name="vehicle_path", datatype=DataType.VARCHAR, max_length=255)
    schema.add_field(field_name="identity", datatype=DataType.VARCHAR, max_length=20)

    index_params = client.prepare_index_params()
    
    index_params.add_index(
        field_name="embedding", 
        index_type="AUTOINDEX",
        metric_type="COSINE"
    )

    index_params.add_index(
        field_name="camera_id",
        index_type="Trie"
    )


    index_params.add_index(
        field_name="identity",
        index_type="Trie"
    )
    index_params.add_index(
        field_name="timestamp",
        index_type=""
    )

    client.drop_collection(collection_name="main_vehicle")
    client.create_collection( 
        collection_name="main_vehicle",
        schema=schema,
        index_params=index_params,
    )

    res = client.get_load_state(collection_name="main_vehicle")
    print(res)
