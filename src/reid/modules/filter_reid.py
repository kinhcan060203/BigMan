import numpy as np
import uuid
import time
from pymilvus import MilvusClient
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_distances
import threading

class ReIDMonitor(threading.Thread):
    def __init__(self, milvus_handler):
        self.milvus_handler = milvus_handler

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
    

    def run(self):
        while True:
            expired_data = self.milvus_handler.tmp_vehicle.get_expired_data()
            best_data = self.filter_best_embeddings(expired_data)
            for data in best_data:
                for embedding, metadata in data:
                    self.milvus_handler.main_vehicle.insert(data={"embedding": embedding, **metadata})
            time.sleep(60) 

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
