from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, QueryResponse

class Embedder:
    def encode_texts(chunks):
        pass
    def encode_query(query):
        pass
    
class Chunker:
    def extract_and_chunk(pdf_path: str):
        pass

class VectorStore:
    def store_to_vector_db():
        pass
    def retrieve():
        pass
    def _create_collection():
        pass
    def _collection_exists():
        pass