The overall goal of this assignment is to build a biomedical search and question-answering system using PubMed abstracts. Instead of relying only on keyword search, the assignment uses embeddings to represent abstracts as vectors, stores them in ChromaDB, and then uses those retrieved abstracts as context for an LLM-based RAG system.

Part 1 Summary

In Part 1, the PubMed XML file was processed to extract each article’s PMID, title, and abstract. The abstracts were cleaned using a similar approach to Assignment 7, including lowercasing, removing punctuation, removing numbers, removing stopwords, and lemmatizing words. Then, a ChromaDB vector database was created. Each abstract was converted into an embedding using ChromaDB’s default embedding model and inserted into the database in batches to make the loading process more efficient and reliable.

Part 2 Summary

In Part 2, a Flask app was created to search the embedded PubMed abstracts. The app allows a user to enter a word, phrase, or sentence through a web interface. Flask sends that query to ChromaDB, which embeds the query and compares it to the stored abstract embeddings. The app then returns the top 5 closest abstracts, including their PMID, title, abstract text, and distance score. This makes the search semantic rather than only keyword-based.

Part 3 Summary

In Part 3, a RAG system was built using ChromaDB and an LLM through OpenRouter. When the user asks an open-ended question, the system first retrieves the most relevant abstracts from ChromaDB. Those abstracts are then formatted as context and sent to the LLM along with the original question. The model is instructed to answer only using the retrieved PubMed abstracts and to cite PMIDs when possible. This allows the final answer to be grounded in the database instead of relying only on the model’s pre-trained knowledge.