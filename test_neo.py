from app.services.neo4j_service import neo4j_service


query = "где посмотреть данные по скважинам"

results = neo4j_service.search_elements_semantic(query, top_k=5)

for item in results:
    print("=" * 80)
    print("ID:", item["source_id"])
    print("Название:", item["title"])
    print("Score:", item["score"])
    print("Labels:", item["labels"])
    print("Маршрут:", " → ".join(item["route"]))
    print("Описание:", item["content"])