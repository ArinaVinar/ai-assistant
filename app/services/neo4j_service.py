from neo4j import GraphDatabase

from app.config import settings
from app.services.embedding_service import embedding_service


class Neo4jService:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    def close(self):
        self.driver.close()

    def search_elements_semantic(self, query: str, top_k: int | None = None) -> list[dict]:

        top_k = top_k or settings.neo4j_top_k
        query_embedding = embedding_service.embed_query(query)

        cypher = """
        CALL db.index.vector.queryNodes(
            'navigator_node_embedding_index',
            $top_k,
            $query_embedding
        )
        YIELD node, score

        OPTIONAL MATCH path = (root)-[:HAS_CHILD|INCLUDE|HAS_ADD_INFO*0..8]->(node)
        WHERE NOT (()-[:HAS_CHILD|INCLUDE|HAS_ADD_INFO]->(root))

        WITH node, score, path
        ORDER BY score DESC

        RETURN
            node.id AS node_id,
            labels(node) AS labels,
            node.name AS name,
            node.description AS description,
            score,
            [x IN nodes(path) | x.name] AS route
        LIMIT $top_k;
        """

        with self.driver.session() as session:
            rows = session.run(
                cypher,
                top_k=top_k,
                query_embedding=query_embedding,
            )

            results = [dict(row) for row in rows]

        return [
            {
                "source_type": "neo4j",
                "source_id": item.get("node_id"),
                "title": item.get("name"),
                "content": item.get("description"),
                "route": item.get("route") or [],
                "labels": item.get("labels") or [],
                "score": float(item.get("score")) if item.get("score") is not None else None,
            }
            for item in results
        ]


neo4j_service = Neo4jService()
