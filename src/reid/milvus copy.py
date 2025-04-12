from pymilvus import MilvusClient, DataType

# Kết nối Milvus
client = MilvusClient(uri="http://localhost:19532", token="root:anh123", db_name="reid")

# Tạo schema
schema = MilvusClient.create_schema(
    auto_id=True,  # Tự động tạo ID
    enable_dynamic_field=True,
)

# Thêm các trường vào schema
schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
schema.add_field(field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=2048)
schema.add_field(field_name="camera_name", datatype=DataType.VARCHAR, max_length=255)
schema.add_field(field_name="timestamp", datatype=DataType.FLOAT)
schema.add_field(field_name="vehicle_path", datatype=DataType.VARCHAR, max_length=255)
schema.add_field(field_name="identity", datatype=DataType.VARCHAR, max_length=20)
                    #   "embedding": row.embedding,
                    #         "timestamp": row.timestamp,
                    #         "camera_name": row.camera_name,
                    #         "identity": row.identity,
                    #         "vehicle_path": vehicle_path,
index_params = client.prepare_index_params()
 
index_params.add_index(
    field_name="embedding", 
    index_type="AUTOINDEX",
    metric_type="COSINE"
)

index_params.add_index(
    field_name="camera_name",
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


# Tạo collection với TTL 30s
# remove collection
client.drop_collection(collection_name="main_vehicle")
client.create_collection( 
    collection_name="main_vehicle",
    schema=schema,
    index_params=index_params,
)

# Kiểm tra trạng thái load collection
res = client.get_load_state(collection_name="main_vehicle")
print(res)
