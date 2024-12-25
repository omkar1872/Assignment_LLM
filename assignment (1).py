# -*- coding: utf-8 -*-
"""ASSIGNMENT.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1igiTrCE2gxHm_M3iLX_ps24tCXTaiWpL
"""

!pip install PyPDF2 sentence-transformers transformers gradio sklearn

from PyPDF2 import PdfReader
import json
from sentence_transformers import SentenceTransformer
from transformers import pipeline

# Function to extract text from a PDF file
def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

# Example PDF paths
pdf_paths = ["/content/textbook1.pdf", "/content/textbook2.pdf", "/content/textbook3.pdf"]
textbooks = {f"Textbook-{i+1}": extract_text_from_pdf(path) for i, path in enumerate(pdf_paths)}

# Function to build a hierarchical index for the textbooks
def build_hierarchical_index(textbooks):
    index = {}
    for book, content in textbooks.items():
        chapters = content.split("Chapter ")[1:]  # Assuming chapters are labeled as "Chapter X"
        index[book] = {}
        for chapter in chapters:
            sections = chapter.split("Section ")[1:]  # Assuming sections are labeled as "Section X"
            chapter_title = chapter.split("\n")[0].strip()
            index[book][chapter_title] = {}
            for section in sections:
                section_title = section.split("\n")[0].strip()
                paragraphs = section.split("\n")[1:]  # Split sections into paragraphs
                index[book][chapter_title][section_title] = paragraphs
    return index

# Build the hierarchical index for textbooks
hierarchical_index = build_hierarchical_index(textbooks)

# Load Sentence-BERT model
model = SentenceTransformer('all-MiniLM-L6-v2')

from transformers import pipeline
import numpy as np

# Initialize GPT-2 model for answer generation with increased max length
llm = pipeline("text-generation", model="gpt2", max_new_tokens=500)

# Implement BM25 and semantic retrieval methods
from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import util

def bm25_retrieval(query, paragraphs):
    """Implements BM25 retrieval using TF-IDF Vectorization."""
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(paragraphs)
    query_vec = vectorizer.transform([query])
    scores = (tfidf_matrix * query_vec.T).toarray()
    return scores.flatten()

def semantic_retrieval(query, paragraphs, model):
    """Implements semantic retrieval using Sentence-BERT."""
    embeddings = model.encode(paragraphs, convert_to_tensor=True)
    query_embedding = model.encode(query, convert_to_tensor=True)
    scores = util.pytorch_cos_sim(query_embedding, embeddings).cpu().numpy()
    return scores.flatten()

def hybrid_retrieval(query, paragraphs, model):
    """Combines BM25 and semantic retrieval."""
    bm25_scores = bm25_retrieval(query, paragraphs)
    semantic_scores = semantic_retrieval(query, paragraphs, model)
    combined_scores = bm25_scores + semantic_scores
    return combined_scores

# Function to retrieve and generate answers with content length limiting
def retrieve_and_generate(query, index, model, llm, max_input_length=1000):
    retrieved_content = []
    context = []

    for book, chapters in index.items():
        for chapter, sections in chapters.items():
            for section, paragraphs in sections.items():
                combined_scores = hybrid_retrieval(query, paragraphs, model)
                relevant_paragraphs = [p for i, p in enumerate(paragraphs) if combined_scores[i] > 0.1]

                if relevant_paragraphs:
                    retrieved_content.extend(relevant_paragraphs)
                    context.append(f"Book: {book}, Chapter: {chapter}, Section: {section}")

    if not retrieved_content:
        return "Sorry, I couldn't find relevant content for your question.", []

    # Limit the content length for the GPT model
    context_text = "\n".join(retrieved_content)
    context_text = context_text[:max_input_length]  # Ensures the input text doesn't exceed max length

    # Generate response with the limited content
    response = llm(context_text)[0]['generated_text']

    return response, context

# Example usage
query = "What is Artificial Intelligence?"
response, context = retrieve_and_generate(query, hierarchical_index, model, llm)

print("Answer:", response)
print("Context:", context)

import gradio as gr

# Gradio interface setup with adjustments for longer responses
def gradio_qa_interface(query):
    response, context = retrieve_and_generate(query, hierarchical_index, model, llm)
    context_text = "\n".join(context)
    return response, context_text

# Define the Gradio UI
gui = gr.Interface(
    fn=gradio_qa_interface,
    inputs=gr.Textbox(label="Enter your query:"),
    outputs=[gr.Textbox(label="Generated Answer:"), gr.Textbox(label="Context Information:")],
    title="Hierarchical QA System",
    description="Ask questions about the textbooks. The system retrieves relevant content and generates detailed answers."
)

# Launch the Gradio UI
gui.launch()

