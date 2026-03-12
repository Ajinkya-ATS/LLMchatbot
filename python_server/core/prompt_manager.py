from langchain_core.prompts import PromptTemplate

class PromptManager:

    @staticmethod
    def get_react_prompt(): # React means reason + acting
        template = """
            Answer the following questions as best you can. You have access to the following tools:

            {tools}

            Use the following format:

            Question: the input question you must answer
            Thought: you should always think about what to do
            Action: the action to take, should be one of [{tool_names}]
            Action Input: the input to the action
            Observation: the result of the action
            ... (this can repeat N times)
            Thought: I now know the final answer
            Final Answer: the final answer to the original input question

            Begin!

            Question: {input}
            Thought:{agent_scratchpad}
            """
        # The above prompt is from langchain examples (hwchase17/react)
        return PromptTemplate.from_template(template)