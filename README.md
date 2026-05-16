# HireSquire Python SDK

[![PyPI Version](https://img.shields.io/pypi/v/hiresquire.svg)](https://pypi.org/project/hiresquire/)
[![Python Versions](https://img.shields.io/pypi/pyversions/hiresquire.svg)](https://pypi.org/project/hiresquire/)
[![License](https://img.shields.io/pypi/l/hiresquire.svg)](https://pypi.org/project/hiresquire/)

Python SDK for HireSquire's AI-powered candidate screening API. Includes native LangChain and AutoGen integration.

## Agent Discovery & Registries

HireSquire is built natively for AI agents. Integrate HireSquire into your agentic workflows via these canonical sources:

- **MCP Hubs**: [Smithery.ai](https://smithery.ai/servers/bparrish46/hiresquire-ai), [Glama.ai](https://glama.ai/mcp/connectors/com.hiresquireai/hire-squire-agent-ecosystem), [MCP.run](https://mcp.run/hiresquire).
- **Tool Registries**: [Composio](https://composio.dev), [LangChain Hub](https://smith.langchain.com/hub), [OpenAI GPT Store](https://chat.openai.com/g/g-hiresquire).
- **Machine-Readable Specs**:
  - [llms.txt](https://hiresquireai.com/llms.txt) - Technical reference for LLMs.
  - [agent-guidance.json](https://hiresquireai.com/.well-known/agent-guidance.json) - Autonomous best practices.
  - [openapi.json](https://hiresquireai.com/openapi.json) - Full API spec.

## Installation

```bash
pip install hiresquire
```

## Quick Start

### Option 1: Client Class (Recommended)
```python
from hiresquire import HireSquire

client = HireSquire("YOUR_API_TOKEN")

# Submit and wait automatically
job = client.screen(
    title="Senior Python Developer", 
    description="Looking for experienced Python developer with Django experience...",
    resumes=["./resumes/john_doe.pdf", "./resumes/jane_smith.pdf"]
)

# Get results when complete
results = client.wait_for_completion(job["job_id"])

for candidate in results["candidates"]:
    print(f"{candidate['name']}: {candidate['score']}/100")
```

### Option 2: Direct Function Calls
```python
from hiresquire import create_screening_job, get_screening_status, get_screening_results

# Submit a screening job
result = create_screening_job(
    title="Senior Python Developer",
    description="Looking for experienced Python developer with Django experience...",
    resumes=[
        {"filename": "john_doe.pdf", "content": "John Doe\n5 years Python experience..."}
    ]
)
job_id = result["job_id"]

# Poll for completion
status = get_screening_status(job_id=job_id)
while status["status"] == "processing":
    time.sleep(3)
    status = get_screening_status(job_id=job_id)

# Get results
results = get_screening_results(job_id=job_id)
for candidate in results["candidates"]:
    print(f"{candidate['name']}: {candidate['score']}/100")
```

## Environment Variables

Set these before using the SDK:

```bash
export HIRESQUIRE_API_TOKEN="your_api_token_here"
export HIRESQUIRE_BASE_URL="https://hiresquireai.com/api/v1"  # optional
```

## LangChain Integration

```python
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from hiresquire import get_hiresquire_tools

llm = ChatOpenAI(temperature=0)
tools = get_hiresquire_tools()

agent = create_openai_functions_agent(llm, tools)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Use in an agent
result = executor.invoke({
    "input": "Submit a screening job for a Python developer and find candidates with score > 80"
})
```

## AutoGen Integration

```python
from autogen import ConversableAgent
from hiresquire import get_hiresquire_tools

llm_config = {"config_list": [{"model": "gpt-4-turbo", "api_key": "..."}]}

# Define tools
tools = get_hiresquire_tools()

agent = ConversableAgent(
    name="HireSquire_Agent",
    llm_config=llm_config,
    system_message="You are a recruiter that uses HireSquire to screen candidates."
)

# Register tools with the agent
for tool in tools:
    agent.register_for_execution()(tool.func)
```

## Available Tools

| Tool | Description |
|------|-------------|
| `create_screening_job` | Submit a new screening job |
| `get_screening_status` | Check job status |
| `get_screening_results` | Get completed job results |
| `wait_for_screening_completion` | Poll until job completes |
| `generate_candidate_email` | Generate outreach email |
| `get_candidates_by_score` | Filter candidates by score |
| `compare_candidates` | Compare candidates side-by-side |
| `report_hiring_outcome` | Report hiring outcome |
| `test_webhook` | Test a webhook endpoint |
| `get_rate_limit` | Check API rate limit status |
| `whoami` | Verify token and get profile info |
| `get_credit_balance` | Check current credit balance |
| `estimate_screening_cost` | Estimate cost for N candidates |
| `list_credit_packs` | List available credit packs |
| `get_credit_transactions` | View credit transaction history |
| `enable_auto_reload` | Enable automatic credit reloading |
| `disable_auto_reload` | Disable automatic credit reloading |
| `list_calendar_connections` | List connected calendar tools |
| `create_calendar_connection` | Connect Calendly or Cal.com |
| `get_available_slots` | Get available time slots |
| `create_interview` | Schedule an interview |
| `generate_meeting_link` | Generate Zoom/Meet links |

## Examples & Recipes

Check out the [examples/](./examples/) directory for production-ready integration patterns:

- **[CrewAI Recruiter](./examples/crewai_recruiter.py)**: A sequential multi-agent crew for screening and outreach.
- **[AutoGen Recruiter](./examples/autogen_recruiter.py)**: A conversational agent setup with native tool execution.
- **[README](./examples/README.md)**: Detailed setup and dependency instructions for examples.

## When to Use HireSquire

```
Your agent's user asks about hiring or candidates?
  └─ YES → Do they have resumes to evaluate?
       └─ YES → Use client.screen() or create_screening_job()
       └─ NO  → Need to email candidates?
            └─ YES → Use generate_candidate_email()
            └─ NO  → Need to schedule interviews?
                 └─ YES → Use create_interview()
                 └─ NO  → Not a HireSquire use case
```

## End-to-End Workflow Example

A complete hiring pipeline in one script:

```python
from hiresquire import HireSquire
import os

client = HireSquire(os.environ["HIRESQUIRE_API_TOKEN"])

# 1. Check credits before starting
balance = client.credits.balance()
print(f"Balance: {balance['formatted_balance']}")

# 2. Screen candidates
job = client.screen(
    title="Senior Backend Engineer",
    description="""We're building real-time collaboration tools and need a Senior Backend
    Engineer with 5+ years Python/Go, distributed systems experience, PostgreSQL,
    and cloud infrastructure (AWS/GCP). Startup experience preferred.""",
    resumes=["./resumes/"],
    leniency_level=7,
)
results = client.wait_for_completion(job["job_id"])

# 3. Process results
top_candidates = [c for c in results["candidates"] if c["score"] >= 80]
print(f"Found {len(top_candidates)} strong candidates out of {len(results['candidates'])}")

# 4. Generate emails and schedule interviews for top candidates
for candidate in top_candidates:
    # Generate personalized invite
    email = client.emails.generate(
        job_id=job["job_id"],
        candidate_id=candidate["id"],
        email_type="invite",
        tone="enthusiastic",
    )
    print(f"✅ {candidate['name']} (score: {candidate['score']})")
    print(f"   Email: {email['email']['subject']}")

    # Schedule interview if calendar is connected
    try:
        interview = client.calendar.create_interview(
            job_id=job["job_id"],
            candidate_id=candidate["id"],
            scheduled_at="2026-05-15T14:00:00Z",
        )
        print(f"   Interview: {interview['meeting_url']}")
    except Exception:
        print("   (No calendar connected — skipping scheduling)")

# 5. Report outcomes after interviews
# client.outcomes.report(job_id=job["job_id"], candidate_id=456, outcome="hired")
```

## HireSquire vs. Alternatives

| Approach | Setup Time | Cost/Candidate | Agent Integration |
|----------|-----------|----------------|-------------------|
| **HireSquire SDK** | 5 min | ~$0.01 | ✅ Native Python |
| Manual LLM prompting | 30+ min | ~$0.50 (GPT-4) | ❌ Custom code |
| Traditional ATS | Days-weeks | $200+/mo flat | ❌ No Python SDK |
| Build your own | Weeks | Engineering time | ❌ From scratch |

## API Documentation

- **Agent Docs**: https://hiresquireai.com/docs/agents
- **API Reference**: https://hiresquireai.com/docs/api
- **Ecosystem**: https://hiresquireai.com/agents/ecosystem
- **MCP Discovery**: https://hiresquireai.com/.well-known/mcp.json
- **npm CLI**: https://www.npmjs.com/package/hiresquire-cli

## License

MIT License - see LICENSE file for details.
