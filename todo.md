create a wrapper class for FAISS indexing.

use config params, paths from Config class

index txt chunks from extraction/<file>/<chunk dir>

use langchain for the whole thing
use langchain loader
use langchain faiss wrapper

use hugging face google gemma model

useful snippets:

## langchain + faiss indexing

```python
from langchain_community.document_loaders import PyPDFLoader

file_path = "../example_data/nke-10k-2023.pdf"
loader = PyPDFLoader(file_path)

docs = loader.load()

print(len(docs))

import getpass
import os

if not os.environ.get("OPENAI_API_KEY"):
os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter API key for OpenAI: ")

from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS

embedding_dim = len(embeddings.embed_query("hello world"))
index = faiss.IndexFlatL2(embedding_dim)

vector_store = FAISS(
    embedding_function=embeddings,
    index=index,
    docstore=InMemoryDocstore(),
    index_to_docstore_id={},
)

ids = vector_store.add_documents(documents=all_splits)
```

## langchain + gemma embedding model + faiss

```python
from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface.embeddings import HuggingFaceEmbeddings

# Download the model from the 🤗 Hub. Also specify to use the "query" and "document" prompts
# as defined in the model configuration, as LangChain doesn't automatically use them.
# See https://huggingface.co/google/embeddinggemma-300m/blob/main/config_sentence_transformers.json
embedder = HuggingFaceEmbeddings(
    model_name="google/embeddinggemma-300m",
    query_encode_kwargs={"prompt_name": "query"},
    encode_kwargs={"prompt_name": "document"}
)

data = [
    "Venus is often called Earth's twin because of its similar size and proximity.",
    "Mars, known for its reddish appearance, is often referred to as the Red Planet.",
    "Jupiter, the largest planet in our solar system, has a prominent red spot.",
    "Saturn, famous for its rings, is sometimes mistaken for the Red Planet."
]

# Create documents for the vector store
documents = [Document(page_content=text, metadata={"id": i}) for i, text in enumerate(data)]

# Create vector store using FAISS. Setting distance_strategy to "MAX_INNER_PRODUCT" uses
# FAISS' FlatIndexIP behind the scenes, which is optimized for inner product search. This
# is what the model was trained for
vector_store = FAISS.from_documents(documents, embedder, distance_strategy="MAX_INNER_PRODUCT")

# Search for top 3 similar documents
query = "Which planet is known as the Red Planet?"
results = vector_store.similarity_search_with_score(query, k=3)

# Print results
for doc, score in results:
    print(f"Text: {doc.page_content} (score: {score:.4f})")
"""
Text: Mars, known for its reddish appearance, is often referred to as the Red Planet. (score: 0.6359)
Text: Jupiter, the largest planet in our solar system, has a prominent red spot. (score: 0.4930)
Text: Saturn, famous for its rings, is sometimes mistaken for the Red Planet. (score: 0.4889)
"""
```

use this code as reference to implement FAISS indexing at `faiss_indexer` module. Do not implement inference yet.

