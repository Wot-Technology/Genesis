import json
import threading
from enum import Enum
from time import sleep, time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone

from openai import OpenAI


class ModelEnum(Enum):
    # Speech-to-text model
    WHISPER_1 = 'whisper-1'

    # Image generation models
    DALL_E_2 = 'dall-e-2'
    DALL_E_3 = 'dall-e-3'

    # Text-to-speech models
    TTS_1 = 'tts-1'
    TTS_1_HD = 'tts-1-hd'
    TTS_1_1106 = 'tts-1-1106'
    TTS_1_HD_1106 = 'tts-1-hd-1106'

    # GPT-3.5 models
    GPT_3_5_TURBO = 'gpt-3.5-turbo'
    GPT_3_5_TURBO_16K = 'gpt-3.5-turbo-16k'
    GPT_3_5_TURBO_0125 = 'gpt-3.5-turbo-0125'
    GPT_3_5_TURBO_1106 = 'gpt-3.5-turbo-1106'
    GPT_3_5_TURBO_INSTRUCT = 'gpt-3.5-turbo-instruct'
    GPT_3_5_TURBO_INSTRUCT_0914 = 'gpt-3.5-turbo-instruct-0914'

    # GPT-4 models
    GPT_4 = 'gpt-4'
    GPT_4_0314 = 'gpt-4-0314'
    GPT_4_0613 = 'gpt-4-0613'
    GPT_4_0125_PREVIEW = 'gpt-4-0125-preview'
    GPT_4_1106_PREVIEW = 'gpt-4-1106-preview'
    GPT_4_TURBO = 'gpt-4-turbo'
    GPT_4_TURBO_PREVIEW = 'gpt-4-turbo-preview'
    GPT_4_TURBO_2024_04_09 = 'gpt-4-turbo-2024-04-09'
    GPT_4_32K_0314 = 'gpt-4-32k-0314'
    GPT_4_TURBO_WITH_VISION = 'gpt-4-turbo-with-vision'

    # Optimized GPT-4 models
    GPT_4O = 'gpt-4o'
    GPT_4O_2024_05_13 = 'gpt-4o-2024-05-13'
    GPT_4O_MINI = 'gpt-4o-mini'

    # Embedding models
    TEXT_EMBEDDING_ADA_002 = 'text-embedding-ada-002'
    TEXT_EMBEDDING_3_SMALL = 'text-embedding-3-small'
    TEXT_EMBEDDING_3_LARGE = 'text-embedding-3-large'

    # Moderation model
    TEXT_MODERATION_UPDATED_2024 = 'text-moderation-updated-2024'

    # Specialized models
    BABBAGE_002 = 'babbage-002'
    DAVINCI_002 = 'davinci-002'

    # New reasoning and multimodal models
    OPENAI_O1 = 'openai-o1'
    OPENAI_O1_MINI = 'openai-o1-mini'


class AIWrapper:
    """
    A class to interact with OpenAI's GPT models.

    Attributes:
        key (str): API key for OpenAI.
        model (ModelEnum): The model to use from ModelEnum.
        temperature (float): Sampling temperature.
        top_p (float): Nucleus sampling probability.
        max_tokens (Optional[int]): Maximum number of tokens to generate.
        history_enabled (bool): Enable history logging.
        cast_to_json (bool): Whether to cast the response to JSON.
        history (List[Dict[str, Any]]): List to store conversation history.
        history_lock (threading.Lock): Lock for thread-safe history operations.
        client (OpenAI): OpenAI client instance.
        async_threads (List[threading.Thread]): List to track running threads.
        async_threads_lock (threading.Lock): Lock for thread-safe thread operations.
    """

    def __init__(self, key: str, model: ModelEnum = ModelEnum.GPT_4O, temperature: float = 0.5,
                 top_p: float = 1.0, history_enabled: bool = False, max_tokens: Optional[int] = 300,
                 cast_to_json: bool = False):
        """
        Initialize the GPT model with the given parameters.

        :param key: API key for OpenAI.
        :param model: The model to use from ModelEnum.
        :param temperature: Sampling temperature.
        :param top_p: Nucleus sampling probability.
        :param history_enabled: Enable history logging.
        :param max_tokens: Maximum number of tokens to generate.
        :param cast_to_json: Whether to cast the response to JSON.
        """
        self.key = key
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.history_enabled = history_enabled
        self.max_tokens = max_tokens
        self.cast_to_json = cast_to_json
        self.history = []
        self.history_lock = threading.Lock()  # Lock for thread-safe history operations
        self.async_threads = []
        # Lock for thread-safe thread operations
        self.async_threads_lock = threading.Lock()

        self.client = OpenAI(api_key=self.key)

    def _create_messages(self, content_dict: Dict[str, str]) -> List[Dict[str, str]]:
        system_content = content_dict.get("system_content")
        user_content = content_dict.get("user_content")

        messages = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        if user_content:
            messages.append({"role": "user", "content": user_content})

        return messages

    def _clean_json_response(self, response: str) -> str:
        """ Clean the GPT response by stripping unwanted characters. """
        response = response.strip().strip("'''").strip('"""')
        if response.startswith("```json"):
            response = response[len("```json"):].strip()
        if response.endswith("```"):
            response = response[:-len("```")].strip()
        return response

    def _create_response_entry(self, response_content: str, success: bool, error_message: Optional[str], start_time: float,
                               openai_id: Optional[str], openai_model: Optional[str], usage: Optional[Dict[str, int]], cast_to_json: bool) -> Dict[str, Any]:
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
                error_message = str(e)

        response_entry = {
            "time": response_time,
            "duration_seconds": duration_seconds,
            "success": success,
            "error": error_message,
            "openai_id": openai_id,
            "openai_model": openai_model,
            "tokens": usage,
            "result": response_content,
            "result_json": result_json
        }

        return response_entry

    def submit_query(self, content_dict: Dict[str, str], max_tokens: Optional[int] = None, request_id: Optional[str] = None,
                     model: Optional[ModelEnum] = None, cast_to_json: Optional[bool] = None) -> Dict[str, Any]:
        """
        Submit a query to the GPT model.

        :param content_dict: Dictionary containing system and user content.
        :param max_tokens: Maximum number of tokens to generate.
        :param request_id: Optional request ID for tracking purposes.
        :param model: Optional model to override the instance's default model.
        :param cast_to_json: Optional boolean to override the instance's default cast_to_json setting.
        :return: Dictionary containing the ID, request, and response with status, result, and timing information.
        """
        chosen_model = model if model is not None else self.model
        messages = self._create_messages(content_dict)
        request_time = datetime.now(timezone.utc).isoformat()
        start_time = time()
        max_tokens_used = max_tokens if max_tokens is not None else self.max_tokens
        cast_to_json_used = cast_to_json if cast_to_json is not None else self.cast_to_json

        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                max_tokens=int(max_tokens_used),
                model=chosen_model.value,
                temperature=self.temperature,
                top_p=self.top_p
            )

            response_content = chat_completion.choices[0].message.content if chat_completion.choices else ""
            success = True
            error_message = None
            openai_id = chat_completion.id
            openai_model = chat_completion.model
            usage = {
                "completion_tokens": chat_completion.usage.completion_tokens,
                "prompt_tokens": chat_completion.usage.prompt_tokens,
                "total_tokens": chat_completion.usage.total_tokens
            } if chat_completion.usage else {}
        except Exception as e:
            response_content = ""
            success = False
            error_message = str(e)
            openai_id = None
            openai_model = None
            usage = None

        response_entry = self._create_response_entry(response_content, success, error_message, start_time,
                                                     openai_id, openai_model, usage, cast_to_json_used)

        full_entry = {
            "id": request_id,
            "request": {
                "time": request_time,
                "model": chosen_model.value,
                "max_tokens": max_tokens_used,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "cast_to_json": cast_to_json_used,
                "messages": messages
            },
            "response": response_entry
        }

        if self.history_enabled:
            with self.history_lock:
                self.history.append(full_entry)

        return full_entry

    def async_submit_query(self, content_dict: Dict[str, str], callback: Callable[[Dict[str, Any]], None],
                           max_tokens: Optional[int] = None, request_id: Optional[str] = None,
                           model: Optional[ModelEnum] = None, cast_to_json: Optional[bool] = None):
        """
        Submit a query to the GPT model asynchronously and call the provided callback function with the result.

        :param content_dict: Dictionary containing system and user content.
        :param callback: Callback function to call with the result.
        :param max_tokens: Maximum number of tokens to generate.
        :param request_id: Optional request ID for tracking purposes.
        :param model: Optional model to override the instance's default model.
        :param cast_to_json: Optional boolean to override the instance's default cast_to_json setting.
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
        """
        Wait for all asynchronous queries to complete.
        """
        while True:
            with self.async_threads_lock:
                if not self.async_threads:
                    break
                for thread in self.async_threads:
                    thread.join(0.1)

    def set_model(self, model: ModelEnum):
        """
        Set the model for the GPT instance.

        :param model: The model to use from ModelEnum.
        """
        self.model = model

    def set_temperature(self, temperature: float):
        """
        Set the temperature for the GPT instance.

        :param temperature: Sampling temperature.
        """
        self.temperature = temperature

    def set_top_p(self, top_p: float):
        """
        Set the top_p for the GPT instance.

        :param top_p: Nucleus sampling probability.
        """
        self.top_p = top_p

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get the conversation history.

        :return: List of dictionaries containing the conversation history.
        """
        if self.history_enabled:
            with self.history_lock:
                return list(self.history)
        else:
            raise ValueError(
                "History is disabled. Enable history to get the conversation history.")

    def reset_conversation(self):
        """
        Reset the conversation history.
        """
        if self.history_enabled:
            with self.history_lock:
                self.history = []
        else:
            raise ValueError(
                "History is disabled. Enable history to reset the conversation.")
