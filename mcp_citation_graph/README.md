# AI Agent with MCP Integration to Search Academic Papers

This project creates an AI agent on top of a comprehensive academic paper citation network data (5M+ papers). Various technologies are used in this project including MCP server, MCP client, vector search, graph databases, and AI agents. 

**The system processes DBLP academic paper data, creates searchable indexes, REST APIs for querying the citation network, MCP server to convert the APIs into LLM-ready tools, MCP client to discover and invoke tools, and an intelligent agent interface that puts everything together for querying the citation network and answering research questions.**

## Architecture Overview

The application consists of several interconnected components:

1. **Data Preparation** ([data_prep.py](data_prep.py)) - Processes raw DBLP data
2. **Vector Database Indexing** ([marqo_index.py](marqo_index.py)) - Creates searchable vector embeddings
3. **Graph Database** ([graph_db.py](graph_db.py)) - Builds Neo4j citation network
4. **FastAPI Backend and MCP Server** ([fastapi_backend.py](fastapi_backend.py)) - REST API with MCP server
5. **MCP Client and AI Agent** ([mcp_agent.py](mcp_agent.py)) - AI agent and the MCP client
6. **Streamlit Interface** ([streamlit_agent.py](streamlit_agent.py)) - Web UI to interact with the agent

## Prerequisites

### Required Services
- **Neo4j Database**: Running on `bolt://127.0.0.1:7687`
- **Marqo Vector Database**: Running on `http://localhost:8882`
- **Python 3.8+**

### Required Python Packages
```bash
pip install neo4j marqo fastapi uvicorn streamlit asyncio httpx tqdm scikit-learn
pip install ijson pandas agents fastapi-mcp pydantic
```

### Data Requirements
- DBLP dataset: data/dblp.v12.json (download from [Kaggle - Citation Network Dataset](https://www.kaggle.com/datasets/mathurinache/citation-network-dataset))

## Step-by-Step Setup and Usage
### Step 1: Data Preparation
The `process_dblp` function in [data_prep.py](data_prep.py) processes the raw DBLP dataset:

#### What it does:

- Filters papers to include only Conference, Journal, and Book publications.
- Requires papers to have references (citation data).
- Flattens nested author, venue, and field-of-study structures.
- Applies additional filters for papers from 2000+ with substantial citations/references.

#### Run data preparation:

```
python data_prep.py
```

#### Output files:

- `data/dblp.filtered.json` - All filtered papers
- `data/dblp.filtered.y2000_r9_c5.json` - Further filtered subset

### Step 2: Vector Database Indexing (Marqo)
The [marqo_index.py](marqo_index.py) script creates a searchable vector index.

#### Features:

- Creates structured Marqo index with semantic and vector search capabilities.
- Generates n-grams for authors and venues for better text matching.
- Indexes paper titles, authors, venues, and fields of study.
- Uses `hf/e5-base-v2` model for embeddings.

#### Start Marqo server:

```
docker run --name marqo -it -p 8882:8882 marqoai/marqo:latest
```

#### Run indexing:

```
python marqo_index.py
```

### Step 3: Graph Database Setup (Neo4j)
The `Neo4jCitationNetwork` class in [graph_db.py](graph_db.py) creates a citation network graph.

#### Graph Structure:

- **Nodes:** Papers, Authors, Venues, Fields of Study
- **Relationships:** `CITES`, `WROTE`, `PUBLISHED_IN`, `IN_FIELD`
- **Constraints:** Unique IDs for all node types
- **Indexes:** Optimized for common queries

#### Start Neo4j:

```
docker run \
    --restart always \
    --publish=7474:7474 --publish=7687:7687 \
    --env NEO4J_AUTH=neo4j/neo4j \
    --volume=~/data:/data \
    neo4j:2025.05.0
```

#### Build citation graph:

```
python graph_db.py
```

### Step 4: FastAPI Backend with MCP Server

The [fastapi_backend.py](fastapi_backend.py) provides both REST API and MCP server functionality.

API Endpoints:

- `/search_papers_by_topic` - Search papers by topic, author, venue, etc.
- `/get_cited_by_paper` - Find papers that cite a specific paper.
- `/get_rooted_in_paper` - Find papers that a specific paper references.
- `/get_literature_graph` - Get both citations and references for a paper.

MCP Integration:

- Automatically exposes select endpoints as MCP tools.
- Provides structured schema for AI agent interactions.

#### Start the server:

```
python fastapi_backend.py
```

The server runs on `http://localhost:8888` with MCP endpoint at `http://localhost:8888/mcp`.

### Step 5: MCP Agent Setup

The `MCPAgent` class in [mcp_agent.py](mcp_agent.py) creates an AI agent that can use the MCP tools.

#### Features:

- Connects to MCP servers via SSE (Server-Sent Events).
- Uses `gpt-4o` as backend Large Language Model (LLM).
- Automatically discovers and uses available tools.
- Handles async operations for real-time interactions.

### Step 6: Streamlit User Interface

The [streamlit_agent.py](streamlit_agent.py) provides a web-based chat interface.

#### Features:

- Interactive chat interface for querying the citation network.
- Real-time responses from the AI agent.
- Conversation history.
- Error handling and user feedback.

#### Start the Streamlit app:

```
streamlit run streamlit_agent.py
```

Access the interface at `http://localhost:8501`

#### Usage Examples:

Query Examples via Streamlit Interface:
1. **Search for papers:** "Find top 5 papers about graph neural networks"
2. **Citation analysis:** "What papers cite 'Attention Is All You Need'?"
3. **Research lineage:** "Show me the research lineage of transformer models"
4. **Author analysis:** "Find papers by Yoshua Bengio in deep learning"
5. **Venue analysis:** "What are the most cited papers from ICML 2020?"

#### Direct API Usage:

```python
import requests

# Search papers by topic
response = requests.get(
    "http://localhost:8888/search_papers_by_topic",
    params={
        "research_topic": "graph neural networks",
        "min_year": 2018,
        "limit": 10
    }
)

# Get citation network
response = requests.get(
    "http://localhost:8888/get_literature_graph",
    params={
        "paper_title": "Attention Is All You Need",
        "predecessor_hop_length": 2,
        "successor_hop_length": 2
    }
)
```

## File Structure

```
mcp_citation_graph/
├── data/
│   ├── dblp.v12.json                    # Raw DBLP dataset
│   ├── dblp.filtered.json               # Filtered dataset
│   └── dblp.filtered.y2000_r9_c5.json   # Final filtered dataset
├── data_prep.py                         # Data preprocessing
├── marqo_index.py                       # Vector database indexing
├── graph_db.py                          # Neo4j graph database
├── fastapi_backend.py                   # REST API + MCP server
├── mcp_agent.py                         # AI agent with MCP integration
├── README.md                            # The readme file
└── streamlit_agent.py                   # Web UI
```

## Configuration
Environment Variables for the application:

```
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="neo4j"
export MARQO_URL="http://localhost:8882"
export OPENAI_API_KEY="your_openai_key"
```

## Troubleshooting

Common Issues:
- **Neo4j Connection Failed:** Ensure Neo4j is running and credentials are correct
- **Marqo Index Error:** Check if Marqo server is accessible and has sufficient memory
- **MCP Connection Timeout:** Verify FastAPI server is running on port 8888
- **Memory Issues:** Reduce batch sizes during indexing

## Logs and Monitoring:
- Check Neo4j logs: `data/logs/neo4j.log`
- FastAPI logs: Console output when running `python fastapi_backend.py`
- Streamlit logs: Console output when running `streamlit run streamlit_agent.py`

## License
This project is licensed under the MIT License.
