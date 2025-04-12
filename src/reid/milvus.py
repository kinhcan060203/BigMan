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
schema.add_field(field_name="event_type", datatype=DataType.VARCHAR, max_length=20)
schema.add_field(field_name="identity", datatype=DataType.VARCHAR, max_length=20)
schema.add_field(field_name="tracker_id", datatype=DataType.INT32)
# embedding
# camera_name
# tracker_id
# identity
# id - primary key
# embedding - vector
# camera_name - tên camera
# lpr - biển số
# timestamp - thời điểm capture xe
# event_type - loại sự kiện bổ sung
# tracker_id - track id của xe 
# identity - định danh uuid của xe
# Tạo index
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
    field_name="tracker_id",
    index_type=""
)


# Tạo collection với TTL 30s
# remove collection
client.drop_collection(collection_name="tmp_vehicle")
client.create_collection( 
    collection_name="tmp_vehicle",
    schema=schema,
    index_params=index_params,
)

# Kiểm tra trạng thái load collection
res = client.get_load_state(collection_name="tmp_vehicle")
print(res)
