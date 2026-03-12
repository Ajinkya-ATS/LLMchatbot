import re

def clean_response(text: str) -> str:
    text = re.sub(r'^(Assistant:|AI:|Bot:)\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(I am an AI|I am an artificial intelligence).*?How can I help you today\?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\n\d+\.\s*', '\n• ', text)
    text = re.sub(r'^\d+\.\s*', '• ', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()