from langchain_community.tools import DuckDuckGoSearchRun
from langchain.tools import BaseTool
from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Guards import safer_getattr
from RestrictedPython.Eval import default_guarded_getiter
from RestrictedPython.PrintCollector import PrintCollector
from pydantic import Field
import traceback
import sys
from io import StringIO
from typing import Optional, List

class RestrictedPythonREPLTool(BaseTool):
    """LangChain-compatible tool that executes Python code using RestrictedPython for improved safety."""
    
    name: str = "python_interpreter"
    description: str = (
        "A stateful Python REPL interpreter using RestrictedPython. "
        "Use this for calculations, math, data analysis, unit conversions, plotting, etc. "
        "Always use print(...) to output the final result when needed. "
        "The environment has limited access — only whitelisted modules and safe operations are allowed."
    )
    
    # Configuration
    allowed_modules: List[str] = Field(
        default_factory=lambda: ["math", "random", "datetime", "json", "re", "sympy", "numpy", "pandas"]
    )
    extra_globals: Optional[dict] = Field(default=None)
    
    # Internal state
    _globals: dict = None
    _locals: dict = None
    
    def __init__(self, **data):
        super().__init__(**data)
        
        # Initialize RestrictedPython environment
        self._locals = {}
        self._globals = safe_globals.copy()
        
        # Security guards
        self._globals['_getattr_'] = safer_getattr
        self._globals['_getiter_'] = default_guarded_getiter
        self._globals['_print_'] = PrintCollector
        
        # Whitelist allowed modules
        self._allow_modules(self.allowed_modules)
        
        # Add any extra safe globals (e.g., custom helper functions)
        if self.extra_globals:
            self._globals.update(self.extra_globals)
    
    def _allow_modules(self, modules: List[str]):
        """Safely whitelist specific modules."""
        def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name in modules:
                return __import__(name, globals, locals, fromlist, level)
            raise ImportError(f"Import of '{name}' is not allowed in this restricted environment.")
        
        self._globals['__import__'] = safe_import
        
        # Pre-import common modules for convenience
        for mod_name in modules:
            try:
                self._globals[mod_name] = __import__(mod_name)
            except ImportError:
                pass  # Module not installed — skip silently
    
    def _run(self, query: str) -> str:
        """Execute the code (this is the method LangChain calls)."""
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            # Compile with RestrictedPython (blocks dangerous syntax)
            byte_code = compile_restricted(
                query,
                filename='<restrictedREPL>',
                mode='exec'
            )
            
            # Execute
            exec(byte_code, self._globals, self._locals)
            
            # Capture output from PrintCollector
            printed = self._globals['_print_']()
            if printed:
                print(printed, file=output, end='')
            
            result = output.getvalue()
            return result.strip() if result.strip() else "Code executed successfully (no output)."
            
        except Exception as e:
            tb = traceback.format_exc()
            return f"Error: {str(e)}\n\n{tb}"
        finally:
            sys.stdout = old_stdout
    
    def reset(self):
        """Clear the REPL session state."""
        self._locals.clear()


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
            python_repl_tool = RestrictedPythonREPLTool(
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