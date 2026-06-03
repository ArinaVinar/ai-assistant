from app.services.ollama_service import ollama_service


answer = ollama_service.generate("Кратко ответь: что такое Neo4j?")
print(answer)