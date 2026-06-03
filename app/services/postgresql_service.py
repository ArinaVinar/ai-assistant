import psycopg2
from pgvector.psycopg2 import register_vector

from app.config import settings
from app.services.embedding_service import embedding_service


class PostgresService:
    def __init__(self):
        self.connection_params = {
            "host": settings.postgres_host,
            "port": settings.postgres_port,
            "dbname": settings.postgres_db,
            "user": settings.postgres_user,
            "password": settings.postgres_password,
        }

    def get_connection(self):
        connection = psycopg2.connect(**self.connection_params)
        register_vector(connection)
        return connection

    def search_geology_blocks(self, query: str, top_k: int | None = None) -> list[dict]:
        """
        Семантический поиск по геологическим знаниям в PostgreSQL.
        """

        top_k = top_k or settings.postgres_top_k
        query_embedding = embedding_service.embed_query(query)

        sql = """
        SELECT
            id,
            title,
            description,
            1 - (embedding <=> %s::vector) AS score
        FROM geology_blocks
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
        """

        with self.get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql,
                    (
                        query_embedding,
                        query_embedding,
                        top_k,
                    ),
                )
                rows = cursor.fetchall()

        return [
            {
                "source_type": "postgres",
                "source_id": row[0],
                "title": row[1],
                "content": row[2],
                "score": float(row[3]) if row[3] is not None else None,
            }
            for row in rows
        ]


postgres_service = PostgresService()