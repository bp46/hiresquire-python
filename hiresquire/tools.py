"""
HireSquire Tools for LangChain
===============================

LangChain @tool decorated functions for candidate screening.
"""

import os
import time
import uuid
import requests
from typing import Optional, List, Dict, Any

# Optional LangChain support - use no-op decorator if not available
try:
    from langchain_core.tools import tool
except ImportError:
    # No-op decorator for use without LangChain
    def tool(func):
        func.is_hiresquire_tool = True
        return func



# Default values
DEFAULT_BASE_URL = "https://hiresquireai.com/api/v1"
MAX_RETRIES = 3
RETRY_DELAY = 1

def _get_api_token(token: Optional[str] = None) -> str:
    """Get API token from parameter or environment."""
    return token or os.environ.get("HIRESQUIRE_API_TOKEN", "")

def _get_base_url(url: Optional[str] = None) -> str:
    """Get Base URL from parameter or environment."""
    return url or os.environ.get("HIRESQUIRE_BASE_URL", DEFAULT_BASE_URL)


def _retry_with_backoff(func, *args, **kwargs) -> Dict[str, Any]:
    """Execute function with exponential backoff retry logic."""
    last_exception = None
    for attempt in range(MAX_RETRIES):
        try:
            result = func(*args, **kwargs)
            return result if result is not None else {}
        except requests.exceptions.RequestException as e:
            last_exception = e
            
            # If we have a response, only retry on specific status codes
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                
                # 429 Rate Limit - always retry with backoff or retry-after
                if status_code == 429:
                    retry_after = e.response.headers.get('retry-after', str(RETRY_DELAY * 4))
                    try:
                        time.sleep(int(retry_after))
                    except (ValueError, TypeError):
                        time.sleep(RETRY_DELAY * 4)
                    continue
                
                # 5xx Server Error - retry with exponential backoff
                if 500 <= status_code < 600:
                    if attempt < MAX_RETRIES - 1:
                        delay = RETRY_DELAY * (2 ** attempt)
                        time.sleep(delay)
                        continue
                
                # For all other errors (401, 403, 404, 422), raise immediately
                raise last_exception
            
            # Network-level errors (no response) - retry with exponential backoff
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY * (2 ** attempt)
                time.sleep(delay)
                continue
                
    if last_exception:
        raise last_exception
    return {}

class HireSquireError(Exception):
    """Base exception for HireSquire SDK."""
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

def _get_headers(token: Optional[str] = None, idempotency_key: Optional[str] = None) -> Dict[str, str]:
    """Get common headers for API requests."""
    api_token = _get_api_token(token)
    if not api_token:
        raise ValueError("HIRESQUIRE_API_TOKEN not set. Pass to function or set HIRESQUIRE_API_TOKEN environment variable.")
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
        "User-Agent": "HireSquirePythonSDK/1.2.3"
    }
    
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
        
    return headers


@tool
def whoami(api_token: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Verify API token validity and get profile/balance info.
    """
    def _make_request():
        response = requests.get(
            f"{_get_base_url(base_url)}/schema/validate",
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def get_credit_balance(api_token: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Get current credit balance and check if you can afford screening.
    """
    def _make_request():
        response = requests.get(
            f"{_get_base_url(base_url)}/credits/balance",
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def estimate_screening_cost(candidate_count: int, api_token: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Estimate cost for screening a number of candidates.
    """
    def _make_request():
        response = requests.get(
            f"{_get_base_url(base_url)}/credits/estimate",
            headers=_get_headers(api_token),
            params={"candidate_count": candidate_count},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def create_screening_job(
    title: str,
    description: str,
    resumes: List[Dict[str, str]],
    leniency_level: int = 5,
    custom_instructions: str = "",
    webhook_url: str = "",
    idempotency_key: Optional[str] = None,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Submit a new candidate screening job.
    """
    payload = {
        "title": title,
        "description": description,
        "resumes": resumes,
        "leniency_level": leniency_level
    }
    
    if custom_instructions:
        payload["custom_instructions"] = custom_instructions
    
    if webhook_url:
        payload["webhook_url"] = webhook_url
    
    # Generate idempotency key OUTSIDE the retry loop to ensure stability across retries
    ikey = idempotency_key or str(uuid.uuid4())
    
    def _make_request():
        response = requests.post(
            f"{_get_base_url(base_url)}/jobs",
            json=payload,
            headers=_get_headers(api_token, idempotency_key=ikey),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def create_screening_job_from_zip(
    title: str,
    description: str,
    zip_path: str,
    leniency_level: int = 5,
    custom_instructions: str = "",
    webhook_url: str = "",
    idempotency_key: Optional[str] = None,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Submit a new candidate screening job by uploading a ZIP file of resumes.
    
    This is an async operation - the job is queued for processing.
    Use get_screening_status to poll for completion.
    
    Args:
        title: Job posting title (e.g., "Senior PHP Developer")
        description: Full job description/requirements (min 50 characters)
        zip_path: Absolute or relative path to a ZIP file containing resumes
        leniency_level: Strictness level 1-10 (default 5)
        custom_instructions: Optional custom instructions for the AI
        webhook_url: Optional webhook URL for async notifications
    
    Returns:
        Dict with job_id, status_url, results_url, and status
    """
    data = {
        "title": title,
        "description": description,
        "leniency_level": str(leniency_level)
    }
    
    if custom_instructions:
        data["custom_instructions"] = custom_instructions
    
    if webhook_url:
        data["webhook_url"] = webhook_url
    
    # Generate idempotency key OUTSIDE the retry loop
    ikey = idempotency_key or str(uuid.uuid4())
    
    def _make_request():
        with open(zip_path, 'rb') as f:
            files = {'zip_file': ('resumes.zip', f, 'application/zip')}
            headers = _get_headers(api_token, idempotency_key=ikey)
            # Remove content-type so requests can set multipart boundary automatically
            if 'Content-Type' in headers:
                del headers['Content-Type']
            
            response = requests.post(
                f"{_get_base_url(base_url)}/jobs/upload-zip",
                data=data,
                files=files,
                headers=headers,
                timeout=120 # longer timeout for file upload
            )
            response.raise_for_status()
            return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def get_screening_status(job_id: int, api_token: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Check the status of a screening job.
    """
    def _make_request():
        response = requests.get(
            f"{_get_base_url(base_url)}/jobs/{job_id}",
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def get_screening_results(job_id: int, api_token: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Get the results of a completed screening job.
    
    Only call this when status is 'completed'. Use get_screening_status first.
    
    Args:
        job_id: The job ID returned from create_screening_job
    
    Returns:
        Dict with job details and list of candidates with scores
    
    Example:
        >>> results = get_screening_results(job_id=123)
        >>> for candidate in results["candidates"]:
        ...     print(f"{candidate['name']}: {candidate['score']}")
    """
    def _make_request():
        response = requests.get(
            f"{_get_base_url(base_url)}/jobs/{job_id}/results",
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def wait_for_screening_completion(
    job_id: int,
    poll_interval: int = 3,
    max_wait_seconds: int = 300,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Poll job status until screening completes or fails.
    
    This is a convenience wrapper around get_screening_status.
    
    Args:
        job_id: The job ID to wait for
        poll_interval: Seconds between polls (default 3)
        max_wait_seconds: Maximum time to wait (default 300 = 5 minutes)
    
    Returns:
        The completed job results
    
    Raises:
        TimeoutError: If job doesn't complete within max_wait_seconds
    """
    start_time = time.time()
    
    while time.time() - start_time < max_wait_seconds:
        status = get_screening_status(job_id, api_token=api_token, base_url=base_url)
        
        if status["status"] == "completed":
            return get_screening_results(job_id, api_token=api_token, base_url=base_url)
        elif status["status"] == "failed":
            raise Exception(f"Screening job {job_id} failed")
        
        time.sleep(poll_interval)
    
    raise TimeoutError(f"Job {job_id} did not complete within {max_wait_seconds} seconds")


@tool
def generate_candidate_email(
    job_id: int,
    candidate_id: int,
    email_type: str = "invite",
    tone: str = "professional",
    custom_notes: str = "",
    api_token: Optional[str] = None,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate an email for a candidate.
    
    Args:
        job_id: The job ID the candidate belongs to
        candidate_id: The candidate ID
        email_type: One of 'invite', 'rejection', or 'keep-warm'
        tone: One of 'professional', 'friendly', or 'formal'
        custom_notes: Optional custom message to include
    
    Returns:
        Dict with generated email content
    
    Example:
        >>> email = generate_candidate_email(
        ...     job_id=123,
        ...     candidate_id=1,
        ...     email_type="invite",
        ...     tone="friendly",
        ...     custom_notes="We are excited to meet you!"
        ... )
    """
    def _make_request():
        response = requests.post(
            f"{_get_base_url(base_url)}/jobs/{job_id}/generate-email",
            json={
                "candidate_id": candidate_id,
                "type": email_type,
                "tone": tone,
                "custom_notes": custom_notes
            },
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def get_candidates_by_score(
    job_id: int,
    min_score: int = 0,
    max_score: int = 100,
    only_top_n: int = 0,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get candidates from a job filtered by score range.
    
    Uses server-side filtering for efficiency.
    
    Args:
        job_id: The job ID to get candidates from
        min_score: Minimum score (inclusive), default 0
        max_score: Maximum score (inclusive), default 100
        only_top_n: Return only top N candidates by score, default 0 (no limit)
    
    Returns:
        Dict with job details and filtered candidate list
    
    Example:
        >>> result = get_candidates_by_score(
        ...     job_id=123,
        ...     min_score=80,
        ...     only_top_n=5
        ... )
        >>> for candidate in result["candidates"]:
        ...     print(f"{candidate['name']}: {candidate['score']}")
    """
    params = {
        "min_score": min_score,
        "max_score": max_score,
    }
    if only_top_n > 0:
        params["only_top_n"] = only_top_n
    
    def _make_request():
        response = requests.get(
            f"{_get_base_url(base_url)}/jobs/{job_id}/results",
            params=params,
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def cancel_screening_job(job_id: int, api_token: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Cancel a running screening job.
    
    Args:
        job_id: The job ID to cancel
    
    Returns:
        Dict with job_id, status, and message
    
    Example:
        >>> result = cancel_screening_job(job_id=123)
        >>> print(result["status"])
    """
    def _make_request():
        response = requests.post(
            f"{_get_base_url(base_url)}/jobs/{job_id}/cancel",
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def report_hiring_outcome(
    job_id: int,
    candidate_id: int,
    outcome: str,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Report hiring outcome to improve AI accuracy.
    
    Args:
        job_id: The job ID the candidate belongs to
        candidate_id: The candidate ID
        outcome: One of 'hired', 'rejected', or 'withdrawn'
    
    Returns:
        Dict with success message
    
    Example:
        >>> result = report_hiring_outcome(
        ...     job_id=123,
        ...     candidate_id=1,
        ...     outcome="hired"
        ... )
    """
    valid_outcomes = ['hired', 'rejected', 'withdrawn']
    if outcome not in valid_outcomes:
        raise ValueError(f"Invalid outcome. Must be one of: {valid_outcomes}")
    
    def _make_request():
        response = requests.post(
            f"{_get_base_url(base_url)}/jobs/{job_id}/outcome",
            json={"candidate_id": candidate_id, "outcome": outcome},
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def test_webhook(url: str, api_token: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Test a webhook endpoint.
    
    Args:
        url: The webhook URL to test
    
    Returns:
        Dict with success status, message, and response code
    
    Example:
        >>> result = test_webhook(url="https://example.com/webhook")
        >>> print(result["success"])
    """
    def _make_request():
        response = requests.post(
            f"{_get_base_url(base_url)}/webhooks/test",
            json={"url": url},
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def get_rate_limit(api_token: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Get current API rate limit status.
    
    Returns:
        Dict with limit, remaining, reset_at, and reset_in_seconds
    
    Example:
        >>> limits = get_rate_limit()
        >>> print(f"Remaining: {limits['remaining']}")
    """
    def _make_request():
        response = requests.get(
            f"{_get_base_url(base_url)}/rate-limit",
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def get_candidate(candidate_id: int, api_token: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Get details of a specific candidate.
    
    Args:
        candidate_id: The candidate ID
    
    Returns:
        Dict with candidate details
    
    Example:
        >>> candidate = get_candidate(candidate_id=1)
        >>> print(candidate["name"])
    """
    def _make_request():
        response = requests.get(
            f"{_get_base_url(base_url)}/candidates/{candidate_id}",
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def update_candidate_status(
    candidate_id: int,
    status: str,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update a candidate's status.
    
    Args:
        candidate_id: The candidate ID
        status: New status (pending, shortlisted, rejected, interviewed, offered, hired)
    
    Returns:
        Dict with success and updated candidate
    
    Example:
        >>> result = update_candidate_status(
        ...     candidate_id=1,
        ...     status="hired"
        ... )
    """
    valid_statuses = ['pending', 'shortlisted', 'rejected', 'interviewed', 'offered', 'hired']
    if status not in valid_statuses:
        raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
    
    def _make_request():
        response = requests.patch(
            f"{_get_base_url(base_url)}/candidates/{candidate_id}/status",
            json={"status": status},
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def enable_auto_reload(
    threshold: float,
    amount: float,
    payment_method_id: str,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enable automatic credit reloading when balance drops below threshold.
    
    Args:
        threshold: Minimum balance to trigger reload (in dollars)
        amount: Amount to reload each time (in dollars, min $5)
        payment_method_id: Stripe payment method ID to use
    
    Returns:
        Dict with auto-reload status
    
    Example:
        >>> enable_auto_reload(threshold=10, amount=25, payment_method_id="pm_123")
    """
    def _make_request():
        response = requests.post(
            f"{_get_base_url(base_url)}/credits/auto-reload/enable",
            json={
                "threshold": threshold,
                "amount": amount,
                "payment_method_id": payment_method_id
            },
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def disable_auto_reload(api_token: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Disable automatic credit reloading.
    
    Returns:
        Dict with success status
    
    Example:
        >>> disable_auto_reload()
    """
    def _make_request():
        response = requests.post(
            f"{_get_base_url(base_url)}/credits/auto-reload/disable",
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def purchase_credits(
    amount: Optional[float] = None,
    pack: Optional[str] = None,
    payment_method_id: Optional[str] = None,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Purchase credits immediately using saved payment method.
    
    Args:
        amount: Amount to purchase in dollars (min $5)
        pack: Credit pack to purchase: pouch, satchel, chest
        payment_method_id: Stripe payment method ID
    
    Returns:
        Dict with purchase result
    
    Example:
        >>> purchase_credits(pack="satchel", payment_method_id="pm_123")
        >>> purchase_credits(amount=25, payment_method_id="pm_123")
    """
    if not amount and not pack:
        raise ValueError("Either amount or pack must be provided")
    if not payment_method_id:
        raise ValueError("payment_method_id is required for direct purchase")
    
    payload = {"payment_method_id": payment_method_id}
    if amount:
        payload["amount"] = float(amount)
    if pack:
        payload["pack"] = str(pack)
    
    def _make_request():
        response = requests.post(
            f"{_get_base_url(base_url)}/credits/purchase",
            json=payload,
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def create_payment_intent(
    amount: float,
    payment_method_id: Optional[str] = None,
    return_url: Optional[str] = None,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a Stripe PaymentIntent for credit purchase.
    
    Args:
        amount: Amount to purchase in dollars
        payment_method_id: Optional saved payment method
        return_url: Optional return URL for 3D Secure
    
    Returns:
        Dict with client_secret and payment intent details
    
    Example:
        >>> create_payment_intent(amount=25, payment_method_id="pm_123")
    """
    payload = {"amount": amount}
    if payment_method_id:
        payload["payment_method_id"] = payment_method_id
    if return_url:
        payload["return_url"] = return_url
    
    def _make_request():
        response = requests.post(
            f"{_get_base_url(base_url)}/credits/payment-intent",
            json=payload,
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def list_credit_packs(api_token: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    List available credit packs for purchase.
    
    Returns:
        Dict with list of available packs, prices, and credit amounts.
    
    Example:
        >>> packs = list_credit_packs()
        >>> for pack_key, pack in packs['packs'].items():
        ...     print(f"{pack_key}: ${pack['price']} for {pack['credits']} credits")
    """
    def _make_request():
        response = requests.get(
            f"{_get_base_url(base_url)}/credits/packs",
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def get_credit_transactions(
    limit: int = 50,
    offset: int = 0,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get credit transaction history.
    
    Args:
        limit: Maximum number of transactions to return (default 50)
        offset: Number of transactions to skip for pagination (default 0)
    
    Returns:
        Dict with transactions list and current balance
    
    Example:
        >>> transactions = get_credit_transactions(limit=20, offset=0)
        >>> for tx in transactions['transactions']:
        ...     print(f"{tx['type']}: {tx['amount']}")
    """
    def _make_request():
        response = requests.get(
            f"{_get_base_url(base_url)}/credits/transactions",
            headers=_get_headers(api_token),
            params={"limit": limit, "offset": offset},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


# ============================================================================
# File Parsing Utilities
# ============================================================================

@tool
def read_resume_from_file(file_path: str) -> Dict[str, str]:
    """
    Read a resume from a file path, supporting multiple formats.
    
    Args:
        file_path: Path to the resume file (.txt, .pdf, .doc, .docx, .md)
    
    Returns:
        Dict with 'filename' and 'content' keys
    
    Example:
        >>> resume = read_resume_from_file("john_doe_resume.pdf")
        >>> print(resume['filename'])
        john_doe_resume.pdf
    """
    import os
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Resume file not found: {file_path}")
    
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    
    content = ""
    
    if ext == '.txt' or ext == '.md':
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    
    elif ext == '.pdf':
        try:
            import pypdf
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    content += page.extract_text() or ""
        except ImportError:
            raise ImportError("pypdf is required to parse PDF files. Please run 'pip install pypdf'.")
    
    elif ext in ['.doc', '.docx']:
        try:
            import docx
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                content += para.text + "\n"
        except ImportError:
            raise ImportError("python-docx is required to parse DOCX files. Please run 'pip install python-docx'.")
    
    else:
        raise ValueError(f"Unsupported file format: {ext}")
    if not content.strip():
        raise ValueError(f"Could not extract text from: {file_path}")
    
    return {"filename": filename, "content": content}


# ============================================================================
# Candidate Comparison Utilities
# ============================================================================

@tool
def compare_candidates(
    candidates: List[Dict[str, Any]],
    candidate_ids: List[int]
) -> Dict[str, Any]:
    """
    Compare two or more candidates side-by-side with AI-powered Delta Analysis.
    
    Args:
        candidates: List of candidate dicts from get_screening_results
        candidate_ids: List of candidate IDs to compare
    
    Returns:
        Dict with comparison analysis
    
    Example:
        >>> results = get_screening_results(job_id=123)
        >>> comparison = compare_candidates(results['candidates'], [1, 2, 3])
        >>> print(comparison['top_candidate'])
    """
    selected = [c for c in candidates if c['id'] in candidate_ids]
    
    if len(selected) < 2:
        raise ValueError("Need at least 2 candidates to compare")
    
    sorted_candidates = sorted(selected, key=lambda x: x.get('score', 0), reverse=True)
    
    score_diff = sorted_candidates[0].get('score', 0) - sorted_candidates[-1].get('score', 0)
    
    comparison = {
        "compared_count": len(selected),
        "top_candidate": sorted_candidates[0].get('name'),
        "top_score": sorted_candidates[0].get('score'),
        "score_range": score_diff,
        "candidates": [
            {
                "id": c.get('id'),
                "name": c.get('name'),
                "score": c.get('score'),
                "summary": c.get('summary', '')[:100],
            }
            for c in sorted_candidates
        ],
    }
    
    return comparison



# ===========================================================================
# Calendar & Meeting Utilities
# ===========================================================================

@tool
def list_calendar_connections(api_token: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """List all connected calendar and meeting tools."""
    def _make_request():
        response = requests.get(
            f"{_get_base_url(base_url)}/calendar/connections",
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)

@tool
def get_available_slots(
    provider: str,
    date: str,
    duration: int = 60,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """Get available time slots from a calendar provider.
    
    Args:
        provider: Calendar provider (calendly, calcom)
        date: Date in Y-m-d format
        duration: Duration in minutes (default 60)
    
    Returns:
        Dict with available slots
    """
    def _make_request():
        response = requests.get(
            f"{_get_base_url(base_url)}/calendar/slots",
            headers=_get_headers(api_token),
            params={'provider': provider, 'date': date, 'duration': duration},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)

@tool
def create_interview(
    job_id: int,
    candidate_id: int,
    scheduled_at: str,
    duration_minutes: int = 60,
    provider: Optional[str] = None,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """Create an interview with calendar event and meeting link.
    
    Args:
        job_id: Job posting ID
        candidate_id: Candidate ID
        scheduled_at: ISO 8601 datetime string
        duration_minutes: Duration in minutes (default 60)
        provider: Optional calendar provider
    
    Returns:
        Dict with interview data and meeting link
    """
    def _make_request():
        data = {
            'job_id': job_id,
            'candidate_id': candidate_id,
            'scheduled_at': scheduled_at,
            'duration_minutes': duration_minutes,
        }
        if provider:
            data['provider'] = provider
        
        response = requests.post(
            f"{_get_base_url(base_url)}/interviews",
            headers=_get_headers(api_token),
            json=data,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)

@tool
def generate_meeting_link(
    provider: str,
    topic: str,
    duration: int = 60,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """Generate a meeting link (Zoom, Google Meet, etc.).
    
    Args:
        provider: Meeting provider (calendly, calcom)
        topic: Meeting topic/title
        duration: Duration in minutes (default 60)
    
    Returns:
        Dict with meeting link
    """
    def _make_request():
        response = requests.post(
            f"{_get_base_url(base_url)}/meetings/links",
            headers=_get_headers(api_token),
            json={'provider': provider, 'topic': topic, 'duration': duration},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def create_calendar_connection(
    provider: str,
    api_key: str,
    calendar_id: Optional[str] = None,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """Connect a calendar provider (calendly, calcom) to HireSquire.
    
    Args:
        provider: Calendar provider (calendly, calcom)
        api_key: API key for the provider
        calendar_id: Optional specific calendar ID
    
    Returns:
        Dict with connection details
    """
    def _make_request():
        data = {
            'provider': provider,
            'api_key': api_key,
        }
        if calendar_id:
            data['calendar_id'] = calendar_id
        
        response = requests.post(
            f"{_get_base_url(base_url)}/calendar/connections",
            headers=_get_headers(api_token),
            json=data,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


def get_hiresquire_tools():
    """Return a list of all Hiresquire tools for LangChain."""
    return [
        create_screening_job,
        create_screening_job_from_zip,
        get_screening_status,
        get_screening_results,
        wait_for_screening_completion,
        generate_candidate_email,
        get_candidates_by_score,
        read_resume_from_file,
        compare_candidates,
        cancel_screening_job,
        report_hiring_outcome,
        test_webhook,
        get_rate_limit,
        get_candidate,
        update_candidate_status,
        enable_auto_reload,
        disable_auto_reload,
        purchase_credits,
        create_payment_intent,
        get_credit_balance,
        estimate_screening_cost,
        list_credit_packs,
        get_credit_transactions,
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
    ]
@tool
def list_agent_keys(api_token: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    List all agent API keys for the authenticated user.
    """
    def _make_request():
        response = requests.get(
            f"{_get_base_url(base_url)}/agent-keys",
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def create_agent_key(
    name: str,
    monthly_spend_limit: Optional[float] = None,
    daily_spend_limit: Optional[float] = None,
    lifetime_spend_limit: Optional[float] = None,
    permissions: Optional[List[str]] = None,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new agent API key with specified spend limits and permissions.
    """
    payload = {"name": name}
    if monthly_spend_limit is not None: payload["monthly_spend_limit"] = monthly_spend_limit
    if daily_spend_limit is not None: payload["daily_spend_limit"] = daily_spend_limit
    if lifetime_spend_limit is not None: payload["lifetime_spend_limit"] = lifetime_spend_limit
    if permissions: payload["permissions"] = permissions
    
    def _make_request():
        response = requests.post(
            f"{_get_base_url(base_url)}/agent-keys",
            json=payload,
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def get_agent_key(key_id: int, api_token: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Get details for a specific agent API key.
    """
    def _make_request():
        response = requests.get(
            f"{_get_base_url(base_url)}/agent-keys/{key_id}",
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def update_agent_key(
    key_id: int,
    name: Optional[str] = None,
    monthly_spend_limit: Optional[float] = None,
    daily_spend_limit: Optional[float] = None,
    lifetime_spend_limit: Optional[float] = None,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update an existing agent API key's settings.
    """
    payload = {}
    if name is not None: payload["name"] = name
    if monthly_spend_limit is not None: payload["monthly_spend_limit"] = monthly_spend_limit
    if daily_spend_limit is not None: payload["daily_spend_limit"] = daily_spend_limit
    if lifetime_spend_limit is not None: payload["lifetime_spend_limit"] = lifetime_spend_limit
    
    def _make_request():
        response = requests.put(
            f"{_get_base_url(base_url)}/agent-keys/{key_id}",
            json=payload,
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def revoke_agent_key(key_id: int, api_token: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Revoke (delete) an agent API key.
    """
    def _make_request():
        response = requests.delete(
            f"{_get_base_url(base_url)}/agent-keys/{key_id}",
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def regenerate_agent_key(key_id: int, api_token: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Regenerate an agent API key (revokes old key and returns new one).
    """
    def _make_request():
        response = requests.post(
            f"{_get_base_url(base_url)}/agent-keys/{key_id}/regenerate",
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)


@tool
def get_agent_key_usage(key_id: int, api_token: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Get detailed spend and usage metrics for a specific agent API key.
    """
    def _make_request():
        response = requests.get(
            f"{_get_base_url(base_url)}/agent-keys/{key_id}/usage",
            headers=_get_headers(api_token),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    return _retry_with_backoff(_make_request)
