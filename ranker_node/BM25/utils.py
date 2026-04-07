from math import log

def compute_idf(documents, term, text_key="name"):
    """
    Compute Inverse Document Frequency (IDF) for a term.
    
    Args:
        documents: List of documents
        term: Term to compute IDF for
        text_key: Key in document dict to search in (uses 'dictionary' column if available)
        
    Returns:
        IDF score for the term
    """
    n = sum(
        1 for doc in documents
        if term.lower() in doc.get(text_key, '').lower().split()
    )
    idf = log((len(documents) - n + 0.5) / (n + 0.5)) if n < len(documents) else 0.0
    return idf

def compute_tf(term, document, text_key="name"):
    """
    Compute Term Frequency (TF) for a term in a document.
    
    Args:
        term: Term to search for
        document: Document dict
        text_key: Key in document dict to search in (uses 'dictionary' column if available)
        
    Returns:
        Term frequency count
    """
    doc_text = document.get(text_key, '')
    return doc_text.lower().split().count(term.lower())


def getAVGDocLength(documents, text_key="name"):
    """
    Calculate average document length in terms of token count.
    
    Args:
        documents: List of documents
        text_key: Key in document dict to measure (uses 'dictionary' column if available)
        
    Returns:
        Average document length
    """
    total_length = sum(len(doc.get(text_key, '').split()) for doc in documents)
    return total_length / len(documents) if documents else 0


def select_text_key(document):
    """
    Helper function to select the best available text field for BM25.
    Priority: dictionary > search_text > description > name
    
    Args:
        document: Document dict
        
    Returns:
        Tuple of (text_key, text_value) to use for BM25
    """
    # When dictionary column is filled, use it for better BM25 results
    if "dictionary" in document and document["dictionary"]:
        return "dictionary", document["dictionary"]
    elif "search_text" in document and document["search_text"]:
        return "search_text", document["search_text"]
    elif "description" in document and document["description"]:
        return "description", document["description"]
    else:
        return "name", document.get("name", "")