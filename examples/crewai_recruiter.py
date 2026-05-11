from crewai import Agent, Task, Crew, Process
from hiresquire import get_hiresquire_tools
import os

# 1. Setup HireSquire Tools
# Ensure HIRESQUIRE_API_TOKEN is set in your environment
tools = get_hiresquire_tools()

# 2. Define Agents
screener = Agent(
    role='Resume Screener',
    goal='Accurately screen resumes against the job description using HireSquire',
    backstory="""You are an expert technical recruiter. You use HireSquire to 
    systematically analyze resumes and identify the best matches based on score.""",
    tools=tools,
    verbose=True
)

outreach_specialist = Agent(
    role='Candidate Outreach Specialist',
    goal='Generate personalized interview invitations for top-scoring candidates',
    backstory="""You specialize in candidate experience. Once the screener identifies 
    top talent, you use HireSquire to generate the perfect outreach email.""",
    tools=tools,
    verbose=True
)

# 3. Define Tasks
screening_task = Task(
    description="""Screen all resumes in the './resumes/' directory for the 'Senior Python Developer' role.
    The job description is: 'Looking for a dev with 5+ years experience, Django, and PostgreSQL'.
    Use HireSquire to get the scores. Return a list of candidate IDs with scores > 80.""",
    expected_output="A list of high-scoring candidate IDs.",
    agent=screener
)

outreach_task = Task(
    description="""For each candidate ID identified in the screening task, 
    use HireSquire to generate an 'invite' email. Summarize the results.""",
    expected_output="A summary of generated emails for top candidates.",
    agent=outreach_specialist,
    context=[screening_task]
)

# 4. Assemble the Crew
recruitment_crew = Crew(
    agents=[screener, outreach_specialist],
    tasks=[screening_task, outreach_task],
    process=Process.sequential
)

# 5. Kickoff
result = recruitment_crew.kickoff()
print("######################")
print(result)
