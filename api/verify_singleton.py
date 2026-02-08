from app.core.dependencies import get_embeddings_service

print("Calling get_embeddings_service() first time...")
s1 = get_embeddings_service()
print(f"First instance: {id(s1)}")

print("Calling get_embeddings_service() second time...")
s2 = get_embeddings_service()
print(f"Second instance: {id(s2)}")

if s1 is s2:
    print("SUCCESS: Service is singleton")
else:
    print("FAILURE: Services are different instances")
    exit(1)
