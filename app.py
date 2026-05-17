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

from flask import Flask, request, jsonify, render_template
from elasticsearch import Elasticsearch

app = Flask(__name__)

# Connect to the local Elasticsearch server.
# localhost:9200 is where the Docker Elasticsearch container is running.
es = Elasticsearch("http://localhost:9200")
INDEX_NAME = "pubmed"
APP_URL = "http://127.0.0.1:5000/"


def open_browser():
    webbrowser.open(APP_URL)

# Helper function that searches Elasticsearch and returns matching documents.
def search_abstracts(keyword, size=10):
    response = es.search(
        index=INDEX_NAME,
        query={
            "match": {
                "abstract": keyword
            }
        },
        size=size
    )

    results = []

    for hit in response["hits"]["hits"]:
        results.append(hit["_source"])

    return results


# Helper function that counts documents matching a keyword, with an optional excluded word.
def count_matching_docs(keyword, exclude=None):
    must_conditions = [
        {
            "match": {
                "abstract": keyword
            }
        }
    ]

    must_not_conditions = []

    if exclude:
        must_not_conditions.append(
            {
                "match": {
                    "abstract": exclude
                }
            }
        )

    response = es.count(
        index=INDEX_NAME,
        query={
            "bool": {
                "must": must_conditions,
                "must_not": must_not_conditions
            }
        }
    )

    return response["count"]


# Home page with forms for searching and counting documents.
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


# Creates an API endpoint called /keyword_search.

@app.route("/keyword_search", methods=["GET", "POST"])
def keyword_search():
    # GET reads keyword from the URL; POST reads keyword from the HTML form.
    if request.method == "POST":
        keyword = request.form.get("keyword")
    else:
        keyword = request.args.get("keyword")

    if not keyword:
        if request.method == "POST":
            return render_template("index.html", error="Please provide a keyword.")
        return jsonify({"error": "Please provide a keyword parameter"}), 400

    # Search the abstract field in the pubmed index for the keyword, and return up to 10 matching documents.
    results = search_abstracts(keyword)

    if request.method == "POST":
        return render_template(
            "index.html",
            keyword=keyword,
            results=results
        )

    # Returns the search response as JSON: keyword searched,how many results were returned, and actual matching documents
    return jsonify({
        "keyword": keyword,
        "num_results_returned": len(results),
        "results": results
    })

# Placeholder
@app.route("/keyword_search_with_typo", methods=["GET", "POST"])
def keyword_search_with_typo():
    return jsonify({
        "message": "This endpoint is for Part 3."
    })


# Keyword is required, exclude is optional.
@app.route("/count_docs", methods=["GET", "POST"])
def count_docs():
    if request.method == "POST":
        keyword = request.form.get("keyword")
        exclude = request.form.get("exclude")
    else:
        keyword = request.args.get("keyword")
        exclude = request.args.get("exclude")

    if not keyword:
        if request.method == "POST":
            return render_template("index.html", error="Please provide a keyword.")
        return jsonify({"error": "Please provide a keyword parameter"}), 400

    # Asks Elasticsearch to count matching documents.
    count = count_matching_docs(keyword, exclude)

    if request.method == "POST":
        return render_template(
            "index.html",
            count_keyword=keyword,
            exclude=exclude,
            count=count
        )

    # This returns the count as JSON.
    return jsonify({
        "keyword": keyword,
        "exclude": exclude,
        "count": count
    })


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Timer(1, open_browser).start()

    app.run(debug=True)
