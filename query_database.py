import chromadb
import arabic_reshaper
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer

# Initialize the model and embedding function
model_name = "akhooli/Arabic-SBERT-100K"
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)

# Connect to the ChromaDB server using the HttpClient (assuming the server is running on localhost:8000)
chroma_client = chromadb.HttpClient(host='localhost', port=8000)

# Try to get the collection with the custom embedding function
try:
    collection = chroma_client.get_collection("recipestest", embedding_function=sentence_transformer_ef)
    print("Collection 'recipes' found.")
except chromadb.errors.InvalidCollectionException:
    print("Collection 'recipes' does not exist. Please add data first using add_data_to_database.py.")
    exit()

# Function to query the database
def search_recipe(query_text):
    results = collection.query(
        query_texts=[query_text], 
        n_results=4,
    )

    print("Search Results:")
    print(results)
    for result in results["documents"]:
        print(arabic_reshaper.reshape(result[0])[::-1])

# Example search query
search_recipe("ورق عنب")
