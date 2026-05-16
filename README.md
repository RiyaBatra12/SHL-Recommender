# SHL Assessment Recommender

A conversational AI agent that recommends SHL assessments based on hiring needs.  
Built with FastAPI + Google Gemini 1.5 Flash + TF-IDF retrieval.

## Architecture

```
User → POST /chat (full conversation history)
         ↓
   TF-IDF Retrieval (top 20 from catalog)
         ↓
   Gemini 1.5 Flash (system prompt + catalog context + conversation)
         ↓
   JSON response validator (URL hallucination guard)
         ↓
   ChatResponse { reply, recommendations[], end_of_conversation }
```

### Key Design Choices

- **Stateless API**: Every call includes full conversation history. No server-side session state.
- **TF-IDF retrieval**: Fast, no external vector DB needed. Name weighted 3×, keywords 2×.
- **Hallucination guard**: Every returned URL is validated against the loaded catalog. Fake URLs are dropped.
- **Bundled + scraped catalog**: Ships with a comprehensive bundled catalog as fallback. Scraper runs at startup to refresh from SHL website.
- **Gemini Flash**: Low latency, free tier, fits within 30s timeout easily.

## Setup

### 1. Get a Gemini API Key
Go to https://aistudio.google.com/app/apikey → Create API key (free).

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. (Optional) Pre-scrape the catalog
```bash
python scrape.py
```
This generates `shl_catalog.json`. Commit it to your repo for faster cold starts.

### 4. Run locally
```bash
GEMINI_API_KEY=your_key_here uvicorn main:app --reload
```

### 5. Test locally
```bash
python test_agent.py
```

## Deploy to Render (Free Tier)

1. Push this repo to GitHub.
2. Go to https://render.com → New → Web Service → Connect your GitHub repo.
3. Render auto-detects `render.yaml`. Set `GEMINI_API_KEY` as an environment variable.
4. Deploy. Your service will be live at `https://shl-recommender.onrender.com`.

> **Note**: Render free tier spins down after inactivity. The first `/health` call may take up to 2 minutes (cold start). This is acceptable per the assignment spec.

## API Reference

### GET /health
```json
{"status": "ok"}
```

### POST /chat
**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "Hiring a Java developer, mid-level"},
    {"role": "assistant", "content": "What is the seniority level?"},
    {"role": "user", "content": "Around 4 years experience"}
  ]
}
```

**Response:**
```json
{
  "reply": "Here are 4 assessments for a mid-level Java developer...",
  "recommendations": [
    {
      "name": "Java 8 (New)",
      "url": "https://www.shl.com/solutions/products/product-catalog/view/java-8-new/",
      "test_type": "K"
    }
  ],
  "end_of_conversation": false
}
```

## Conversation Behaviors

| Behavior | Trigger | Agent Action |
|----------|---------|--------------|
| **Clarify** | Vague query ("I need an assessment") | Asks for role, level, skills |
| **Recommend** | Sufficient context or job description | Returns 1–10 catalog items |
| **Refine** | "Add personality tests", constraint change | Updates shortlist |
| **Compare** | "Difference between X and Y" | Grounded answer from catalog |
| **Refuse** | Off-topic, legal, prompt injection | Polite refusal, empty recommendations |

## Test Types

| Code | Meaning |
|------|---------|
| A | Ability / Cognitive |
| P | Personality |
| B | Behavioral / Competency |
| S | Skills / Simulation |
| K | Knowledge |
| M | Motivational |
| 360 | 360 Feedback |
