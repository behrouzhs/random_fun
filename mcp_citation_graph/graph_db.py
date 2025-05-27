import json
import os
import time
import concurrent.futures
from neo4j import GraphDatabase
from tqdm import tqdm
import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

NEO4J_URI = "bolt://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4j"
DEFAULT_WORKERS = 4
DEFAULT_BATCH_SIZE = 100

class Neo4jCitationNetwork:
    def __init__(self, uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD, database='papers'):
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.driver = GraphDatabase.driver(uri, auth=(user, password), database=database)
        
    def close(self):
        self.driver.close()
        
    def create_constraints(self):
        with self.driver.session() as session:
            try:
                session.run("CREATE CONSTRAINT paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.id IS UNIQUE")
                session.run("CREATE CONSTRAINT author_id IF NOT EXISTS FOR (a:Author) REQUIRE a.id IS UNIQUE")
                session.run("CREATE CONSTRAINT venue_id IF NOT EXISTS FOR (v:Venue) REQUIRE v.id IS UNIQUE")
                logger.info("Constraints created successfully")
            except Exception as e:
                logger.error(f"Error creating constraints: {e}")
    
    def create_indexes(self):
        with self.driver.session() as session:
            try:
                session.run("CREATE INDEX paper_title IF NOT EXISTS FOR (p:Paper) ON (p.title)")
                session.run("CREATE INDEX paper_year IF NOT EXISTS FOR (p:Paper) ON (p.year)")
                session.run("CREATE INDEX author_name IF NOT EXISTS FOR (a:Author) ON (a.name)")
                session.run("CREATE INDEX venue_name IF NOT EXISTS FOR (v:Venue) ON (v.name)")
                logger.info("Indexes created successfully")
            except Exception as e:
                logger.error(f"Error creating indexes: {e}")
    
    def create_paper_node(self, tx, paper):
        query = """
        MERGE (p:Paper {id: $id})
        ON CREATE SET 
            p.title = $title,
            p.year = $year,
            p.n_citation = $n_citation,
            p.doc_type = $doc_type,
            p.publisher = $publisher,
            p.n_reference = $n_reference
        """
        tx.run(query, 
               id=paper["id"],
               title=paper["title"],
               year=paper["year"],
               n_citation=paper.get("n_citation", 0),
               doc_type=paper.get("doc_type", ""),
               publisher=paper.get("publisher", ""),
               n_reference=paper.get("n_reference", 0))
    
    def create_authors(self, tx, paper):
        if "author_names" not in paper or "author_ids" not in paper:
            return
            
        for i, (name, auth_id) in enumerate(zip(paper["author_names"], paper["author_ids"])):
            org = paper["author_orgs"][i] if "author_orgs" in paper and i < len(paper["author_orgs"]) else ""
            
            # Create author node
            query = """
            MERGE (a:Author {id: $auth_id})
            ON CREATE SET 
                a.name = $name,
                a.organization = $org
            """
            tx.run(query, auth_id=auth_id, name=name, org=org)
            
            # Create author-paper relationship
            query = """
            MATCH (a:Author {id: $auth_id})
            MATCH (p:Paper {id: $paper_id})
            MERGE (a)-[r:WROTE]->(p)
            ON CREATE SET r.position = $position
            """
            tx.run(query, auth_id=auth_id, paper_id=paper["id"], position=i)
    
    def create_venue(self, tx, paper):
        if "venue_name" not in paper or "venue_id" not in paper:
            return
            
        # Create venue node
        query = """
        MERGE (v:Venue {id: $venue_id})
        ON CREATE SET 
            v.name = $venue_name,
            v.type = $venue_type
        """
        tx.run(query, 
               venue_id=paper["venue_id"],
               venue_name=paper["venue_name"],
               venue_type=paper.get("venue_type", ""))
        
        # Create venue-paper relationship
        query = """
        MATCH (v:Venue {id: $venue_id})
        MATCH (p:Paper {id: $paper_id})
        MERGE (p)-[r:PUBLISHED_IN]->(v)
        """
        tx.run(query, venue_id=paper["venue_id"], paper_id=paper["id"])
    
    def create_citations(self, tx, paper):
        if "references" not in paper or not paper["references"]:
            return
            
        # Create citation relationships
        for ref_id in paper["references"]:
            query = """
            MATCH (p1:Paper {id: $paper_id})
            MERGE (p2:Paper {id: $ref_id})
            MERGE (p1)-[r:CITES]->(p2)
            """
            tx.run(query, paper_id=paper["id"], ref_id=ref_id)
    
    def create_fields_of_study(self, tx, paper):
        if "fos_names" not in paper or not paper["fos_names"]:
            return
            
        # Create field of study nodes and relationships
        for i, fos_name in enumerate(paper["fos_names"]):
            weight = paper["fos_ws"][i] if "fos_ws" in paper and i < len(paper["fos_ws"]) else 0.0
            
            # Create field of study node
            query = """
            MERGE (f:FieldOfStudy {name: $fos_name})
            """
            tx.run(query, fos_name=fos_name)
            
            # Create paper-field relationship
            query = """
            MATCH (p:Paper {id: $paper_id})
            MATCH (f:FieldOfStudy {name: $fos_name})
            MERGE (p)-[r:IN_FIELD]->(f)
            ON CREATE SET r.weight = $weight
            """
            tx.run(query, paper_id=paper["id"], fos_name=fos_name, weight=weight)
    
    def process_paper(self, tx, paper):
        self.create_paper_node(tx, paper)
        self.create_authors(tx, paper)
        self.create_venue(tx, paper)
        self.create_citations(tx, paper)
        self.create_fields_of_study(tx, paper)
    
    def process_data_file(self, file_path, num_workers=DEFAULT_WORKERS, batch_size=DEFAULT_BATCH_SIZE):
        logger.info(f"Processing file: {file_path}")
        total_papers = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line == "[":
                pass
            else:
                total_papers += 1
                
            for line in f:
                line = line.strip()
                if line.startswith("{"):
                    total_papers += 1
        
        logger.info(f"Found {total_papers} papers to process")
        
        batches = []
        current_batch = []
        batch_count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            
            if first_line != "[":
                paper_json = first_line.lstrip("[").rstrip(",")
                try:
                    current_batch.append(json.loads(paper_json))
                except json.JSONDecodeError:
                    logger.error(f"Error parsing JSON from first line")
            
            for line in f:
                line = line.strip()
                if not line or line == "]":
                    continue
                
                if line.endswith(","):
                    line = line[:-1]
                
                try:
                    paper = json.loads(line)
                    current_batch.append(paper)
                    
                    if len(current_batch) >= batch_size:
                        batches.append(current_batch)
                        current_batch = []
                        batch_count += 1
                        if batch_count % 10 == 0:
                            logger.info(f"Created {batch_count} batches")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing JSON: {e}, Line: {line[:100]}...")
            
            if current_batch:
                batches.append(current_batch)
        
        logger.info(f"Created {len(batches)} batches of approximately {batch_size} papers each")
        
        start_time = time.time()
        if num_workers <= 1:
            logger.info("Using sequential processing")
            for i, batch in enumerate(batches):
                if i % 10 == 0 or i == len(batches) - 1:
                    logger.info(f"Processing batch {i+1}/{len(batches)}")
                self._process_batch(batch)
        else:
            logger.info(f"Using parallel processing with {num_workers} workers")
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                list(tqdm(executor.map(self._process_batch, batches), total=len(batches), desc="Processing batches"))
        
        end_time = time.time()
        processing_time = end_time - start_time
        papers_per_second = total_papers / processing_time if processing_time > 0 else 0
        logger.info(f"Processing completed in {processing_time:.2f} seconds")
        logger.info(f"Processed {total_papers} papers at {papers_per_second:.2f} papers/second")
    
    def _process_batch(self, papers_batch):
        with self.driver.session() as session:
            for paper in papers_batch:
                try:
                    session.execute_write(self.process_paper, paper)
                except Exception as e:
                    logger.error(f"Error processing paper {paper.get('id', 'unknown')}: {e}")

    def create_graph(self, file_path=None, num_workers=DEFAULT_WORKERS, batch_size=DEFAULT_BATCH_SIZE):
        if file_path is None:
            file_path = os.path.join("data", "dblp.filtered.json")
            
        try:
            start_time = time.time()
            logger.info(f"Connected to Neo4j database at {self.uri}")
            
            # Create schema
            self.create_constraints()
            self.create_indexes()
            
            # Process data file
            if num_workers > 1:
                logger.info(f"Starting parallel processing with {num_workers} workers and batch size {batch_size}")
            else:
                logger.info(f"Starting sequential processing with batch size {batch_size}")
                
            self.process_data_file(file_path, num_workers=num_workers, batch_size=batch_size)
            total_time = time.time() - start_time
            logger.info(f"Data processing completed in {total_time:.2f} seconds")
            self.close()

            return total_time
        except Exception as e:
            logger.error(f"Error creating graph: {e}")
            raise


if __name__ == "__main__":
    client = Neo4jCitationNetwork()
    client.create_graph()#file_path='data/dblp.filtered.y2000_r9_c5.json')
