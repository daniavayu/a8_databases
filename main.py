# Reads the XML, cleans abstracts, stores them in ChromaDB as embeddings, 
# and lets you test semantic search from the command line.

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
import nltk
nltk.download("stopwords")
nltk.download("punkt")
nltk.download("wordnet")

XML_FILE = "pubmed25n0001.xml"
CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "pubmed_abstracts"
BATCH_SIZE = 500

#  Extracts text from an XML element. If the element is missing, it returns an 
#  empty string. Otherwise, it collects all text inside the element, strips extra 
#  spaces, and joins it into one clean string.
def get_text(element):
    """Return all text inside an XML element, including nested tags."""
    if element is None:
        return ""
    return " ".join(text.strip() for text in element.itertext() if text.strip())

# Load stopwords, WordNetLemmatizer and word_tokenize
def load_nltk_helpers():
        from nltk.corpus import stopwords
        from nltk.stem import WordNetLemmatizer
        from nltk.tokenize import word_tokenize
        return set(stopwords.words("english")), WordNetLemmatizer(), word_tokenize

STOP_WORDS, LEMMATIZER, WORD_TOKENIZE = load_nltk_helpers()

# Clean abstract
def preprocess_abstract(text):
    """Apply the same cleaning donde for A7: lowercase, words only, stopwords out."""
    if not text:
        return ""

    # The abstract is lowercased and split into words.
    tokens = WORD_TOKENIZE(text.lower())

    # Remove punctuation, numbers, symbols, and stopwords.
    processed_tokens = []
    for token in tokens:
        if not token.isalpha() or token in STOP_WORDS:
            continue
        if LEMMATIZER is not None:
            token = LEMMATIZER.lemmatize(token)
        processed_tokens.append(token)

    return " ".join(processed_tokens)

# Reads the XML and creates a list of article dictionaries.
def parse_pubmed_xml(file_path):
    documents = []

    # This loops through the XML efficiently. iterparse is better than loading the entire XML tree at once because the PubMed file is large.
    for _, article in ET.iterparse(file_path, events=("end",)):
        if article.tag != "PubmedArticle":
            continue

        pmid = get_text(article.find(".//MedlineCitation/PMID"))
        title = get_text(article.find(".//Article/ArticleTitle"))
        abstract_parts = [
            get_text(node) for node in article.findall(".//Article/Abstract/AbstractText")
        ]
        # The abstract sections are joined, then cleaned.
        raw_abstract = " ".join(part for part in abstract_parts if part)
        processed_abstract = preprocess_abstract(raw_abstract)

        # Only articles with both a PMID and non-empty abstract are saved.
        if pmid and processed_abstract:
            documents.append(
                {
                    "pmid": pmid,
                    "title": title,
                    "abstract": processed_abstract,
                }
            )

        # Save memory
        article.clear()

    return documents

# Splits the list of abstracts into smaller groups of 500.
def batched(items, batch_size):
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]

# Loads data to ChromaDB
def load_chromadb(documents, db_path=CHROMA_PATH, collection_name=COLLECTION_NAME):
    import chromadb

    # Creates a local database saved in chroma_db/
    client = chromadb.PersistentClient(path=db_path)
    # Either opens the existing pubmed_abstracts collection or creates it.
    collection = client.get_or_create_collection(name=collection_name)

    # Loops through 500 abstracts at a time, inserts records in ChromaDB.
    # ChromaDB automatically converts each abstract into an embedding using its default model.
    for batch_number, batch in enumerate(batched(documents, BATCH_SIZE), start=1):
        # Upsert avoids duplicates
        collection.upsert(
            ids=[doc["pmid"] for doc in batch],
            documents=[doc["abstract"] for doc in batch],
            metadatas=[
                {
                    "pmid": doc["pmid"],
                    "title": doc["title"],
                }
                for doc in batch
            ],
        )
        print(f"Loaded batch {batch_number}: {len(batch)} abstracts")

    return collection

# Reconnects to the saved ChromaDB database.
def get_collection(db_path=CHROMA_PATH, collection_name=COLLECTION_NAME):
    import chromadb
    client = chromadb.PersistentClient(path=db_path)
    return client.get_collection(name=collection_name)

# Searches the ChromaDB collection.
def search_abstracts(query, n_results=5, db_path=CHROMA_PATH, collection_name=COLLECTION_NAME):
    collection = get_collection(db_path=db_path, collection_name=collection_name)
    # ChromaDB embeds the search query, compares it to stored abstract embeddings, and returns the closest abstracts.
    response = collection.query(query_texts=[query], n_results=n_results)

    # Formats ChromaDB’s response into a clean list of dictionaries: PMID, title, abstract, and distance score.
    results = []
    for pmid, abstract, metadata, distance in zip(
        response["ids"][0],
        response["documents"][0],
        response["metadatas"][0],
        response["distances"][0],
    ):
        results.append(
            {
                "pmid": pmid,
                "title": metadata["title"],
                "abstract": abstract,
                "distance": distance,
            }
        )

    return results


def main():
    parser = argparse.ArgumentParser(description="Load PubMed abstracts into ChromaDB.")
    parser.add_argument("--xml-file", default=XML_FILE)
    parser.add_argument("--db-path", default=CHROMA_PATH)
    parser.add_argument("--collection", default=COLLECTION_NAME)
    parser.add_argument("--query", help="Optional query to test the loaded ChromaDB collection.")
    args = parser.parse_args()

    if args.query:
        for result in search_abstracts(
            args.query,
            db_path=args.db_path,
            collection_name=args.collection,
        ):
            print(f"{result['pmid']} | distance={result['distance']:.4f}")
            print(result["title"])
            print()
        return

    xml_path = Path(args.xml_file)
    if not xml_path.exists():
        raise FileNotFoundError(f"Could not find XML file: {xml_path}")

    documents = parse_pubmed_xml(xml_path)
    print(f"Parsed {len(documents)} abstracts with PMID, title, and abstract text.")

    collection = load_chromadb(
        documents,
        db_path=args.db_path,
        collection_name=args.collection,
    )
    print(f"ChromaDB collection '{args.collection}' now has {collection.count()} records.")


if __name__ == "__main__":
    main()
