"""
Multi-Provider LLM Wrapper
Supports OpenAI, Anthropic (Claude), Google (Gemini), and Azure-hosted endpoints
"""
import json
import threading
from enum import Enum
from time import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"


class LLMModel(Enum):
    """Common model identifiers across providers"""
    # OpenAI models
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_3_5_TURBO = "gpt-3.5-turbo"

    # Anthropic models
    CLAUDE_SONNET_4 = "claude-sonnet-4-20250514"
    CLAUDE_OPUS_4 = "claude-opus-4-20250514"
    CLAUDE_SONNET_3_5 = "claude-3-5-sonnet-20241022"
    CLAUDE_HAIKU_3_5 = "claude-3-5-haiku-20241022"
    CLAUDE_OPUS_4_5 = "claude-opus-4-5-20251101"

    # Google models
    GEMINI_3_PRO_PREVIEW = "gemini-3-pro-preview"
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_0_FLASH_EXP = "gemini-2.0-flash-exp"
    GEMINI_2_0_FLASH = "gemini-2.0-flash"

    # Azure-hosted models (deployment names)
    AZURE_GPT_4O = "azure-gpt-4o"
    AZURE_GPT_4_TURBO = "azure-gpt-4-turbo"


class MultiProviderLLM:
    """
    A unified wrapper for multiple LLM providers (OpenAI, Anthropic, Google, Azure).

    Attributes:
        provider (LLMProvider): The LLM provider to use
        api_key (str): API key for the provider
        model (LLMModel): The model to use
        temperature (float): Sampling temperature
        max_tokens (int): Maximum tokens to generate
        history_enabled (bool): Enable history logging
        cast_to_json (bool): Whether to cast response to JSON
        azure_endpoint (Optional[str]): Azure endpoint URL (for Azure provider)
        azure_api_version (Optional[str]): Azure API version (for Azure provider)
    """

    def __init__(
        self,
        provider: LLMProvider,
        api_key: str,
        model: LLMModel,
        temperature: float = 0.5,
        max_tokens: int = 1000,
        history_enabled: bool = False,
        cast_to_json: bool = False,
        azure_endpoint: Optional[str] = None,
        azure_api_version: Optional[str] = "2025-11-15-preview",
        azure_deployment_name: Optional[str] = None
    ):
        """
        Initialize the multi-provider LLM wrapper.

        :param provider: The LLM provider to use
        :param api_key: API key for the provider
        :param model: The model to use
        :param temperature: Sampling temperature (0.0 to 1.0)
        :param max_tokens: Maximum tokens to generate
        :param history_enabled: Enable conversation history logging
        :param cast_to_json: Whether to parse response as JSON
        :param azure_endpoint: Azure endpoint URL (required for Azure provider)
        :param azure_api_version: Azure API version (for Azure provider)
        :param azure_deployment_name: Azure deployment name (for Azure-hosted models)
        """
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.history_enabled = history_enabled
        self.cast_to_json = cast_to_json
        self.azure_endpoint = azure_endpoint
        self.azure_api_version = azure_api_version
        self.azure_deployment_name = azure_deployment_name

        self.history = []
        self.history_lock = threading.Lock()
        self.async_threads = []
        self.async_threads_lock = threading.Lock()

        # Initialize provider-specific clients
        self._client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the appropriate client based on provider"""
        if self.provider == LLMProvider.OPENAI:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)

        elif self.provider == LLMProvider.ANTHROPIC:
            try:
                # If Azure endpoint is provided, use AnthropicFoundry client
                if self.azure_endpoint:
                    from anthropic import AnthropicFoundry

                    self._client = AnthropicFoundry(
                        api_key=self.api_key,
                        base_url=self.azure_endpoint
                    )
                else:
                    from anthropic import Anthropic
                    self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "anthropic package not installed. Run: pip install anthropic")

        elif self.provider == LLMProvider.GOOGLE:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai
            except ImportError:
                raise ImportError(
                    "google-generativeai package not installed. Run: pip install google-generativeai")

        elif self.provider == LLMProvider.AZURE:
            if not self.azure_endpoint:
                raise ValueError(
                    "azure_endpoint is required for Azure provider")
            from openai import AzureOpenAI
            self._client = AzureOpenAI(
                api_key=self.api_key,
                api_version=self.azure_api_version,
                azure_endpoint=self.azure_endpoint
            )

    def _create_messages(self, content_dict: Dict[str, str]) -> List[Dict[str, str]]:
        """Create messages list from content dictionary"""
        system_content = content_dict.get("system_content")
        user_content = content_dict.get("user_content")

        messages = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        if user_content:
            messages.append({"role": "user", "content": user_content})

        return messages

    def _clean_json_response(self, response: str) -> str:
        """Clean the response by stripping unwanted characters"""
        response = response.strip().strip("'''").strip('"""')
        if response.startswith("```json"):
            response = response[len("```json"):].strip()
        if response.endswith("```"):
            response = response[:-len("```")].strip()
        return response

    def _submit_openai(self, messages: List[Dict[str, str]], max_tokens: int) -> tuple:
        """Submit query to OpenAI"""
        chat_completion = self._client.chat.completions.create(
            messages=messages,
            max_tokens=max_tokens,
            model=self.model.value,
            temperature=self.temperature
        )

        response_content = chat_completion.choices[0].message.content if chat_completion.choices else ""
        provider_id = chat_completion.id
        provider_model = chat_completion.model
        usage = {
            "completion_tokens": chat_completion.usage.completion_tokens,
            "prompt_tokens": chat_completion.usage.prompt_tokens,
            "total_tokens": chat_completion.usage.total_tokens
        } if chat_completion.usage else {}

        return response_content, provider_id, provider_model, usage

    def _submit_anthropic(self, messages: List[Dict[str, str]], max_tokens: int) -> tuple:
        """Submit query to Anthropic (or Azure-hosted Anthropic via AnthropicFoundry)"""
        # Both standard Anthropic and AnthropicFoundry use the same API format
        # Separate system message from messages array
        system_content = None
        anthropic_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                anthropic_messages.append(msg)

        # Use deployment name if provided (for Azure), otherwise use model name
        model_name = self.azure_deployment_name if self.azure_deployment_name else self.model.value

        kwargs = {
            "model": model_name,
            "max_tokens": max_tokens,
            "temperature": self.temperature,
            "messages": anthropic_messages
        }

        if system_content:
            kwargs["system"] = system_content

        response = self._client.messages.create(**kwargs)

        response_content = response.content[0].text if response.content else ""
        provider_id = response.id
        provider_model = response.model
        usage = {
            "completion_tokens": response.usage.output_tokens,
            "prompt_tokens": response.usage.input_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens
        }

        return response_content, provider_id, provider_model, usage

    def _submit_google(self, messages: List[Dict[str, str]], max_tokens: int) -> tuple:
        """Submit query to Google"""
        # Combine system and user messages for Gemini
        prompt_parts = []
        for msg in messages:
            if msg["role"] == "system":
                prompt_parts.append(f"System: {msg['content']}")
            else:
                prompt_parts.append(msg["content"])

        prompt = "\n\n".join(prompt_parts)

        model = self._client.GenerativeModel(self.model.value)
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": self.temperature,
                "max_output_tokens": max_tokens
            }
        )

        response_content = response.text if hasattr(response, 'text') else ""
        provider_id = "google-generated"
        provider_model = self.model.value

        # Google doesn't provide detailed token usage in the same way
        usage = {
            "completion_tokens": response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0,
            "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
            "total_tokens": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0
        }

        return response_content, provider_id, provider_model, usage

    def _submit_azure(self, messages: List[Dict[str, str]], max_tokens: int) -> tuple:
        """Submit query to Azure OpenAI"""
        # Azure uses OpenAI client with deployment name
        chat_completion = self._client.chat.completions.create(
            messages=messages,
            max_tokens=max_tokens,
            # Remove azure- prefix for deployment name
            model=self.model.value.replace("azure-", ""),
            temperature=self.temperature
        )

        response_content = chat_completion.choices[0].message.content if chat_completion.choices else ""
        provider_id = chat_completion.id
        provider_model = chat_completion.model
        usage = {
            "completion_tokens": chat_completion.usage.completion_tokens,
            "prompt_tokens": chat_completion.usage.prompt_tokens,
            "total_tokens": chat_completion.usage.total_tokens
        } if chat_completion.usage else {}

        return response_content, provider_id, provider_model, usage

    def _create_response_entry(
        self,
        response_content: str,
        success: bool,
        error_message: Optional[str],
        start_time: float,
        provider_id: Optional[str],
        provider_model: Optional[str],
        usage: Optional[Dict[str, int]],
        cast_to_json: bool
    ) -> Dict[str, Any]:
        """Create standardized response entry"""
        end_time = time()
        response_time = datetime.now(timezone.utc).isoformat()
        duration_seconds = end_time - start_time

        result_json = None
        if cast_to_json:
            try:
                response_content = self._clean_json_response(response_content)
                result_json = json.loads(response_content)
            except json.JSONDecodeError as e:
                success = False
                error_message = f"JSON decode error: {str(e)}"

        return {
            "time": response_time,
            "duration_seconds": duration_seconds,
            "success": success,
            "error": error_message,
            "provider": self.provider.value,
            "provider_id": provider_id,
            "provider_model": provider_model,
            "tokens": usage,
            "result": response_content,
            "result_json": result_json
        }

    def submit_query(
        self,
        content_dict: Dict[str, str],
        max_tokens: Optional[int] = None,
        request_id: Optional[str] = None,
        model: Optional[LLMModel] = None,
        cast_to_json: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Submit a query to the configured LLM provider.

        :param content_dict: Dictionary with 'system_content' and/or 'user_content'
        :param max_tokens: Override max tokens for this request
        :param request_id: Optional request ID for tracking
        :param model: Override model for this request
        :param cast_to_json: Override cast_to_json for this request
        :return: Dictionary with request and response details
        """
        chosen_model = model if model is not None else self.model
        messages = self._create_messages(content_dict)
        request_time = datetime.now(timezone.utc).isoformat()
        start_time = time()
        max_tokens_used = max_tokens if max_tokens is not None else self.max_tokens
        cast_to_json_used = cast_to_json if cast_to_json is not None else self.cast_to_json

        try:
            # Route to appropriate provider
            if self.provider == LLMProvider.OPENAI:
                response_content, provider_id, provider_model, usage = self._submit_openai(
                    messages, max_tokens_used)
            elif self.provider == LLMProvider.ANTHROPIC:
                response_content, provider_id, provider_model, usage = self._submit_anthropic(
                    messages, max_tokens_used)
            elif self.provider == LLMProvider.GOOGLE:
                response_content, provider_id, provider_model, usage = self._submit_google(
                    messages, max_tokens_used)
            elif self.provider == LLMProvider.AZURE:
                response_content, provider_id, provider_model, usage = self._submit_azure(
                    messages, max_tokens_used)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            success = True
            error_message = None

        except Exception as e:
            import traceback
            response_content = ""
            success = False
            error_message = str(e)
            provider_id = None
            provider_model = None
            usage = None

            # Print detailed error for debugging
            print(f"ERROR in submit_query for {self.provider.value}:")
            print(f"  Error: {error_message}")
            print(f"  Traceback:")
            traceback.print_exc()

        response_entry = self._create_response_entry(
            response_content, success, error_message, start_time,
            provider_id, provider_model, usage, cast_to_json_used
        )

        full_entry = {
            "id": request_id,
            "request": {
                "time": request_time,
                "provider": self.provider.value,
                "model": chosen_model.value,
                "max_tokens": max_tokens_used,
                "temperature": self.temperature,
                "cast_to_json": cast_to_json_used,
                "messages": messages
            },
            "response": response_entry
        }

        if self.history_enabled:
            with self.history_lock:
                self.history.append(full_entry)

        return full_entry

    def async_submit_query(
        self,
        content_dict: Dict[str, str],
        callback: Callable[[Dict[str, Any]], None],
        max_tokens: Optional[int] = None,
        request_id: Optional[str] = None,
        model: Optional[LLMModel] = None,
        cast_to_json: Optional[bool] = None
    ):
        """
        Submit a query asynchronously and call callback with result.

        :param content_dict: Dictionary with 'system_content' and/or 'user_content'
        :param callback: Function to call with the result
        :param max_tokens: Override max tokens for this request
        :param request_id: Optional request ID for tracking
        :param model: Override model for this request
        :param cast_to_json: Override cast_to_json for this request
        """
        def run_query():
            result = self.submit_query(
                content_dict, max_tokens, request_id, model, cast_to_json)
            callback(result)
            with self.async_threads_lock:
                self.async_threads.remove(threading.current_thread())

        thread = threading.Thread(target=run_query)
        with self.async_threads_lock:
            self.async_threads.append(thread)
        thread.start()

    def wait_on_all_async(self):
        """Wait for all asynchronous queries to complete"""
        while True:
            with self.async_threads_lock:
                if not self.async_threads:
                    break
                for thread in self.async_threads:
                    thread.join(0.1)

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history"""
        if self.history_enabled:
            with self.history_lock:
                return list(self.history)
        else:
            raise ValueError(
                "History is disabled. Enable history to get conversation history.")

    def reset_conversation(self):
        """Reset the conversation history"""
        if self.history_enabled:
            with self.history_lock:
                self.history = []
        else:
            raise ValueError(
                "History is disabled. Enable history to reset conversation.")
