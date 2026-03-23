from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, QueryResponse
from pathlib import Path
import fitz
import uuid

CHUNK_SIZE = 512
CHUNK_OVERLAP = 100
BATCH_SIZE = 32
QDRANT_URL = "http://localhost:6333"

class Embedder:
    def __init__(self):
        self.embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")

    def encode_chunks(self, chunks):
        texts = [c["text"] for c in chunks]
        embs = self.embedder.encode(
            texts,
            batch_size=BATCH_SIZE,
            show_progress_bar=True,
            normalize_embeddings=True,
        ).tolist()
        return embs

    def encode_query(self, query):
        return self.embedder.encode(query, normalize_embeddings=True).tolist()
    
    def get_vector_dim(self):
        return self.embedder.get_sentence_embedding_dimension()
    
class Chunker:
    @staticmethod
    def extract_and_chunk(pdf_path: str):
        path = Path(pdf_path)
        if not path.is_file():
            raise FileNotFoundError(pdf_path)

        doc = fitz.open(pdf_path)
        filename = path.name
        chunks = []
        cid = 0

        for page_num, page in enumerate(doc, 1):
            text = page.get_text("text").strip()
            if not text:
                continue

            i = 0
            while i < len(text):
                end = min(i + CHUNK_SIZE, len(text))
                chunk_text = text[i:end].strip()
                if chunk_text:
                    chunks.append({
                        "text": chunk_text,
                        "metadata": {
                            "source": filename,
                            "page": page_num,
                            "chunk_id": cid,
                        }
                    })
                    cid += 1
                i += CHUNK_SIZE - CHUNK_OVERLAP

        doc.close()
        print(f"Extracted {len(chunks)} chunks from {filename}")
        return chunks

class VectorStore:
    def __init__(self,):
        self.client = QdrantClient(url=QDRANT_URL, timeout=60)
        self.embedder = Embedder()

    def store_to_vector_db(self, collection_name, pdf_path):
        if not self._collection_exists(collection_name):
            self._create_collection(collection_name)
        chunks = Chunker.extract_and_chunk(pdf_path)
        encodings = self.embedder.encode_chunks(chunks)
        data = []
        for chunk, vec in zip(chunks, encodings):
            data.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={
                    "text": chunk["text"],
                    **chunk["metadata"],
                }
            ))
        self.client.upsert(collection_name, points=data, wait=True)
        return True

    def retrieve(self, query, collection_name, k = 5):
        if not self._collection_exists(collection_name):
            print("No such collection exists")
            return []
        
        query_vector = self.embedder.encode_query(query)
        
        response: QueryResponse = self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=k,
            with_payload=True,
        )

        results = []
        for data in response.points:
            text = data.payload.get("text")
            if text:
                results.append(text)
                
        return results

    def _create_collection(self, collection_name) -> bool:
        vector_dim = self.embedder.get_vector_dim()
        if not self.client.collection_exists(collection_name):
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE),
            )
            return True
        return False

    def _collection_exists(self, collection_name) -> bool:
        return self.client.collection_exists(collection_name)