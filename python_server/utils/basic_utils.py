from datetime import datetime
import hashlib

def formatted_datetime():
    now = datetime.now()
    formatted = now.strftime("%Y-%m-%d %H:%M:%S")
    return formatted

def format_history(conversation_history, k=3):
    recent = conversation_history[-k:]
    
    formatted = []
    for item in recent:
        role = item.get("role")
        content = item.get("content")
        formatted.append(f"{role.upper()}: {content}")
    
    return "\n".join(formatted)

def build_context(retrieved_items):
    context_chunks = []

    for i, item in enumerate(retrieved_items, 1):
        text = item.get("text", "")
        page = item.get("page", "N/A")
        source = item.get("source", "Unknown")
        score = item.get("score", 0)

        chunk = f"""[Chunk {i}]
            Source: {source}
            Page: {page}
            Relevance Score: {score:.3f}

            {text}
        """
        context_chunks.append(chunk.strip())

    return "\n\n".join(context_chunks)


def compute_file_hash(file_stream):
    file_stream.seek(0)
    hash_sha256 = hashlib.sha256()

    for chunk in iter(lambda: file_stream.read(4096), b""):
        hash_sha256.update(chunk)

    file_stream.seek(0)
    return hash_sha256.hexdigest()
