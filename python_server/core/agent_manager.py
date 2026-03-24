from langchain_classic.agents import create_react_agent, AgentExecutor
from langchain_ollama import ChatOllama
from functools import lru_cache
from .tool_manager import ToolManager
from .prompt_manager import PromptManager
from config import OLLAMA_BASE_URL
from langchain_ollama import ChatOllama
from langchain_experimental.agents import create_pandas_dataframe_agent
from prompts.csv_prefix_prompt import CSV_PREFIX_PROMPT
import pandas as pd
import matplotlib.pyplot as plt
from langchain.tools import tool

class CSVAgent:
    def __init__(self):
        self.agent = None
        self.df = None
    @tool
    def execute_plot_code(self, code: str) -> str:
        """Execute Python code that uses pandas dataframe df and matplotlib for plotting. 
        Returns the result of execution."""
        try:
            exec(code, {"df": self.df, "pd": pd, "plt": plt})
            return "Plot code executed successfully"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def create_pandas_agent(self, model, df):
        try:
            self.df = df
            llm = ChatOllama(
                model=model,
                temperature=0.1,
                base_url="http://localhost:11434"
            )

            self.agent = create_pandas_dataframe_agent(
                llm,
                df,
                verbose=True,
                allow_dangerous_code=True,
                agent_type="tool-calling",
                prefix=CSV_PREFIX_PROMPT,
                extra_tools=[self.execute_plot_code] # Will add it later for graph plotting logic
            )
            return True
        except Exception as e:
            print("Exception while creating csv agent: ", e)
            return False

    def execute_query(self, query):
        if self.agent:
            results = self.agent.invoke({"input": query})
            return results['output']
        return "Some error happened"


class AgenticMode:
    @lru_cache(maxsize=128)
    def get_agent(self, model: str):
        llm = ChatOllama(
            model=model,
            temperature=0,
            top_k=40,
            repeat_penalty=1.2
        )
        tools = ToolManager.get_tools()
        prompt = PromptManager.get_react_prompt()

        agent = create_react_agent(llm, tools, prompt=prompt)
        executor = AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=10,  # Prevent infinite loops
            early_stopping_method="force",  # Force stop after max iterations
            handle_parsing_errors="output_fixing",  # Handle malformed model outputs
        )
        return executor