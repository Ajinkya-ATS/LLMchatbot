from langchain_community.tools import DuckDuckGoSearchRun
from langchain_experimental.tools.python.tool import PythonREPLTool

class ToolManager:
    """
    Provides and configures the set of tools available to agentic mode.
    Tools in this manager can be used by REAct-style agents.
    """

    _tools_cache: list = None

    @classmethod
    def get_tools(cls) -> list:
        """Return the list of tools. The Python REPL is instantiated only once."""
        if cls._tools_cache is None:
            python_repl_tool = PythonREPLTool(
                name="python_interpreter",
                description=(
                    "A stateful Python REPL interpreter. "
                    "Use for math, calculations, data analysis, unit conversion, plotting, etc. "
                    "Always use print(...) for the final result. "
                    "The environment has numpy, pandas, matplotlib, sympy, etc."
                ),
                globals={"__builtins__": {}},
            )

            cls._tools_cache = [
                DuckDuckGoSearchRun(name="web_search"),
                python_repl_tool,
            ]

        return cls._tools_cache