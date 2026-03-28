from sentence_transformers import SentenceTransformer, CrossEncoder
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, QueryResponse
from pathlib import Path
import fitz
import uuid

CHUNK_SIZE = 512
CHUNK_OVERLAP = 100
BATCH_SIZE = 32
QDRANT_URL = "http://localhost:6333"
DENSE_SEARCH_LIMIT = 70

class Embedder:
    """
    Wrapper around SentenceTransformer for:
        - embedding document chunks
        - embedding user queries
        - exposing embedding dimensionality
    """
    def __init__(self):
        """
        Initializes the sentence transformer embedder.
        Model: BAAI/bge-small-en-v1.5 (fast, high quality dense encoder)
        """
        self.embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")

    def encode_chunks(self, chunks):
        """
        Encodes list of text chunks into embeddings.
        
        Args:
            chunks (list): [{"text": "...", "metadata": {...}}, ...]

        Returns:
            list[list[float]]: Dense vector embeddings
        """
        texts = [c["text"] for c in chunks]
        embs = self.embedder.encode(
            texts,
            batch_size=BATCH_SIZE,
            show_progress_bar=True,
            normalize_embeddings=True,
        ).tolist()
        return embs

    def encode_query(self, query):
        """
        Encodes a single query string with normalization.
        """
        return self.embedder.encode(query, normalize_embeddings=True).tolist()
    
    def get_vector_dim(self):
        """
        Returns embedding dimensionality for creating Qdrant collection.
        """
        return self.embedder.get_sentence_embedding_dimension()
    
class Chunker:
    """
    Extracts text from PDF files and splits into overlapping chunks.
    """
    @staticmethod
    def extract_and_chunk(pdf_path: str):
        """
        Extracts text from each PDF page and splits into chunks of fixed length.
        Allows overlap to preserve context.

        Args:
            pdf_path (str): Path to PDF file

        Returns:
            list: [{ "text": chunk, "metadata": {...}}]
        """
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
    """
    Wrapper around Qdrant for:
        - creating collections
        - storing chunk embeddings
        - retrieving and re-ranking chunks
    """
    def __init__(self,):
        """
        Initializes Qdrant client, embedder and reranker.
        """
        self.client = QdrantClient(url=QDRANT_URL, timeout=60)
        self.embedder = Embedder()
        self.cross_encoder = CrossEncoder("BAAI/bge-reranker-base")

    def store_to_vector_db(self, collection_name, pdf_path):
        """
        Extract → Chunk → Embed → Store chunks into Qdrant.

        Args:
            collection_name (str): Qdrant collection
            pdf_path (str): path to PDF file

        Returns:
            bool: True on success
        """
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
        for i in range(0, len(data), 100):
            self.client.upsert(
                collection_name,
                points=data[i:i+100],
                wait=True
            )
        return True

    def retrieve(self, query, query_history,collection_name, k = 5):
        """
        Retrieval phase for RAG:
        1. Encode query
        2. Dense search in Qdrant
        3. Build contextual query including recent chat history
        4. Re-rank retrieved chunks using cross-encoder
        5. Return top k results

        Args:
            query (str): user question
            query_history (list): recent history (for personalization)
            collection_name (str)
            k (int): number of final results

        Returns:
            list[dict]: [{text, score, page, source}]
        """
        if not self._collection_exists(collection_name):
            print("No such collection exists")
            return []
            
        query_vector = self.embedder.encode_query(query)
        
        # This is retrival step (Dense Search), I did not add sparse search as of now
        response: QueryResponse = self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=DENSE_SEARCH_LIMIT,
            with_payload=True,
        )

        dense_results = []
        for point in response.points:
            text = point.payload.get("text")
            if text:
                dense_results.append(point.payload)

        # Just giving some context to RAG
        user_queries = [
                msg["content"]
                for msg in query_history[-3:]
                if msg["role"] == "user"
            ]
        current_query = query

        history_block = "\n".join(
            [f"Past query {i+1}: {q}" for i, q in enumerate(user_queries)]
        )

        contextual_query = f"""
        {history_block}

        Current query: {current_query}
        """.strip()

        pairs = [[contextual_query, doc["text"]] for doc in dense_results] 
        rerank_scores = self.cross_encoder.predict(pairs)

        for result, score in zip(dense_results, rerank_scores):
            result["rerank_score"] = float(score)

        dense_results.sort(key=lambda x: x["rerank_score"], reverse=True)

        top_k_results = []
        for result in dense_results[:k]:
            top_k_results.append({
                "text": result.get("text"),
                "score": result.get("rerank_score"),
                "page": result.get("page"),
                "source": result.get("source")
            })
        print("Fetched top k results")
        return top_k_results

    def _create_collection(self, collection_name) -> bool:
        """
        Creates a new Qdrant collection with cosine similarity.

        Args:
            collection_name (str): Id of the collection
        """
        vector_dim = self.embedder.get_vector_dim()
        if not self.client.collection_exists(collection_name):
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE),
            )
            return True
        return False

    def _collection_exists(self, collection_name) -> bool:
        """
        Checks if Qdrant collection exists.
        """
        return self.client.collection_exists(collection_name)