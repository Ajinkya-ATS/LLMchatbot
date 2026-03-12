from langchain_community.tools import DuckDuckGoSearchRun
from langchain_experimental.tools.python.tool import PythonREPLTool

class ToolManager:
    """SRP: Responsible ONLY for creating tools."""

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
                globals={"__builtins__": {}}  # security
            )
        ]