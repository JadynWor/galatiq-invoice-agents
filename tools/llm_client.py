import os
from openai import OpenAI


class LLMClient:
    """Wrapper around OpenAI API with token tracking and error handling."""

    def __init__(self, api_key=None, model=None):
        # Load API key from param or environment
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key must be provided via parameter or OPENAI_API_KEY environment variable.")
        
        # Initialize the OpenAI client
        self.client = OpenAI(api_key=self.api_key)
        # Set up token tracking dict
        self.model = model or "gpt-4o-mini"
        self.token_usage = {"prompt": 0, "completion": 0, "total": 0}

    def call(self, system_prompt, user_prompt, json_mode=False):
        # Build the messages list

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Make the API call (with try/except)
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,                
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            response = self.client.chat.completions.create(**kwargs)

            self.token_usage["prompt"] += response.usage.prompt_tokens
            self.token_usage["completion"] += response.usage.completion_tokens
            self.token_usage["total"] += response.usage.total_tokens
            return text.strip() if (text := response.choices[0].message.content) else None
        except Exception as e:
            print(f"Error during LLM call: {e}")
            return None