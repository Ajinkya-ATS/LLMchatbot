from langchain_core.prompts import PromptTemplate
from prompts.agentic_prompt import REACT_AGENT_PROMPT
from prompts.grafcet_prompt import GRAFCET_SYSTEM_PROMPT

class PromptManager:

    @staticmethod
    def get_react_prompt(): # React means reason + acting
        # The above prompt is from langchain examples (hwchase17/react)
        return PromptTemplate.from_template(REACT_AGENT_PROMPT)

    @staticmethod
    def get_grafcet_prompt():
        return PromptTemplate.from_template(GRAFCET_SYSTEM_PROMPT)