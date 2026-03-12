from langchain_classic.agents import create_react_agent, AgentExecutor
from langchain_ollama import ChatOllama
from .tool_manager import ToolManager
from .prompt_manager import PromptManager
from config import OLLAMA_BASE_URL

class AgentManager:

    def get_agent(self, model: str):
        llm = ChatOllama(
            model=model,
            temperature=0,
            base_url=OLLAMA_BASE_URL
        )
        tools = ToolManager.get_tools()
        prompt = PromptManager.get_react_prompt()

        agent = create_react_agent(llm, tools, prompt=prompt)
        executor = AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=tools,
            verbose=True
        )
        return executor