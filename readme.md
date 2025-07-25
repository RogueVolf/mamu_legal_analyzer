# 🧾 Mamu: Legal Document Analyzer

<p align="center">
  <img src="https://your-logo-or-banner-url.com" width="200" alt="Mamu Logo"/>
</p>

<p align="center">
  <b>Your personal legal assistant to understand any agreement in simple language.</b><br>
  Designed for students, tenants, and everyday people navigating complex legal documents.
</p>

---

## 👤 Target Persona

1. **Students or Young Professionals**
   - Often signing documents like rental agreements, co-living arrangements, NDAs, employment offers without legal help.

2. **General Public with Limited Legal Knowledge**
   - Dealing with complex documents like house deeds, power of attorney, shop leases, etc., without understanding the legal verbatim.

---

## 🎯 Scope

Mamu helps users by:

1. 🛑 Highlighting **risks** involved in the document.  
2. 🧩 Explaining **scenarios** and conditions covered.  
3. 📄 Providing a **layman summary** of the whole document.  
4. 📜 Giving **clause-by-clause explanations** in simple language.

---

## 🆚 Why Mamu is Different from Just Using GPT

| Feature              | Mamu | Raw GPT |
|----------------------|------|---------|
| Context Curation     | ✅   | ❌      |
| Customizability      | ✅   | ❌      |
| BYOK (Bring Your Own Key) | ✅   | ❌      |
| Model Switching      | ✅   | ❌      |

---

## 🧠 How It Works: The Algorithm

### Step 1: 🧭 Document Context Builder
- Identify the **type of document**, **parties involved**, **jurisdiction**, and other key metadata.

### Step 2: 📚 Clause & Topic Extraction
- Segment the document into clauses/topics and **explain each in simple terms**.

### Step 3: ⚠️ Risk Analysis
- Detect **risks**, **unfair terms**, and **tricky clauses** that could affect the user negatively.

### Step 4: 🗒️ Layman Summary
- Provide an **easy-to-understand overview** covering rights, responsibilities, and notable clauses.

---

## 🚀 Getting Started

### 1. Create a Virtual Environment
```bash
python3 -m venv my_env_name
```

### 2. Activate the Environment
- **Windows**
  ```bash
  my_env_name\Scripts\activate
  ```
- **macOS/Linux**
  ```bash
  source my_env_name/bin/activate
  ```

### 3. Install Requirements
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
- Rename `.env.sample` to `.env` and **fill in your API keys and other configs**.

### 5. (Optional) Use Your Own Model
- To switch to OpenRouter:
  - Edit line 13 in `ai_tasks/document_analyzer.py`
  ```python
  from utils.llm_utils import ask_llm
  ```
  ➜ Change to:
  ```python
  from utils.openrouter_llm_utils import ask_llm
  ```

- You can also switch models inside `utils/llm_utils.py`.

### 6. Run the Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```
- Then open `http://localhost:8000` in your browser to start using Mamu.

---

## 💡 Tip
You can use **Cerebras for free** without any configuration change. If using your own model (e.g., OpenRouter), follow the instructions in Step 5 above.

---

Happy Analyzing! 🧠📄
