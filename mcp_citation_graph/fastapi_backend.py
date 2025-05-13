import uvicorn
import marqo
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


# --- Marqo client setup ---
mq = marqo.Client(url="http://localhost:8882")
INDEX_NAME = "papers"


# --- Utils ---
def fetch_paper_by_id(paper_id):
    doc = mq.index(INDEX_NAME).get_document(str(paper_id))
    return dict(doc) if doc else None


def fetch_paper_by_title(paper_title):
    search_res = mq.index(INDEX_NAME).search(
        paper_title,
        search_method=marqo.SearchMethods.TENSOR,
        limit=1
    )
    if not search_res['hits']:
        return None
    return dict(search_res['hits'][0])


def fetch_citations(paper_id: int, depth: int):
    if depth <= 0:
        return []
    filter_str = f"references:({paper_id})"
    res = mq.index(INDEX_NAME).search(
        "",
        search_method=marqo.SearchMethods.TENSOR,
        limit=1000,
        filter_string=filter_str
    )
    citations = []
    for pap in res['hits']:
        pid = pap.get('id')
        if pid is None:
            continue
        pap_copy = fetch_paper_by_id(pid)
        if pap_copy is not None:
            pap_copy['cited_by'] = fetch_citations(pid, depth - 1)
            citations.append(pap_copy)
    return citations


def fetch_origins(paper_id: int, depth: int):
    if depth <= 0:
        return []
    doc = fetch_paper_by_id(paper_id)
    if not doc or "references" not in doc or not doc["references"]:
        return []
    origins = []
    for rid in doc["references"]:
        try:
            ref = fetch_paper_by_id(rid)
            if ref:
                ref_copy = dict(ref)
                ref_copy['cites'] = fetch_origins(ref_copy.get('id'), depth - 1)
                origins.append(ref_copy)
        except Exception:
            continue
    return origins


# --- Pydantic Models ---
class PublicationType(Enum):
    Conference = 'Conference'
    Journal = 'Journal'
    Book = 'Book'
    All = 'All'

class Paper(BaseModel):
    id: int
    title: str
    year: Optional[int] = None
    n_citation: Optional[int] = None
    doc_type: Optional[str] = None
    publisher: Optional[str] = None
    references: Optional[List[int]] = None
    n_reference: Optional[int] = None
    author_names: Optional[List[str]] = None
    author_orgs: Optional[List[str]] = None
    author_ids: Optional[List[int]] = None
    venue_name: Optional[str] = None
    venue_id: Optional[int] = None
    venue_type: Optional[str] = None
    fos_names: Optional[List[str]] = None
    fos_ws: Optional[List[float]] = None
    _id: Optional[str] = None

class PaperWithRefs(BaseModel):
    id: int
    title: str
    year: Optional[int] = None
    n_citation: Optional[int] = None
    doc_type: Optional[str] = None
    publisher: Optional[str] = None
    references: Optional[List[int]] = None
    n_reference: Optional[int] = None
    author_names: Optional[List[str]] = None
    author_orgs: Optional[List[str]] = None
    author_ids: Optional[List[int]] = None
    venue_name: Optional[str] = None
    venue_id: Optional[int] = None
    venue_type: Optional[str] = None
    fos_names: Optional[List[str]] = None
    fos_ws: Optional[List[float]] = None
    _id: Optional[str] = None
    cites: Optional[List[Paper]] = []
    cited_by: Optional[List[Paper]] = []

class BulkPapersRequest(BaseModel):
    papers: List[Paper]

class PaperSearchRequest(BaseModel):
    query: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    limit: int = 10
    offset: int = 0

class PaperSearchResponse(BaseModel):
    results: List[Paper]
    cnt_result: int
    time_miliseconds: int

class StatsResponse(BaseModel):
    total_papers: int
    by_year: Optional[Dict[str, int]] = None
    by_author: Optional[Dict[str, int]] = None
    by_venue: Optional[Dict[str, int]] = None

class HealthResponse(BaseModel):
    status: str

# --- FastAPI App ---
app = FastAPI(title="Papers and Citation Network FastAPI Backend", description="API for searching academic papers.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Endpoints ---
@app.get("/health", response_model=HealthResponse, operation_id="health_check")
def health():
    return {"status": "ok"}


@app.get("/search_papers_by_topic", response_model=PaperSearchResponse, operation_id="search_papers_by_topic")
def search_papers(
    limit: int = Query(10, ge=1, le=100),
    research_topic: Optional[str] = None,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    min_citation: Optional[int] = None,
    max_citation: Optional[int] = None,
    publication_type: Optional[PublicationType] = None,
    author_name: Optional[str] = None,
    author_organization: Optional[str] = None,
    venue_name: Optional[str] = None,
    keywords: Optional[str] = None,
):
    research_topic = '' if research_topic is None else research_topic
    min_year = 1930 if min_year is None else min_year
    max_year = 2021 if max_year is None else max_year
    min_citation = 0 if min_citation is None else min_citation
    max_citation = 1_000_000 if max_citation is None else max_citation
    publication_type = PublicationType.All if publication_type is None else publication_type

    filter_string = f'(year:[{min_year} TO {max_year}])'
    filter_string += f' AND (n_citation:[{min_citation} TO {max_citation}])'
    if publication_type is not PublicationType.All:
        filter_string += f' AND (doc_type:({publication_type.value}))'
    if author_name is not None:
        filter_string += f' AND (author_names_ngram:({author_name}))'
    if author_organization is not None:
        filter_string += f' AND (author_orgs_ngram:({author_organization}))'
    if venue_name is not None:
        filter_string += f' AND (venue_name_ngram:({venue_name}))'
    if keywords is not None:
        filter_string += f' AND (fos_names_ngram:({keywords}))'

    res = mq.index(INDEX_NAME).search(
        research_topic, 
        search_method=marqo.SearchMethods.TENSOR,
        limit=limit, 
        offset=0, 
        filter_string=filter_string
    )
    return PaperSearchResponse(
        results=res['hits'], 
        cnt_result=len(res['hits']), 
        time_miliseconds=res['processingTimeMs']
    )


@app.get("/get_cited_by_paper", response_model=PaperWithRefs, operation_id="get_cited_by_paper")
def cited_by(
    paper_title: str = Query(..., description="Title of the paper to search for"),
    successor_hop_length: int = Query(1, ge=1, le=3, description="Number of citation hops (1-3)")
):
    root = fetch_paper_by_title(paper_title)
    if not root:
        raise HTTPException(status_code=404, detail=f"Paper with title '{paper_title}' not found")
    root['cited_by'] = fetch_citations(root.get('id'), successor_hop_length)
    return PaperWithRefs(**root)


@app.get("/get_rooted_in_paper", response_model=PaperWithRefs, operation_id="get_rooted_in_paper")
def rooted_in(
    paper_title: str = Query(..., description="Title of the paper to search for"),
    predecessor_hop_length: int = Query(1, ge=1, le=3, description="Number of reference hops (1-3)")
):
    root = fetch_paper_by_title(paper_title)
    if not root:
        raise HTTPException(status_code=404, detail=f"Paper with title '{paper_title}' not found")
    root['cites'] = fetch_origins(root.get('id'), predecessor_hop_length)
    return PaperWithRefs(**root)


@app.get("/get_literature_graph", response_model=PaperWithRefs, operation_id="get_literature_graph")
def literature_graph(
    paper_title: str = Query(..., description="Title of the paper to search for"),
    predecessor_hop_length: int = Query(1, ge=1, le=3, description="Number of reference hops (1-3)"),
    successor_hop_length: int = Query(1, ge=1, le=3, description="Number of citation hops (1-3)")
):
    root = fetch_paper_by_title(paper_title)
    if not root:
        raise HTTPException(status_code=404, detail=f"Paper with title '{paper_title}' not found")
    root['cites'] = fetch_origins(root.get('id'), predecessor_hop_length)
    root['cited_by'] = fetch_citations(root.get('id'), successor_hop_length)
    return PaperWithRefs(**root)


@app.get("/get_paper_by_id", response_model=Paper, operation_id="get_paper_by_id")
def get_paper_by_id(paper_id: int):
    res = fetch_paper_by_id(paper_id)
    if not res:
        raise HTTPException(status_code=404, detail="Paper not found")
    return res


@app.get("/get_paper_by_title", response_model=Paper, operation_id="get_paper_by_title")
def get_paper_by_title(paper_title: str):
    res = fetch_paper_by_title(paper_title)
    if not res:
        raise HTTPException(status_code=404, detail="Paper not found")
    return res


@app.get("/get_stats", response_model=StatsResponse, operation_id="get_stats")
def get_stats():
    # Example: count, by year, by author, by venue (stubbed, can be improved)
    res = mq.index(INDEX_NAME).search("", limit=0, offset=0)
    total = res["hits_total_count"]
    # For demo: not aggregating by year/author/venue
    return {"total_papers": total}


@app.get("/get_fields", operation_id="get_fields")
def get_fields():
    return [
        "id", "title", "year", "n_citation", "doc_type", "publisher", "references", "n_reference",
        "author_names", "author_orgs", "author_ids", "venue_name", "venue_id", "venue_type", "fos_names", "fos_ws"
    ]


@app.get("/get_index_info", operation_id="get_index_info")
def get_index_info():
    return mq.index(INDEX_NAME).get_stats()


mcp = FastApiMCP(
    app, 
    name="Papers and Citation Network API MCP",
    description="Papers and Citation Network API MCP",
    # base_url="http://localhost:8888/mcp",
    describe_all_responses=False,
    describe_full_response_schema=False,
    exclude_operations=[
        "health_check", 
        "get_paper_by_id", 
        "get_paper_by_title", 
        "get_stats", 
        "get_fields", 
        "get_index_info"
    ]
)
mcp.mount()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8888)
    # uvicorn.run(app, host="0.0.0.0", port=443, ssl_keyfile="key.pem", ssl_certfile="cert.pem")
