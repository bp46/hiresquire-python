# HireSquire SDK Examples

This directory contains recipes for integrating HireSquire into popular AI agent frameworks.

## Recipes

### 1. [CrewAI Recruiter](crewai_recruiter.py)
Build a sequential multi-agent crew where one agent screens resumes and another generates outreach emails.
- **Library**: `crewai`
- **Key Feature**: Sequential task processing with shared tool context.

### 2. [AutoGen Recruiter](autogen_recruiter.py)
A conversational multi-agent setup where an Assistant Agent uses HireSquire tools and a User Proxy Agent executes them.
- **Library**: `autogen`
- **Key Feature**: Native tool registration and execution loop.

## Setup

Ensure you have your API token set:
```bash
export HIRESQUIRE_API_TOKEN=your_token_here
```

Install dependencies:
```bash
pip install hiresquire crewai autogen
```
