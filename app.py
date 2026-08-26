"""
Enterprise RAG Assistant — single-file phone-deployable version.

WHY ONE FILE:
The full modular project (separate repo) is better for a GitHub portfolio,
but it needs a terminal to install/run multiple files and a Qdrant server.
This version is self-contained on purpose:
- Qdrant runs in EMBEDDED LOCAL mode (qdrant-client's `path=` option) — no
  Docker, no cloud account, no separate server. It's a real Qdrant engine,
  just running inside this process instead of over the network.
- Demo documents are inlined as strings instead of separate files, since
  uploading a folder of files from a phone browser is painful; pasting one
  file into GitHub's web editor is not.
- No pydantic/FastAPI — plain dicts/dataclasses keep the dependency list to
  exactly 3 packages (streamlit, qdrant-client, sentence-transformers),
  which matters because Streamlit Community Cloud rebuilds this from
  requirements.txt on every deploy.

DEPLOY (from your phone, no laptop needed):
1. github.com -> New repository -> name it e.g. "enterprise-rag-assistant"
2. "Add file" -> "Create new file" -> name it app.py -> paste this whole file -> commit
3. "Add file" -> "Create new file" -> name it requirements.txt -> paste:
     streamlit
     qdrant-client
     sentence-transformers
   -> commit
4. Go to share.streamlit.io -> sign in with GitHub -> "New app" -> pick this
   repo, branch main, file app.py -> in "Advanced settings", add a secret:
     GROQ_API_KEY = "your_free_key_from_console.groq.com"
   -> Deploy.
5. You get a permanent URL. Open it from your phone browser any time.

First load will take ~1-2 minutes (downloading the embedding model and
building the demo index) — that only happens once per app restart.
"""
import hashlib
import os
import re
import sys
import urllib.error
import urllib.request
import json
from dataclasses import dataclass, field
from pathlib import Path

import streamlit as st

# ============================================================================
# CONFIG
# ============================================================================
LLM_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
LLM_MODEL = "llama-3.1-8b-instant"
LLM_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
QDRANT_LOCAL_PATH = "/tmp/qdrant_local_db"
COLLECTION_NAME = "enterprise_docs"
RETRIEVAL_TOP_K = 4
RETRIEVAL_SCORE_THRESHOLD = 0.25
DEMO_PASSWORD = "demo1234"

DEPARTMENTS = ["HR", "Finance", "Marketing", "Engineering", "Executive", "General"]

ROLE_DEPARTMENT_ACCESS: dict[str, list[str]] = {
    "employee": ["General"],
    "hr": ["General", "HR"],
    "finance": ["General", "Finance"],
    "marketing": ["General", "Marketing"],
    "engineering": ["General", "Engineering"],
    "executive": DEPARTMENTS,
}


def get_allowed_departments(role: str) -> list[str]:
    return ROLE_DEPARTMENT_ACCESS[role.lower()]


# ============================================================================
# DEMO USERS  (sha256, demo-only auth — not production security)
# ============================================================================
def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


_PW_HASH = _hash(DEMO_PASSWORD)


@dataclass
class DemoUser:
    email: str
    name: str
    role: str


DEMO_USERS: dict[str, DemoUser] = {
    "employee@example.com": DemoUser("employee@example.com", "Employee Demo", "employee"),
    "hr@example.com": DemoUser("hr@example.com", "HR Demo", "hr"),
    "finance@example.com": DemoUser("finance@example.com", "Finance Demo", "finance"),
    "marketing@example.com": DemoUser("marketing@example.com", "Marketing Demo", "marketing"),
    "engineering@example.com": DemoUser("engineering@example.com", "Engineering Demo", "engineering"),
    "executive@example.com": DemoUser("executive@example.com", "Executive Demo", "executive"),
}


def authenticate(email: str, password: str) -> DemoUser | None:
    user = DEMO_USERS.get(email.strip().lower())
    if user and _hash(password) == _PW_HASH:
        return user
    return None


# ============================================================================
# DEMO DOCUMENTS (synthetic/fictional — inlined so no file upload is needed)
# ============================================================================
DEMO_DOCS: dict[str, list[tuple[str, str]]] = {
    "HR": [
        ("leave_policy", """# HR Leave Policy (Fictional Demo Document)
Employees are entitled to 12 casual leaves per calendar year. Casual leave cannot be carried forward and does not encash upon exit.
Employees receive 10 sick leaves per year. A medical certificate is required for sick leave exceeding 3 consecutive days.
Maternity leave is granted for 26 weeks. Paternity leave is granted for 2 weeks, to be availed within 3 months of the child's birth.
All leave requests must be submitted through the HR portal at least 2 working days in advance, except in documented emergencies."""),
        ("employee_handbook", """# Employee Handbook (Fictional Demo Document)
Standard working hours are 9:30 AM to 6:30 PM, Monday to Friday, with a one-hour lunch break.
Employees may work remotely up to 2 days per week, subject to manager approval.
Grievances should first be raised with the immediate manager. If unresolved within 5 working days, employees may escalate to HR."""),
    ],
    "Finance": [
        ("q1_financial_report", """# Q1 Financial Report (Fictional Demo Document)
Total Q1 revenue was $4.2M, a 9% increase quarter-over-quarter, driven by growth in the enterprise subscription segment.
Total Q1 operating expenditure was $2.8M: $1.1M engineering payroll, $0.7M sales and marketing, $1.0M general and administrative.
Q1 closed with a net operating margin of approximately 33%, ahead of the 28% target."""),
        ("company_budget", """# Company Budget Overview (Fictional Demo Document)
The FY2026 annual budget is allocated: Engineering 40%, Sales & Marketing 25%, Operations 15%, HR 10%, Executive/Admin 10%.
Discretionary spend above $10,000 requires Finance director approval. Spend above $50,000 requires executive sign-off."""),
    ],
    "Marketing": [
        ("q1_campaign_report", """# Q1 Campaign Report (Fictional Demo Document)
The Q1 "Spring Launch" campaign generated 12,400 marketing qualified leads, a 15% increase over Q4, at a cost-per-lead of $34.
Paid social contributed 45% of leads, organic search 30%, and email nurture campaigns 25%."""),
        ("marketing_budget", """# Marketing Budget (Fictional Demo Document)
Total Q1 marketing spend was $420,000: paid social $190,000, content production $120,000, events $110,000."""),
    ],
    "Engineering": [
        ("engineering_handbook", """# Engineering Handbook (Fictional Demo Document)
All pull requests require at least one approval before merging to main. Critical infrastructure changes require two approvals.
Engineers participate in a weekly on-call rotation, with escalation paths documented in the internal runbook."""),
    ],
    "Executive": [
        ("company_strategy", """# Company Strategy Overview (Fictional Demo Document)
FY2026 strategic priorities: expand enterprise segment revenue by 25%, launch two new product lines by Q3, improve gross margin by 4 points.
Executive team is evaluating a potential acquisition in the analytics space; details are restricted to Executive-level access."""),
    ],
    "General": [
        ("company_overview", """# Company Overview (Fictional Demo Document)
Acme Corp is a fictional mid-size SaaS company with approximately 850 employees across engineering, sales, marketing, HR, and finance.
Acme Corp has offices in Bengaluru, Austin, and Berlin, with a remote-friendly policy across all locations."""),
    ],
}


# ============================================================================
# CHUNKING (sentence-aware, configurable overlap — see inline rationale)
# ============================================================================
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def chunk_text(text: str, chunk_size: int = 400, chunk_overlap: int = 60) -> list[str]:
    paragraphs = [p for p in text.split("\n") if p.strip()]
    sentences: list[str] = []
    for para in paragraphs:
        sentences.extend(s for s in _SENTENCE_SPLIT_RE.split(para) if s.strip())
    if not sentences:
        return []

    chunks, current, current_len = [], [], 0
    for sentence in sentences:
        sentence_len = len(sentence) + 1
        if current and current_len + sentence_len > chunk_size:
            chunks.append(" ".join(current))
            overlap, overlap_len = [], 0
            for s in reversed(current):
                if overlap_len + len(s) + 1 > chunk_overlap:
                    break
                overlap.insert(0, s)
                overlap_len += len(s) + 1
            current, current_len = overlap, overlap_len
        current.append(sentence)
        current_len += sentence_len
    if current:
        chunks.append(" ".join(current))
    return chunks


@dataclass
class Chunk:
    text: str
    document_name: str
    department: str
    chunk_id: str


def build_corpus() -> list[Chunk]:
    corpus: list[Chunk] = []
    for department, docs in DEMO_DOCS.items():
        for doc_name, text in docs:
            for i, piece in enumerate(chunk_text(text)):
                corpus.append(Chunk(text=piece, document_name=doc_name, department=department, chunk_id=f"{doc_name}-{i}"))
    return corpus


# ============================================================================
# GUARDRAILS
# ============================================================================
_INJECTION_PATTERNS = [
    r"ignore (all |any )?(the )?(previous|above|prior) instructions",
    r"disregard (all |any )?(the )?(previous|above|prior) instructions",
    r"reveal (your |the )?system prompt",
    r"show (me )?(your |the )?system prompt",
    r"bypass (your |the )?(restrictions|rules|permissions|access control)",
    r"act as (if )?(you (are|were) )?(an? )?(admin|root|developer|unrestricted)",
    r"(you are now|enter) (in )?(dan|jailbreak|developer mode)",
    r"reveal (confidential|restricted|unauthorized) information",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def detect_prompt_injection(text: str) -> bool:
    return bool(_INJECTION_RE.search(text))


_PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "pan_like": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    "aadhaar_like": re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b"),
    "phone": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3,5}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b"),
}


def detect_pii(text: str) -> list[str]:
    return [label for label, pat in _PII_PATTERNS.items() if pat.search(text)]


def redact_pii(text: str) -> str:
    redacted = text
    for label, pat in _PII_PATTERNS.items():
        redacted = pat.sub(f"[REDACTED_{label.upper()}]", redacted)
    return redacted


# ============================================================================
# EMBEDDINGS + VECTOR STORE (real sentence-transformers + real embedded Qdrant)
# ============================================================================
@st.cache_resource(show_spinner="Loading embedding model (first run only)...")
def get_embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL)


@st.cache_resource(show_spinner="Building document index (first run only)...")
def get_vector_store():
    """
    Runs Qdrant in EMBEDDED mode: `QdrantClient(path=...)` starts a real
    Qdrant engine backed by local files, no server/Docker/cloud account
    needed. RBAC filtering below is a real Qdrant metadata filter applied
    server-side (inside this same process) — not a post-hoc Python filter —
    so the same security property as the full networked version holds:
    a role's disallowed chunks are never returned, let alone sent to the LLM.
    """
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qm

    client = QdrantClient(path=QDRANT_LOCAL_PATH)
    embedder = get_embedder()

    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        corpus = build_corpus()
        vectors = embedder.encode([c.text for c in corpus], show_progress_bar=False).tolist()
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qm.VectorParams(size=len(vectors[0]), distance=qm.Distance.COSINE),
        )
        points = [
            qm.PointStruct(
                id=i,
                vector=vec,
                payload={"text": c.text, "document_name": c.document_name, "department": c.department},
            )
            for i, (c, vec) in enumerate(zip(corpus, vectors))
        ]
        client.upsert(collection_name=COLLECTION_NAME, points=points)

    return client


def search(query: str, allowed_departments: list[str]) -> list[dict]:
    from qdrant_client.http import models as qm

    client = get_vector_store()
    embedder = get_embedder()
    query_vector = embedder.encode([query], show_progress_bar=False)[0].tolist()

    # RBAC filter applied inside the Qdrant query itself — see docstring above.
    query_filter = qm.Filter(
        must=[qm.FieldCondition(key="department", match=qm.MatchAny(any=allowed_departments))]
    )
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        query_filter=query_filter,
        limit=RETRIEVAL_TOP_K,
        score_threshold=RETRIEVAL_SCORE_THRESHOLD,
    )
    return [{"text": r.payload["text"], "document_name": r.payload["document_name"], "score": r.score} for r in results]


# ============================================================================
# RAG ANSWER GENERATION
# ============================================================================
SYSTEM_PROMPT = (
    "You are an internal enterprise knowledge assistant. Answer ONLY using the "
    "provided context. If the answer is not contained in the context, say you "
    "don't have that information in the available documents — do not guess. "
    "Be concise and factual."
)

NO_CONTEXT_MESSAGE = (
    "I don't have information about that in the documents I'm authorized to search. "
    "I can help with questions related to the company's internal knowledge base."
)


def call_llm(system_prompt: str, user_prompt: str) -> str:
    if not LLM_API_KEY:
        return "⚠️ No LLM_API_KEY / GROQ_API_KEY configured. Add it as a secret in your deployment settings."
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "temperature": 0.1,
        "max_tokens": 500,
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LLM_API_KEY}"}
    req = urllib.request.Request(LLM_ENDPOINT, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"]
    except urllib.error.URLError as e:
        return f"⚠️ LLM request failed: {e}"
    except (KeyError, IndexError):
        return "⚠️ Unexpected response from LLM provider."


def generate_answer(question: str, chunks: list[dict]) -> dict:
    if not chunks:
        return {"answer": NO_CONTEXT_MESSAGE, "sources": []}
    context = "\n\n".join(f"[{c['document_name']}]\n{c['text']}" for c in chunks)
    user_prompt = f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer using only the context above."
    answer = call_llm(SYSTEM_PROMPT, user_prompt)
    seen, sources = set(), []
    for c in chunks:
        if c["document_name"] not in seen:
            seen.add(c["document_name"])
            sources.append(c["document_name"])
    return {"answer": answer, "sources": sources}


# ============================================================================
# STREAMLIT UI
# ============================================================================
st.set_page_config(page_title="Enterprise RAG Assistant", page_icon="🏢", layout="wide")

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; }
    .chat-bubble-user { background:#2563eb; color:white; padding:10px 16px; border-radius:14px 14px 2px 14px; margin:6px 0; max-width:80%; margin-left:auto; }
    .chat-bubble-ai { background:white; border:1px solid #e5e7eb; padding:10px 16px; border-radius:14px 14px 14px 2px; margin:6px 0; max-width:80%; }
    .chat-bubble-blocked { background:#fef2f2; border:1px solid #fecaca; color:#991b1b; padding:10px 16px; border-radius:14px; margin:6px 0; }
    .source-tag { display:inline-block; background:#eef2ff; color:#3730a3; font-size:0.78rem; padding:2px 8px; border-radius:8px; margin:2px 4px 0 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []


def login_screen():
    st.markdown("## 🏢 Enterprise RAG Assistant")
    st.caption("Internal knowledge assistant — demo login")
    with st.form("login"):
        email = st.text_input("Email", placeholder="hr@example.com")
        password = st.text_input("Password", type="password", placeholder="demo1234")
        submitted = st.form_submit_button("Log in")
    if submitted:
        user = authenticate(email, password)
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Invalid credentials.")
    with st.expander("Demo accounts"):
        st.code(
            "employee@example.com\nhr@example.com\nfinance@example.com\n"
            "marketing@example.com\nengineering@example.com\nexecutive@example.com\n\n"
            "password (all accounts): demo1234"
        )


def sidebar(user):
    with st.sidebar:
        st.markdown(f"### 👤 {user.name}")
        st.markdown(f"**Role:** `{user.role}`")
        st.markdown("**Accessible departments:**")
        for d in get_allowed_departments(user.role):
            st.markdown(f"- {d}")
        st.divider()
        if st.button("🗑️ Clear chat"):
            st.session_state.messages = []
            st.rerun()
        if st.button("🚪 Logout"):
            st.session_state.user = None
            st.session_state.messages = []
            st.rerun()
        st.divider()
        st.caption("⚠️ Demo system — guardrails are basic pattern-based checks, not complete security.")


def handle_question(question: str, user) -> dict:
    if detect_prompt_injection(question):
        return {"blocked": True, "message": "⚠️ This request was blocked: it appears to attempt to bypass system restrictions."}
    safe_question = redact_pii(question) if detect_pii(question) else question
    allowed = get_allowed_departments(user.role)
    chunks = search(safe_question, allowed)
    result = generate_answer(safe_question, chunks)
    return {"blocked": False, **result}


def chat_screen(user):
    sidebar(user)
    st.markdown("## 💬 Ask the Knowledge Assistant")
    st.caption(f"Answering only from documents you're authorized to access as **{user.role}**.")

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-bubble-user">{msg["content"]}</div>', unsafe_allow_html=True)
        elif msg["role"] == "blocked":
            st.markdown(f'<div class="chat-bubble-blocked">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-bubble-ai">{msg["content"]}</div>', unsafe_allow_html=True)
            if msg.get("sources"):
                tags = "".join(f'<span class="source-tag">📄 {s}</span>' for s in msg["sources"])
                st.markdown(tags, unsafe_allow_html=True)

    question = st.chat_input("Ask a question about company policies, reports, or documents...")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.spinner("Thinking..."):
            result = handle_question(question, user)
        if result["blocked"]:
            st.session_state.messages.append({"role": "blocked", "content": result["message"]})
        else:
            st.session_state.messages.append({"role": "assistant", "content": result["answer"], "sources": result["sources"]})
        st.rerun()


def main():
    if st.session_state.user is None:
        login_screen()
    else:
        chat_screen(st.session_state.user)


if __name__ == "__main__":
    main()
