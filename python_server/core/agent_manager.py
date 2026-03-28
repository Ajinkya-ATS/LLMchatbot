from langchain_classic.agents import create_react_agent, AgentExecutor
from langchain_ollama import ChatOllama
from .tool_manager import ToolManager
from .prompt_manager import PromptManager
from config import Config
from langchain_experimental.agents import create_pandas_dataframe_agent
from prompts.csv_prefix_prompt import CSV_PREFIX_PROMPT
import pandas as pd
import numpy as np
from langchain.tools import tool
import ast
from RestrictedPython import compile_restricted
from RestrictedPython import safe_globals, utility_builtins


class CSVAgent:
    """
    Agent wrapper enabling LLM interactions with CSV data.
    Supports dataframe querying, analysis, and safe execution of plotting code.
    """
    def __init__(self):
        """
        Initializes CSVAgent with empty agent & dataframe references.
        """
        self.agent = None
        self.df = None
    
    def safe_execute_pandas(code: str, df):
        byte_code = compile_restricted(
            code,
            filename="<restrictedCSV>",
            mode="exec"
        )

        restricted_globals = {
            **safe_globals,
            **utility_builtins,
            "_print_": print,
            "pd": pd,
            "np": np,
            "df": df,
        }

        restricted_locals = {}

        exec(byte_code, restricted_globals, restricted_locals)

        return restricted_locals
    
    @tool
    @staticmethod
    def execute_plot_code(df, code: str) -> str:
        """
        Executes Python code passed from the agent (for answering user question).

        The execution environment only exposes:
        - df: the loaded pandas DataFrame
        - pd: pandas library

        Returns:
            str: status message indicating success or error.
        """
        try:
            CSVAgent.safe_execute_pandas(code, df)
            return "code executed successfully"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def create_pandas_agent(self, model, df):
        """
        Creates a Pandas DataFrame agent using the provided LLM model and dataframe.
        Allows the agent to execute SQL-like reasoning, analysis, and plotting.

        Args:
            model (str): Model name for the LLM.
            df (pd.DataFrame): Loaded CSV dataframe.

        Returns:
            bool: True if agent created successfully; otherwise False.
        """
        try:
            self.df = df
            llm = ChatOllama(
                model=model,
                temperature=0.1,
                base_url=Config.OLLAMA_BASE_URL
            )

            self.agent = create_pandas_dataframe_agent(
                llm,
                df,
                verbose=True,
                allow_dangerous_code=True,
                agent_type="tool-calling",
                prefix=CSV_PREFIX_PROMPT,
                extra_tools=[CSVAgent.execute_plot_code] # Will add it later for graph plotting logic
            )
            return True
        except Exception as e:
            print("Exception while creating csv agent: ", e)
            return False

    def execute_query(self, query):
        """
        Executes a query using the active CSV agent.

        Args:
            query (str): User query or instruction related to CSV.

        Returns:
            str: Output from agent or error message.
        """
        if self.agent:
            results = self.agent.invoke({"input": query})
            return results['output']
        return "Some error happened"


class AgenticMode:
    """
    Manages creation and caching of agentic mode LLM agents.
    Agents include tool use, REAct-style reasoning, and step-by-step workflows.
    """
    _agent_cache: dict[str, AgentExecutor] = {}

    def get_agent(self, model: str) -> AgentExecutor:
        if model not in self._agent_cache:
            self._agent_cache[model] = self._build_agent(model)
        return self._agent_cache[model]
    
    def _build_agent(self, model: str) -> AgentExecutor:
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
            max_iterations=10,
            early_stopping_method="force",
            handle_parsing_errors="output_fixing",
        )
        return executor