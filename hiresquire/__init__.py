"""
HireSquire - AI-Powered Candidate Screening SDK
================================================

This package provides tools and SDK for integrating HireSquire's
candidate screening API into AI agents, workflows, and applications.

Optional LangChain integration available as extra dependency.

Installation:
    pip install hiresquire

Quick Start:
    from hiresquire import create_screening_job, get_screening_status
    
    # Submit a job
    result = create_screening_job(
        title="Senior Developer",
        description="Looking for Python developer...",
        resumes=[{"filename": "john.pdf", "content": "John Doe\n5 years Python..."}]
    )
    
    # Check status
    status = get_screening_status(job_id=result["job_id"])

Environment Variables:
    HIRESQUIRE_API_TOKEN: Your API token from hiresquire dashboard
    HIRESQUIRE_BASE_URL: API base URL (default: https://hiresquireai.com/api/v1)
"""

from .tools import (
    create_screening_job,
    get_screening_status,
    get_screening_results,
    wait_for_screening_completion,
    generate_candidate_email,
    get_candidates_by_score,
    get_hiresquire_tools,
    read_resume_from_file,
    compare_candidates,
    get_credit_balance,
    estimate_screening_cost,
    list_credit_packs,
    list_calendar_connections,
    create_calendar_connection,
    get_available_slots,
    create_interview,
    generate_meeting_link,
    whoami,
    list_agent_keys,
    create_agent_key,
    get_agent_key,
    update_agent_key,
    revoke_agent_key,
    regenerate_agent_key,
    get_agent_key_usage,
    HireSquireError,
)
import os
from typing import Optional, List, Dict, Any, Union

__version__ = "1.2.2"

def _unwrap(func_or_tool):
    """Unwrap LangChain tool to underlying function, handling mocks safely."""
    if type(func_or_tool).__name__ in ('MagicMock', 'AsyncMock', 'Mock'):
        return func_or_tool
        
    if hasattr(func_or_tool, "func"):
        return func_or_tool.func
        
    return func_or_tool

class JobsNamespace:
    def __init__(self, client):
        self.client = client

    def create(self, title: str, description: str, resumes: List[Union[str, Dict[str, str]]], **kwargs) -> Dict[str, Any]:
        """Submit a screening job. Resumes can be file paths or list of content dicts."""
        resume_objects = []
        
        for resume in resumes:
            if isinstance(resume, str) and os.path.exists(resume):
                resume_objects.append(read_resume_from_file(resume))
            elif isinstance(resume, dict) and "filename" in resume and "content" in resume:
                resume_objects.append(resume)
            else:
                raise ValueError(f"Invalid resume: {resume}. Must be file path or dict with filename and content.")
        
        f = _unwrap(create_screening_job)
        return f(
            title, description, resume_objects, 
            api_token=self.client.api_token, 
            base_url=self.client.base_url, 
            **kwargs
        )

    def get_status(self, job_id: int) -> Dict[str, Any]:
        """Get status of a job."""
        f = _unwrap(get_screening_status)
        return f(job_id, api_token=self.client.api_token, base_url=self.client.base_url)

    def get_results(self, job_id: int, **kwargs) -> Dict[str, Any]:
        """Get results for a completed job."""
        f = _unwrap(get_screening_results)
        return f(job_id, api_token=self.client.api_token, base_url=self.client.base_url, **kwargs)

    def wait(self, job_id: int, **kwargs) -> Dict[str, Any]:
        """Wait for screening job to complete and return results."""
        f = _unwrap(wait_for_screening_completion)
        return f(job_id, api_token=self.client.api_token, base_url=self.client.base_url, **kwargs)


class CandidatesNamespace:
    def __init__(self, client):
        self.client = client

    def generate_email(self, job_id: int, candidate_id: int, **kwargs) -> Dict[str, Any]:
        """Generate email for a candidate."""
        f = _unwrap(generate_candidate_email)
        return f(job_id, candidate_id, api_token=self.client.api_token, base_url=self.client.base_url, **kwargs)

    def compare(self, candidates: List[Dict[str, Any]], candidate_ids: List[int]) -> Dict[str, Any]:
        """Compare candidates side-by-side."""
        return compare_candidates(candidates, candidate_ids)


class CreditsNamespace:
    def __init__(self, client):
        self.client = client

    def get_balance(self) -> Dict[str, Any]:
        """Get current credit balance."""
        f = _unwrap(get_credit_balance)
        return f(api_token=self.client.api_token, base_url=self.client.base_url)

    def estimate_cost(self, candidate_count: int) -> Dict[str, Any]:
        """Estimate screening cost."""
        f = _unwrap(estimate_screening_cost)
        return f(candidate_count, api_token=self.client.api_token, base_url=self.client.base_url)

    def list_packs(self) -> Dict[str, Any]:
        """List available credit packs."""
        f = _unwrap(list_credit_packs)
        return f(api_token=self.client.api_token, base_url=self.client.base_url)


class CalendarNamespace:
    def __init__(self, client):
        self.client = client

    def list(self) -> Dict[str, Any]:
        """List all connected calendar and meeting tools."""
        f = _unwrap(list_calendar_connections)
        return f(api_token=self.client.api_token, base_url=self.client.base_url)

    def connect(self, provider: str, api_key: str, calendar_id: Optional[str] = None) -> Dict[str, Any]:
        """Connect a calendar provider."""
        f = _unwrap(create_calendar_connection)
        return f(provider, api_key, calendar_id, api_token=self.client.api_token, base_url=self.client.base_url)

    def get_slots(self, provider: str, date: str, duration: int = 60) -> Dict[str, Any]:
        """Get available time slots."""
        f = _unwrap(get_available_slots)
        return f(provider, date, duration, api_token=self.client.api_token, base_url=self.client.base_url)

    def create_interview(self, **kwargs) -> Dict[str, Any]:
        """Create an interview with calendar event and meeting link."""
        f = _unwrap(create_interview)
        return f(api_token=self.client.api_token, base_url=self.client.base_url, **kwargs)

    def generate_link(self, provider: str, topic: str, duration: int = 60) -> Dict[str, Any]:
        """Generate a meeting link (Zoom, Google Meet, etc.)."""
        f = _unwrap(generate_meeting_link)
        return f(provider, topic, duration, api_token=self.client.api_token, base_url=self.client.base_url)


class AgentKeysNamespace:
    def __init__(self, client):
        self.client = client

    def list(self) -> Dict[str, Any]:
        """List all agent API keys."""
        f = _unwrap(list_agent_keys)
        return f(api_token=self.client.api_token, base_url=self.client.base_url)

    def create(self, name: str, **kwargs) -> Dict[str, Any]:
        """Create a new agent API key."""
        f = _unwrap(create_agent_key)
        return f(name, api_token=self.client.api_token, base_url=self.client.base_url, **kwargs)

    def get(self, key_id: int) -> Dict[str, Any]:
        """Get details for a specific agent API key."""
        f = _unwrap(get_agent_key)
        return f(key_id, api_token=self.client.api_token, base_url=self.client.base_url)

    def update(self, key_id: int, **kwargs) -> Dict[str, Any]:
        """Update an existing agent API key."""
        f = _unwrap(update_agent_key)
        return f(key_id, api_token=self.client.api_token, base_url=self.client.base_url, **kwargs)

    def revoke(self, key_id: int) -> Dict[str, Any]:
        """Revoke (delete) an agent API key."""
        f = _unwrap(revoke_agent_key)
        return f(key_id, api_token=self.client.api_token, base_url=self.client.base_url)

    def regenerate(self, key_id: int) -> Dict[str, Any]:
        """Regenerate an agent API key."""
        f = _unwrap(regenerate_agent_key)
        return f(key_id, api_token=self.client.api_token, base_url=self.client.base_url)

    def get_usage(self, key_id: int) -> Dict[str, Any]:
        """Get usage metrics for an agent API key."""
        f = _unwrap(get_agent_key_usage)
        return f(key_id, api_token=self.client.api_token, base_url=self.client.base_url)


class HireSquire:
    """
    HireSquire SDK client.
    
    Example:
        client = HireSquire("YOUR_API_TOKEN")
        job = client.jobs.create("Job title", "Job description", ["resume1.txt", "resume2.txt"])
        results = client.jobs.wait(job["job_id"])
    """
    
    def __init__(self, api_token: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize HireSquire client.
        
        Args:
            api_token: Your API token. If not provided, HIRESQUIRE_API_TOKEN env var is used.
            base_url: Optional custom API base URL.
        """
        self.api_token = api_token or os.environ.get("HIRESQUIRE_API_TOKEN")
        
        if not self.api_token:
            raise HireSquireError(
                "HireSquire API token is required. Please provide it as an argument "
                "or set the HIRESQUIRE_API_TOKEN environment variable."
            )
            
        self.base_url = base_url or os.environ.get("HIRESQUIRE_BASE_URL", "https://hiresquireai.com/api/v1")
        
        # Initialize namespaces
        self.jobs = JobsNamespace(self)
        self.candidates = CandidatesNamespace(self)
        self.credits = CreditsNamespace(self)
        self.calendar = CalendarNamespace(self)
        self.agent_keys = AgentKeysNamespace(self)
    
    def whoami(self) -> Dict[str, Any]:
        """Verify API token and get profile info."""
        f = _unwrap(whoami)
        return f(api_token=self.api_token, base_url=self.base_url)

    def screen(self, title: str, description: str, resumes: List[Union[str, Dict[str, str]]], **kwargs) -> Dict[str, Any]:
        """
        Submit a screening job and wait for completion (shortcut).
        
        Args:
            title: Job title
            description: Job description
            resumes: List of file paths or resume content dicts
            
        Returns:
            The created job object. Use wait_for_completion() to get results.
        """
        return self.jobs.create(title, description, resumes, **kwargs)

    def wait_for_completion(self, job_id: int, **kwargs) -> Dict[str, Any]:
        """
        Poll until job completes and return results (shortcut).
        
        Args:
            job_id: The job ID to wait for
            
        Returns:
            The completed job results.
        """
        return self.jobs.wait(job_id, **kwargs)


__all__ = [
    "__version__",
    "HireSquire",
    "create_screening_job",
    "get_screening_status",
    "get_screening_results",
    "wait_for_screening_completion",
    "generate_candidate_email",
    "get_candidates_by_score",
    "get_hiresquire_tools",
    "read_resume_from_file",
    "compare_candidates",
    "get_credit_balance",
    "estimate_screening_cost",
    "list_credit_packs",
    "list_calendar_connections",
    "create_calendar_connection",
    "get_available_slots",
    "create_interview",
    "generate_meeting_link",
    "whoami",
    "list_agent_keys",
    "create_agent_key",
    "get_agent_key",
    "update_agent_key",
    "revoke_agent_key",
    "regenerate_agent_key",
    "get_agent_key_usage",
    "HireSquireError",
]
