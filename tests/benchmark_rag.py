
import requests
import time
import os
import json

BASE_URL = "http://localhost:9305/api/v1"
TEST_FILE = "test_rag.txt"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE_PATH = os.path.join(PROJECT_ROOT, TEST_FILE)

def upload_document():
    print(f"Uploading {FILE_PATH}...")
    with open(FILE_PATH, 'rb') as f:
        files = {'file': (TEST_FILE, f, 'text/plain')}
        response = requests.post(f"{BASE_URL}/documents", files=files)
    
    if response.status_code != 200:
        print(f"Upload failed: {response.text}")
        return None
    
    data = response.json()
    print(f"Uploaded. Doc ID: {data['id']}")
    return data['id']

def index_document(doc_id):
    print(f"Indexing document {doc_id}...")
    response = requests.post(f"{BASE_URL}/documents/{doc_id}/index")
    if response.status_code != 200:
        print(f"Index start failed: {response.text}")
        return False
    return True

def wait_for_indexing(doc_id):
    print("Waiting for indexing to complete...")
    for _ in range(30):
        response = requests.get(f"{BASE_URL}/documents")
        if response.status_code == 200:
            docs = response.json()
            for doc in docs:
                if doc['id'] == doc_id:
                    print(f"Status: {doc['status']}")
                    if doc['status'] == 'indexed':
                        return True
                    if doc['status'] == 'error':
                        print(f"Error: {doc.get('error_message')}")
                        return False
        time.sleep(1)
    print("Timeout waiting for indexing")
    return False

def search(query):
    print(f"\nSearching for: {query}")
    payload = {
        "query": query,
        "top_k": 3,
        "rerank": True
    }
    response = requests.post(f"{BASE_URL}/search", json=payload)
    if response.status_code == 200:
        results = response.json()
        for i, res in enumerate(results):
            print(f"Result {i+1} (Score: {res['score']:.4f}):")
            print(f"Content: {res['content'][:200]}...")
        return results
    else:
        print(f"Search failed: {response.text}")
        return []

def main():
    if not os.path.exists(FILE_PATH):
        print(f"Test file not found: {FILE_PATH}")
        return

    doc_id = upload_document()
    if not doc_id:
        return

    if index_document(doc_id):
        if wait_for_indexing(doc_id):
            print("Indexing complete.")
            
            queries = [
                "人工智能这个术语是谁提出的？",
                "1997年发生了什么重要事件？",
                "ChatGPT 是哪一年发布的？",
                "深度学习技术在什么时候取得突破？"
            ]
            
            for q in queries:
                search(q)
        else:
            print("Indexing failed.")

if __name__ == "__main__":
    main()
