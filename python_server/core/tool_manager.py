from langchain_community.tools import DuckDuckGoSearchRun
from langchain_experimental.tools.python.tool import PythonREPLTool
from langchain.tools import tool
from typing import Literal

class ToolManager:

    @staticmethod
    def get_tools():
        return [
            DuckDuckGoSearchRun(name="web_search"),
            PythonREPLTool(
                name="python_interpreter",
                description=(
                    "A stateful Python REPL interpreter. "
                    "Use for math, calculations, data analysis, unit conversion, plotting, etc. "
                    "Always use print(...) for the final result. "
                    "Environment has numpy, pandas, matplotlib, sympy."
                ),
                globals={"__builtins__": {}}  # basically avoiding harmful code execution like import os
            )
        ] # A list of tools