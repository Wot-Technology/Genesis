#!/usr/bin/env python3
"""
Download the embedding model for Thread 2 RAG pipeline.
Run this from a machine with network access to HuggingFace.

Usage:
    python download_model.py

The model will be cached in ~/.cache/huggingface/ and automatically
used by wellspring_embeddings.py on future runs.
"""

import sys

def main():
    print("Downloading all-MiniLM-L6-v2 embedding model...")
    print("This is ~90MB and may take a minute.\n")

    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer('all-MiniLM-L6-v2')

        # Test it works
        test_embedding = model.encode("test sentence")
        print(f"Model loaded successfully!")
        print(f"Embedding dimension: {len(test_embedding)}")
        print(f"\nModel cached at: ~/.cache/huggingface/")
        print("The RAG pipeline will now use neural embeddings instead of fallback.")

    except ImportError:
        print("ERROR: sentence-transformers not installed")
        print("Run: pip install sentence-transformers")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        print("\nIf this is a network error, ensure you have access to huggingface.co")
        sys.exit(1)

if __name__ == "__main__":
    main()
