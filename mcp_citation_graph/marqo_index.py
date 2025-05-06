from typing import Text
import marqo
import json
import os
import asyncio
import httpx
from tqdm import tqdm
from sklearn.feature_extraction.text import CountVectorizer
from marqo.models.marqo_index import FieldFeature, FieldRequest, FieldType, IndexType, TextPreProcessing, TextSplitMethod


def get_papers_schema():
    return [
        FieldRequest(name="id", type=FieldType.Long, features=[FieldFeature.Filter]),
        FieldRequest(name="title", type=FieldType.Text, features=[FieldFeature.LexicalSearch]),
        FieldRequest(name="year", type=FieldType.Int, features=[FieldFeature.Filter]),
        FieldRequest(name="n_citation", type=FieldType.Int, features=[FieldFeature.Filter]),
        FieldRequest(name="doc_type", type=FieldType.Text, features=[FieldFeature.Filter]),
        FieldRequest(name="publisher", type=FieldType.Text, features=[FieldFeature.LexicalSearch]),
        FieldRequest(name="references", type=FieldType.ArrayLong, features=[FieldFeature.Filter]),
        FieldRequest(name="n_reference", type=FieldType.Int, features=[FieldFeature.Filter]),
        FieldRequest(name="author_names", type=FieldType.ArrayText, features=[FieldFeature.Filter, FieldFeature.LexicalSearch]),
        FieldRequest(name="author_orgs", type=FieldType.ArrayText, features=[FieldFeature.Filter, FieldFeature.LexicalSearch]),
        FieldRequest(name="author_ids", type=FieldType.ArrayLong, features=[FieldFeature.Filter]),
        FieldRequest(name="author_names_ngram", type=FieldType.ArrayText, features=[FieldFeature.Filter, FieldFeature.LexicalSearch]),
        FieldRequest(name="author_orgs_ngram", type=FieldType.ArrayText, features=[FieldFeature.Filter, FieldFeature.LexicalSearch]),
        FieldRequest(name="venue_name", type=FieldType.Text, features=[FieldFeature.Filter, FieldFeature.LexicalSearch]),
        FieldRequest(name="venue_id", type=FieldType.Long, features=[FieldFeature.Filter]),
        FieldRequest(name="venue_type", type=FieldType.Text, features=[FieldFeature.Filter]),
        FieldRequest(name="venue_name_ngram", type=FieldType.ArrayText, features=[FieldFeature.Filter, FieldFeature.LexicalSearch]),
        FieldRequest(name="fos_names", type=FieldType.ArrayText, features=[FieldFeature.Filter, FieldFeature.LexicalSearch]),
        FieldRequest(name="fos_ws", type=FieldType.ArrayFloat, features=[FieldFeature.Filter]),
        FieldRequest(name="fos_names_ngram", type=FieldType.ArrayText, features=[FieldFeature.Filter, FieldFeature.LexicalSearch]),
    ]


def extract_ngrams(text_inputs: list[str], ngram_range: tuple = (1, 3)):
    if sum([1 for t in text_inputs if t]) == 0:
        return []
    try:
        vectorizer = CountVectorizer(ngram_range=ngram_range, lowercase=False)
        vectorizer.fit_transform(text_inputs)
        tokens = vectorizer.get_feature_names_out()
        return list(tokens)
    except:
        return []


mq = marqo.Client(url='http://localhost:8882')
data_path = 'data/dblp.filtered.y2000_r9_c5.json'

try:
    mq.create_index(
        'papers',
        type=IndexType.Structured,
        model='hf/e5-base-v2',
        all_fields=get_papers_schema(),
        tensor_fields=['title'],
        text_preprocessing=TextPreProcessing(split_method=TextSplitMethod.Passage, split_length=10, split_overlap=0),
        normalize_embeddings=True,
    )
except marqo.errors.MarqoWebError as e:
    if 'already exists' not in str(e):
        raise

with open(data_path, 'r', encoding='utf-8') as f:
    entries = json.load(f)


def preprocess_docs(batch, batch_offset=0):
    # Preprocess a batch of documents (extract ngrams, ensure _id)
    for idx, doc in enumerate(batch):
        if 'author_names' in doc:
            doc['author_names_ngram'] = extract_ngrams(doc['author_names'], ngram_range=(1, 2))
        if 'author_orgs' in doc:
            doc['author_orgs_ngram'] = extract_ngrams(doc['author_orgs'], ngram_range=(1, 3))
        if 'venue_name' in doc:
            doc['venue_name_ngram'] = extract_ngrams([doc['venue_name']], ngram_range=(1, 4))
        if 'fos_names' in doc:
            doc['fos_names_ngram'] = extract_ngrams(doc['fos_names'], ngram_range=(1, 2))
        if '_id' not in doc:
            doc['_id'] = str(doc.get('id', batch_offset + idx))
    return batch


def index_papers_sequential(entries, batch_size=100, n_batches=None):
    total = len(entries)
    max_batches = (total + batch_size - 1) // batch_size
    if n_batches is not None:
        max_batches = min(max_batches, n_batches)
    for batch_num, i in enumerate(tqdm(range(0, total, batch_size), total=max_batches, desc="Indexing batches")):
        if batch_num >= max_batches:
            break
        batch = entries[i:i+batch_size]
        batch = preprocess_docs(batch, batch_offset=i)
        res = mq.index('papers').add_documents(batch, device='cuda')
    print(f"Indexed {min(max_batches * batch_size, total)} documents into the 'papers' index.")


# async def async_add_documents(client, url, batch, device='cuda'):
#     # Async POST to Marqo add_documents endpoint
#     payload = {
#         'documents': batch,
#         'device': device
#     }
#     resp = await client.post(url, json=payload)
#     resp.raise_for_status()
#     return await resp.json()


# async def index_papers_concurrent(
#     entries, 
#     batch_size=100, 
#     n_batches=None, 
#     max_concurrent=5, 
#     marqo_url='http://localhost:8882', 
#     index_name='papers', 
#     device='cuda'
# ):
#     # Concurrently index papers using Marqo REST API
#     total = len(entries)
#     max_batches = (total + batch_size - 1) // batch_size
#     if n_batches is not None:
#         max_batches = min(max_batches, n_batches)
#     batches = [entries[i:i+batch_size] for i in range(0, total, batch_size)][:max_batches]
#     # Preprocess all batches
#     batches = [preprocess_docs(batch, batch_offset=i*batch_size) for i, batch in enumerate(batches)]
#     url = f"{marqo_url}/indexes/{index_name}/documents"

#     sem = asyncio.Semaphore(max_concurrent)
#     async with httpx.AsyncClient(timeout=60.0) as client:
#         async def sem_add(batch):
#             async with sem:
#                 return await async_add_documents(client, url, batch, device)
#         tasks = [sem_add(batch) for batch in batches]
#         results = []
#         # Await all tasks INSIDE the async with block
#         for fut in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Concurrent Indexing"):
#             result = await fut
#             results.append(result)
#         print(f"Indexed {min(max_batches * batch_size, total)} documents into the '{index_name}' index (concurrent mode).")
#         return results


if __name__ == "__main__":
    index_papers_sequential(entries, batch_size=100, n_batches=None)
    # asyncio.run(index_papers_concurrent(entries, batch_size=100, n_batches=12, max_concurrent=4))
