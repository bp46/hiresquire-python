import autogen
from hiresquire import get_hiresquire_tools
import os

# 1. Configuration
config_list = [
    {
        "model": "gpt-4-turbo",
        "api_key": os.environ.get("OPENAI_API_TOKEN")
    }
]

# 2. Setup HireSquire Tools
tools = get_hiresquire_tools()

# 3. Define Agents
user_proxy = autogen.UserProxyAgent(
    name="UserProxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
)

recruiter = autogen.AssistantAgent(
    name="Recruiter",
    llm_config={"config_list": config_list},
    system_message="""You are a recruiter powered by HireSquire. 
    Your goal is to screen candidates and report the best ones.
    Use the provided tools to submit jobs and fetch results.
    When done, say 'TERMINATE'.""",
)

# 4. Register tools for execution
# This allows the UserProxy to execute the tools requested by the Recruiter
for tool in tools:
    user_proxy.register_for_execution()(tool.func)
    recruiter.register_for_llm(name=tool.name, description=tool.description)(tool.func)

# 5. Start the conversation
user_proxy.initiate_chat(
    recruiter,
    message="Screen the resumes in ./candidates/ for the 'DevOps Engineer' role. Give me the top 3 scores."
)
