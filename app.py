# 1) Browser / curl request
# 2) Flask receives URL
# 3) Flask extracts keyword from URL
# 4) Flask sends query to Elasticsearch
# 5) Elasticsearch searches PubMed index
#6) Flask returns results as JSON

# Import Flask tools: Flask creates the web app, request lets us read query parameters from the URL, jsonify converts Python dictionaries/lists into JSON responses.

import os
import threading
import webbrowser

# Add ChromaDB and connect to ChromaDB foldeR:
import chromadb
CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "pubmed_abstracts"

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_collection(name=COLLECTION_NAME)

from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

APP_URL = "http://127.0.0.1:5000/"


def open_browser():
    webbrowser.open(APP_URL)

# Helper function that searches database and 
def search_abstracts(query, size=5):
    response = collection.query(
        query_texts=[query],
        n_results=size
    )
    
    results = []

    for pmid, abstract,metadata, distance in zip(
        response["ids"][0],
        response["documents"][0],
        response["metadatas"][0],
        response["distances"][0]
    ):
        results.append({
            "pmid": pmid,
            "title": metadata["title"],
            "abstract": abstract,
            "distance": distance
        })

    return results

# Home page with forms for searching documents
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


# Creates an API endpoint called /keyword_search.

@app.route("/search", methods=["GET", "POST"])
def search():
    # GET reads keyword from the URL; POST reads keyword from the HTML form.
    if request.method == "POST":
        query = request.form.get("query")
    else:
        query = request.args.get("query")

    if not query:
        if request.method == "POST":
            return render_template("index.html", error="Please provide a search query.")
        return jsonify({"error": "Please provide a query parameter"}), 400

    # Search the abstract field in the pubmed index for the keyword, and return up to 10 matching documents.
    results = search_abstracts(query, size=5)

    if request.method == "POST":
        return render_template(
            "index.html",
            query=query,
            results=results
        )

    # Returns the search response as JSON: keyword searched,how many results were returned, and actual matching documents
    return jsonify({
        "query": query,
        "num_results_returned": len(results),
        "results": results
    })

if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Timer(1, open_browser).start()

    app.run(debug=True)
