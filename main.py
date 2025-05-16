import os
import streamlit as st
import asyncio
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

# Import our custom utilities
from utils.document_loader import DocumentLoader
from utils.parallel_executor import ParallelExecutor

# Load environment variables
load_dotenv()

# Initialize processors
document_loader = DocumentLoader()
parallel_executor = ParallelExecutor()

# Configure Streamlit page
st.set_page_config(
    page_title="Financial Research Assistant",
    page_icon="📈",
    layout="wide"
)

# Add custom CSS (optional)
st.markdown("""
    <style>
    body {
        background-color: #f7f9fa;
        font-family: 'Segoe UI', 'Arial', sans-serif;
    }
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        margin-top: 1rem;
        background-color: #1976D2;
        color: white;
        border-radius: 6px;
        font-weight: 600;
        font-size: 1rem;
        border: none;
        transition: background 0.2s;
    }
    .stButton>button:hover {
        background-color: #1565C0;
    }
    .model-response {
        background: linear-gradient(90deg, #e3f0ff 0%, #f7f9fa 100%);
        padding: 1.5rem;
        border-radius: 0.75rem;
        margin: 1.5rem 0;
        border-left: 6px solid #1976D2;
        box-shadow: 0 2px 8px rgba(25, 118, 210, 0.07);
    }
    .model-name {
        font-weight: bold;
        color: #1976D2;
        font-size: 1.2rem;
        margin-bottom: 0.5rem;
        letter-spacing: 0.5px;
    }
    .answer-label {
        color: #333;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }
    .answer-text {
        color: #222;
        font-size: 1.05rem;
        margin-bottom: 0.5rem;
    }
    .source-box {
        background-color: #f1f8e9;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-top: 0.5rem;
        border-left: 5px solid #43A047;
        font-size: 0.98rem;
    }
    .stTextInput>div>div>input {
        border-radius: 6px;
        border: 1.5px solid #1976D2;
        padding: 0.5rem;
        font-size: 1.05rem;
    }
    .stTextInput>div>div>input:focus {
        border: 2px solid #1565C0;
        outline: none;
    }
    </style>
""", unsafe_allow_html=True)

# Title and description
st.title("FinGPT - Financial Research Assistant 📈")
st.markdown("""
    This AI-powered tool analyzes financial documents and provides insights using triple-validation:
    - OpenAI GPT-4o
    - Perplexity Sonar Pro
    - Perplexity Sonar
    
    Each query is processed by all three models to ensure accuracy and reliability.
""")

# Sidebar for input method selection and data input
with st.sidebar:
    st.title("Input Sources")
    input_method = st.radio(
        "Choose input method:",
        ["URLs", "Documents"]
    )
    
    # Initialize lists to store inputs
    urls = []
    uploaded_files = []
    
    if input_method == "URLs":
        st.subheader("Enter URLs")
        for i in range(3):
            url = st.text_input(f"URL {i+1}", key=f"url_{i}")
            if url:
                urls.append(url)
                
        if not urls:
            st.info("Please enter at least one URL")
    else:
        st.subheader("Upload Documents")
        uploaded_files = st.file_uploader(
            "Upload PDFs or Images",
            type=["pdf", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            help="Supported formats: PDF, PNG, JPG"
        )
        
        if not uploaded_files:
            st.info("Please upload at least one document")
    
    process_button = st.button(
        "Process Input",
        disabled=(len(urls) == 0 and len(uploaded_files) == 0)
    )

# Main content area
main_placeholder = st.empty()

# Process input when button is clicked
if process_button:
    try:
        with st.spinner("Processing input..."):
            progress_bar = st.progress(0)
            
            # Process either URLs or documents
            if input_method == "URLs":
                progress_bar.progress(20)
                main_placeholder.info("Processing URLs...")
                documents = document_loader.process_urls(urls)
            else:
                progress_bar.progress(20)
                main_placeholder.info("Processing documents with OCR...")
                documents = document_loader.process_input(uploaded_files)
            
            # Split text into chunks
            progress_bar.progress(40)
            main_placeholder.info("Splitting text into chunks...")
            text_splitter = RecursiveCharacterTextSplitter(
                separators=['\n\n', '\n', '.', ','],
                chunk_size=int(os.getenv('CHUNK_SIZE', 1000))
            )
            texts = []
            for doc in documents:
                texts.extend(text_splitter.split_text(doc))
            
            # Create embeddings and FAISS index
            progress_bar.progress(60)
            main_placeholder.info("Generating embeddings...")
            embeddings = OpenAIEmbeddings()
            vectorstore = FAISS.from_texts(texts, embeddings)
            
            # Save FAISS index
            progress_bar.progress(80)
            main_placeholder.info("Saving index...")
            vectorstore.save_local("faiss_index")
            
            progress_bar.progress(100)
            main_placeholder.success("✅ Processing complete! You can now ask questions.")
            
            # Store the processed state
            st.session_state.processed = True
            st.session_state.texts = texts
            
    except Exception as e:
        st.error(f"An error occurred during processing: {str(e)}")
        st.session_state.processed = False

# --- Always show the query box ---
st.markdown("---")
st.subheader("Ask a Question")
query = st.text_input("What would you like to know?")

if query:
    try:
        with st.spinner("Analyzing with multiple AI models..."):
            # Check if user has processed any input
            if st.session_state.get('processed', False):
                # Use processed context (from FAISS, as before)
                vectorstore = FAISS.load_local("faiss_index", OpenAIEmbeddings(), allow_dangerous_deserialization=True)
                relevant_docs = vectorstore.similarity_search(query, k=3)
                context = "\n\n".join(doc.page_content for doc in relevant_docs)
            else:
                # No context, general query
                context = ""

            # Process query through multiple AI models
            result = asyncio.run(parallel_executor.process_query(query, context))
            
            if not result.get("responses"):
                st.error("No responses received from AI models. Please check your API keys and try again.")
                st.stop()
                
            # Use the new response formatter
            formatted_result = parallel_executor.format_final_response(result)
            
            # Display each model's answer only
            for res in formatted_result["results"]:
                st.markdown(f"""
                    <div class="model-response">
                        <div class="model-name">{res['model']}</div>
                        <div class="answer-label">Answer:</div>
                        <div class="answer-text">{res['answer']}</div>
                    </div>
                """, unsafe_allow_html=True)
            
            # Display sources at the end (if you ever add them)
            if formatted_result["sources"]:
                st.markdown("### Sources")
                for src in formatted_result["sources"]:
                    st.markdown(f"- [{src['title']}]({src['url']})")
            
    except Exception as e:
        st.error(f"An error occurred while processing your question: {str(e)}")
else:
    st.info("👈 Start by adding URLs or uploading documents in the sidebar if you want to ask about specific content. Otherwise, just type your question above for a general answer.")