import numpy as np
import uuid
import time
from pymilvus import MilvusClient
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_distances
import threading

class SingleMilvus:
    def __init__(self, uri, token, collection_name):
        self.client = MilvusClient(uri=uri, token=token)
        self.collection_name = collection_name

    def get_expired_data(self):
        current_time = time.time()
        expr = f"timestamp<{current_time - 60}"
        res = self.client.query(
            collection_name=self.collection_name,
            expr=expr,
            output_fields=["id", "embedding", "identity"]
        )
        return res
    
    def search(self, query_vector, camera_name, limit=3):
        res = self.client.search(
            collection_name=self.collection_name,
            anns_field="embedding",
            data=[query_vector],
            limit=limit,
            search_params={"metric_type": "COSINE"},
            output_fields=["identity", "timestamp", "camera_name"],
            expr=f'camera_name == "{camera_name}"' 
        )
        return res
    
    def get_tracker_id(self, tracker_id, limit=10):
        res = self.client.search(
            collection_name=self.collection_name,
            limit=limit,
            output_fields=["identity", "timestamp", "camera_name"],
            expr=f'tracker_id == "{tracker_id}"' 
        )
        return res
    
    def insert(self, data):
        self.client.insert(collection_name=self.collection_name, data=data)

    def upsert(self, data):
        self.client.upsert(collection_name=self.collection_name, data=data)

class MilvusMonitor():
    def __init__(self, uri, token, tmp_collection_name, main_collection_name, stop_event):
        self.milvus_vehicle = MilvusClient(uri=uri, token=token, db_name="reid")
        self.tmp_collection_name = tmp_collection_name
        self.main_collection_name = main_collection_name  
        self.stop_event = stop_event
        print(self.milvus_vehicle.list_collections())

    def search(self, collection_name, query_vector, camera_name, limit=3):
        filtered_ids = self.milvus_vehicle.query(
            collection_name=collection_name,
            filter=f'camera_name == "{camera_name}"',
            output_fields=["id"],
        )
        ids = [r["id"] for r in filtered_ids]
        expr_search = f"id in {ids}"
        results = []
        if ids:
            results = self.milvus_vehicle.search(
                collection_name=collection_name,
                data=[query_vector],
                anns_field="embedding", 
                search_params={"metric_type": "COSINE"}, 
                limit=limit,
                filter=expr_search,
                output_fields=["identity", "timestamp", "camera_name"]
            )
        return results
        
    def insert(self, collection_name, data):
        return self.milvus_vehicle.insert(collection_name=collection_name, data=data)
    def upsert(self, collection_name, data):    
        self.milvus_vehicle.upsert(collection_name=collection_name, data=data)
        
    def get_tracker_id(self, collection_name, tracker_id, limit=10):
        return self.milvus_vehicle.query(
            collection_name=collection_name,
            limit=limit,
            output_fields=["*"],
            filter=f'tracker_id == {tracker_id}' 
        )
    def delete_by_id(self, collection_name, id):
        self.milvus_vehicle.delete(collection_name=collection_name, ids=[id], timeout=1000)

    def filter_best_embeddings(expired_data):
        if not expired_data:
            return []
        
        grouped_data = {}
        for row in expired_data:
            identity = row.identity
            embedding = np.array(row.embedding)
            
            if identity not in grouped_data:
                grouped_data[identity] = []
            metadata = {
                "camera_name": row.camera_name,
                "lpr": row.lpr,
                "timestamp": row.timestamp,
            }
            grouped_data[identity].append((embedding, metadata))
        best_embeddings = []
        for identity, (embeddings, metadata) in grouped_data.items():
            if len(embeddings) > 3:
                embeddings = np.array(embeddings)
                distances = np.dot(embeddings, embeddings.T) 
                sum_distances = np.average(distances, axis=1)
                top_indices = np.argsort(sum_distances)[:3] 
                mask = sum_distances[top_indices]  > 0.3
                top_indices = top_indices[mask]
                best_embeds = embeddings[top_indices]
                best_metadata = metadata[top_indices]
                best_embeddings.extend(zip(best_embeds, best_metadata))
            else:
                best_embeddings.extend(zip(embeddings, metadata))
        
        return best_embeddings 
    

    # def run(self):
    #     while not self.stop_event.is_set():
    #         expired_data = self.tmp_vehicle.get_expired_data()
    #         best_data = self.filter_best_embeddings(expired_data)
    #         for data in best_data:
    #             for embedding, metadata in data:
    #                 self.main_vehicle.insert(data={"embedding": embedding, **metadata})
    #         time.sleep(60) 
    # def stop(self):
    #     self.stop_event.set()
    #     self.join()
        
    def dbscan_clustering(self, embeddings, eps=0.2, min_samples=3):
        if len(embeddings) < min_samples:
            return np.zeros(len(embeddings)) 
        distance_matrix = cosine_distances(embeddings)
        clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="precomputed").fit(distance_matrix)
        return clustering.labels_

    def select_top_images(self, embeddings, metadata, eps=0.2):
        labels = self.dbscan_clustering(embeddings, eps=eps)
        unique_clusters = set(labels) - {-1}  

        selected_images = []
        for cluster in unique_clusters:
            indices = [i for i, lbl in enumerate(labels) if lbl == cluster]
            best_index = max(indices, key=lambda idx: metadata[idx]['timestamp'])
            selected_images.append(metadata[best_index])

        while len(selected_images) < 3 and unique_clusters:
            largest_cluster = max(unique_clusters, key=lambda c: sum(1 for lbl in labels if lbl == c), default=None)
            if largest_cluster is None:
                break
            indices = [i for i, lbl in enumerate(labels) if lbl == largest_cluster]
            best_index = min(indices, key=lambda idx: metadata[idx]['timestamp'])
            selected_images.append(metadata[best_index])
            unique_clusters.remove(largest_cluster)
        
        return selected_images[:3]
