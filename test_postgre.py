from app.services.postgresql_service import postgres_service


query = "что такое пластовые воды"

results = postgres_service.search_geology_blocks(query, top_k=5)

for item in results:
    print("=" * 80)
    print("ID:", item["source_id"])
    print("Название:", item["title"])
    print("Score:", item["score"])
    print("Описание:", item["content"][:500])