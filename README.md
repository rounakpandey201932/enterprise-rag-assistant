🏢 Enterprise RAG Assistant

«A secure, role-aware Retrieval-Augmented Generation (RAG) assistant for querying enterprise knowledge bases.»

""Python" (https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)" (https://www.python.org/)
""Streamlit" (https://img.shields.io/badge/Streamlit-App-red?logo=streamlit)" (https://streamlit.io/)
""Qdrant" (https://img.shields.io/badge/Qdrant-Vector%20Database-purple)" (https://qdrant.tech/)
""Sentence Transformers" (https://img.shields.io/badge/Sentence--Transformers-Embeddings-orange)" (https://www.sbert.net/)
""Groq" (https://img.shields.io/badge/Groq-LLM-black)" (https://groq.com/)

An end-to-end Enterprise RAG Assistant built with Streamlit, Qdrant, Sentence Transformers, and Groq.

The application allows employees to ask questions about internal company information while ensuring that retrieved information is restricted according to the user's role and department permissions.

---

✨ Features

🔎 Retrieval-Augmented Generation

The application follows a complete RAG pipeline:

User Question
      ↓
Prompt Guardrails
      ↓
PII Detection / Redaction
      ↓
Query Embedding
      ↓
Qdrant Semantic Search
      ↓
Role-Based Filtering
      ↓
Relevant Document Chunks
      ↓
Groq LLM
      ↓
Grounded Answer + Sources

The LLM is instructed to answer only from retrieved context and avoid inventing information that isn't present in the authorized documents.

---

🔐 Role-Based Access Control

Different users can access different departments.

Role| Accessible Departments
👤 Employee| General
🧑‍💼 HR| General + HR
💰 Finance| General + Finance
📣 Marketing| General + Marketing
👨‍💻 Engineering| General + Engineering
👑 Executive| All Departments

Access control is applied inside the Qdrant search query, meaning unauthorized document chunks are filtered before they are returned to the application.

---

🛡️ Security Guardrails

The application includes basic security mechanisms designed for an enterprise RAG demonstration.

Prompt Injection Detection

Blocks common attempts such as:

- Ignoring previous instructions
- Revealing system prompts
- Bypassing permissions
- Entering jailbreak/developer modes
- Requesting confidential or restricted information

PII Detection & Redaction

The application detects and redacts patterns resembling:

- Email addresses
- Indian PAN numbers
- Aadhaar-like numbers
- Phone numbers

Example:

john@example.com
        ↓
[REDACTED_EMAIL]

---

🧠 Semantic Search

Instead of relying on simple keyword matching, the application converts text into vector embeddings using:

"sentence-transformers/all-MiniLM-L6-v2"

This allows the system to retrieve documents based on semantic meaning, even when the exact words in the question aren't present in the document.

---

⚡ Qdrant Vector Database

The project uses Qdrant as its vector database.

For this phone-deployable version, Qdrant runs in embedded local mode:

QdrantClient(path="/tmp/qdrant_local_db")

This means:

- No Docker required
- No separate Qdrant server
- No external vector database account
- Real Qdrant semantic search
- Metadata filtering for RBAC

---

🤖 Groq LLM

The retrieved context is sent to a Groq-hosted LLM.

The application uses:

llama-3.1-8b-instant

The model receives:

System Instructions
        +
Retrieved Context
        +
User Question
        ↓
     Answer

The system prompt explicitly instructs the model to avoid guessing and answer only from the supplied context.

---

🏗️ Architecture

                    ┌─────────────────────┐
                    │      Streamlit      │
                    │     Web Interface   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Demo Authentication│
                    │      + RBAC          │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Security Guardrails │
                    │                     │
                    │ • Prompt Injection │
                    │ • PII Detection    │
                    │ • PII Redaction    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Sentence Transformer│
                    │    Embeddings       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       Qdrant        │
                    │   Vector Database   │
                    │                     │
                    │ Semantic Search     │
                    │ + RBAC Filtering    │
                    └──────────┬──────────┘
                               │
                         Top-K Chunks
                               │
                               ▼
                    ┌─────────────────────┐
                    │      Groq LLM       │
                    │  Grounded Response  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Answer + Sources    │
                    └─────────────────────┘

---

📚 Demo Knowledge Base

The current deployment contains synthetic/fictional enterprise documents covering:

👥 HR

- Leave Policy
- Employee Handbook

💰 Finance

- Q1 Financial Report
- Company Budget

📣 Marketing

- Q1 Campaign Report
- Marketing Budget

👨‍💻 Engineering

- Engineering Handbook

👑 Executive

- Company Strategy

🌐 General

- Company Overview

«Note: All included company information is fictional and created purely for demonstration purposes.»

---

🧩 Document Processing

Documents are processed using sentence-aware chunking.

The system:

1. Splits documents into paragraphs.
2. Splits paragraphs into sentences.
3. Groups sentences into manageable chunks.
4. Uses a configurable overlap between chunks.
5. Generates embeddings for each chunk.
6. Stores vectors and metadata in Qdrant.

Each vector contains metadata such as:

text
document_name
department

This metadata is then used during retrieval and access-control filtering.

---

🔍 Retrieval Process

When a user asks:

«"How many casual leaves do employees receive?"»

The system doesn't simply search for the exact words.

Instead:

Question
   ↓
Embedding
   ↓
Vector Similarity Search
   ↓
Qdrant
   ↓
Relevant HR chunks
   ↓
RBAC verification
   ↓
Groq
   ↓
Answer

For an authorized HR user, the relevant HR document can be retrieved.

For a user without HR access, the HR document is filtered out during retrieval.

---

🔑 Demo Credentials

All demo accounts use the same password:

demo1234

Email| Role
"employee@example.com"| Employee
"hr@example.com"| HR
"finance@example.com"| Finance
"marketing@example.com"| Marketing
"engineering@example.com"| Engineering
"executive@example.com"| Executive

Example

Log in as:

hr@example.com

Then ask:

How many casual leaves are employees entitled to?

The HR user can retrieve HR information.

Try the same question using:

employee@example.com

The HR documents will not be available to that role.

---

🚀 Running Locally

1. Clone the repository

git clone https://github.com/YOUR_USERNAME/enterprise-rag-assistant.git

cd enterprise-rag-assistant

2. Install dependencies

pip install -r requirements.txt

3. Configure the Groq API key

Create a ".streamlit/secrets.toml" file:

GROQ_API_KEY = "your_groq_api_key"

Never commit your API key to GitHub.

4. Start the application

streamlit run app.py

---

☁️ Deploy on Streamlit Community Cloud

This project is designed to be deployable directly from GitHub.

1. Push "app.py" and "requirements.txt" to GitHub.
2. Open Streamlit Community Cloud.
3. Connect your GitHub account.
4. Select the repository.
5. Select the "main" branch.
6. Set the main file to:

app.py

7. Add the following secret:

GROQ_API_KEY = "your_groq_api_key"

8. Deploy.

The application can then be accessed through its Streamlit URL.

---

📦 Dependencies

The project intentionally keeps dependencies minimal:

streamlit
qdrant-client
sentence-transformers

The embedding model is downloaded automatically on first startup.

---

⚙️ Configuration

Important configuration values are defined near the top of "app.py":

LLM_MODEL = "llama-3.1-8b-instant"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

RETRIEVAL_TOP_K = 4

RETRIEVAL_SCORE_THRESHOLD = 0.25

These can be adjusted depending on the desired retrieval behavior.

---

🎯 Why This Project?

Traditional enterprise chatbots can have problems such as:

- Hallucinated answers
- Unauthorized information retrieval
- Poor semantic search
- Prompt injection
- Sensitive information exposure

This project demonstrates how a RAG architecture can combine:

LLMs + Vector Search + RBAC + Security Guardrails

to create a more controlled enterprise knowledge assistant.

---

🔮 Future Improvements

The current version is intentionally designed as a lightweight, single-file deployment.

Possible future improvements include:

- [ ] PDF document upload
- [ ] PPT/PPTX document upload
- [ ] DOCX document upload
- [ ] User-uploaded knowledge bases
- [ ] Persistent cloud Qdrant
- [ ] Production authentication
- [ ] OAuth / SSO
- [ ] PostgreSQL user management
- [ ] Advanced prompt-injection detection
- [ ] Hybrid keyword + vector search
- [ ] Reranking models
- [ ] Conversation memory
- [ ] Document versioning
- [ ] Audit logs
- [ ] Admin dashboard
- [ ] Production-grade secrets management

---

⚠️ Disclaimer

This project is an educational and portfolio demonstration.

The authentication system uses demo credentials and SHA-256 password hashing for simplicity. The security guardrails are pattern-based and should not be considered sufficient for production enterprise security.

The company, employees, financial figures, policies, and other documents included in the demo are fictional.

---

👨‍💻 Tech Stack

Technology| Purpose
🐍 Python| Core application
🎈 Streamlit| Web application
🔎 Qdrant| Vector database & semantic search
🧠 Sentence Transformers| Text embeddings
🤖 Groq| LLM inference
🔐 SHA-256| Demo password hashing
🛡️ Regex| Security & PII detection

---

⭐ Project Highlights

This project demonstrates practical knowledge of:

"RAG" · "LLMs" · "Vector Databases" · "Embeddings" · "Semantic Search" · "Qdrant" · "RBAC" · "Prompt Injection Defense" · "PII Redaction" · "Streamlit" · "Groq" · "Python"

---

Made with Python + Streamlit + Qdrant + Groq ❤️
