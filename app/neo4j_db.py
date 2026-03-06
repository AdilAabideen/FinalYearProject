from functools import lru_cache
from neo4j import GraphDatabase
from app.config import settings


@lru_cache
def get_neo4j_driver():
    """
    Lazily construct and cache the Neo4j driver.
    
    Returns:
        GraphDatabase driver instance
        
    Raises:
        RuntimeError: If Neo4j credentials are not configured
    """
    if not settings.NEO4J_URI:
        raise RuntimeError(
            "NEO4J_URI is not set. Add it to `.env` (see `.env.example`)."
        )
    
    if not settings.NEO4J_PASSWORD:
        raise RuntimeError(
            "NEO4J_PASSWORD is not set. Add it to `.env` (see `.env.example`)."
        )
    
    return GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER or "neo4j", settings.NEO4J_PASSWORD)
    )


