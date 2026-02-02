#!/usr/bin/env python
# Ensures that the script runs with the virtual environment's Python interpreter.

from builtins import str
import random
import re
from common.setup.Setup import ScriptSetup
from common.Log import LogType
from common.ai.OpenAI import AIWrapper, ModelEnum
from common.ai.MultiProviderLLM import MultiProviderLLM, LLMProvider, LLMModel

import os
import pandas as pd
import json
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from common.API import APIClient
from common.Config import ConfigLoader
from common.Log import Logger2, LogLevel, LogType
from common.AzureCommon import AzureHelper, AzureBlobUploader
from common.AuthWrapper import Auth
from common.Kinde import KindeAuth
from common.Excel import ProductExcelParser
from common.Imagery import ImageFetcherV3
from common.Requests import SafeRequest
from common.Thread import Threader
from common.GUI import Interaction
from common.State import ProductStateTracker
from common.Validate import Validator
from common.SiteMap import SiteMapBuilder
from common.Category import CategoryJSON
from common.Algolia import AlgoliaClient
from common.o365.Teams import Alerts
from common.datetime.Timing import Timer
from pprint import pprint
from copy import deepcopy

# Define the custom order for block types
layout_order = {
    "metaDescription": 1,
    "product": 2,
    "subCategories": 3,
    "faq": 4,
    "text": 5,
    "products": 6,
    "relatedProducts": 7,
    "frequentlyBoughtTogether": 8,
    "categories": 9
}

MAX_TOKENS = 16384

layout_block_types = ["text", "faq", "metaDescription", "subCategories", "product", "products",
                      "relatedProducts", "frequentlyBoughtTogether", "categories"]


def get_order_index(block):
    # Default to 99 if type is not found
    return layout_order.get(block.get("type"), 99)

# def deep_merge(dict1, dict2):
#     """
#     Recursively merge two dictionaries.
#     Values from dict2 will override those in dict1, but dict1 keys will be inherited if not present in dict2.
#     """
#     result = deepcopy(dict1)
#     for key, value in dict2.items():
#         if isinstance(value, dict) and key in result and isinstance(result[key], dict):
#             result[key] = deep_merge(result[key], value)
#         else:
#             result[key] = value
#     return result


# def deep_merge(dict1, dict2):
#     """
#     Recursively merge two dictionaries.
#     Values from dict2 will override those in dict1, but dict1 keys will be inherited if not present in dict2.
#     """
#     result = deepcopy(dict1)
#     for key, value in dict2.items():
#         if isinstance(value, dict) and key in result and isinstance(result[key], dict):
#             result[key] = deep_merge(result[key], value)
#             print(f"Merged '{key}': {result[key]}")
#         elif value is not None:
#             result[key] = value
#             print(f"Set '{key}' to: {value}")
#     print(f"Result after merging: {result}")
#     return result


def deep_merge(dict1, dict2):
    """
    Recursively merge two dictionaries.
    Values from dict2 will override those in dict1, but dict1 keys will be inherited if not present in dict2.
    """
    result = deepcopy(dict1)  # Start with a copy of dict1
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge if both are dictionaries
            result[key] = deep_merge(result[key], value)
        else:
            # Directly override or add if not a dict
            result[key] = value
    return result


def parse_time_period(time_period):
    """
    Parse a time period string (e.g., '1d', '1w', '1m') and return a timedelta object.

    :param time_period: str, the time period string.
    :return: timedelta, the corresponding timedelta object.
    """
    unit = time_period[-1]
    value = int(time_period[:-1])

    if unit == 'd':
        return timedelta(days=value)
    elif unit == 'w':
        return timedelta(weeks=value)
    elif unit == 'm':
        return timedelta(days=value * 30)  # Approximate a month as 30 days
    else:
        raise ValueError(f"Invalid time period unit: {unit}")


def create_layout_content(lvl, category, text_label="About"):
    if lvl == 1:
        layout_content = {
            "layout": [
                {
                    "title": "Meta Description",
                    "type": "metaDescription",
                    "text": "This is the meta description for the page."

                },
                {
                    "type": "subCategories"
                },
                {
                    "title": text_label + ' ' + category,
                    "type": "text",
                    "text": "This is the text content for the page."
                },
            ],
        }
    elif lvl == 2:
        layout_content = {
            "layout": [
                {
                    "title": "Meta Description",
                    "type": "metaDescription",
                    "text": "This is the meta description for the page."

                },
                {
                    "type": "subCategories"
                },
                {
                    "title": "FAQ",
                    "type": "faq",
                    "text": category
                },
                {
                    "title": text_label + ' ' + category,
                    "type": "text",
                    "text": "This is the text content for the page."
                }
            ],
        }

    elif lvl == 3:
        layout_content = {
            "layout": [
                {
                    "title": "Meta Description",
                    "type": "metaDescription",
                    "text": "This is the meta description for the page."
                },
                {
                    "title": "Products",
                    "type": "product",
                    "category": category
                },
                {
                    "title": "FAQ",
                    "type": "faq",
                    "text": category
                },
                {
                    "title": text_label + ' ' + category,
                    "type": "text",
                    "text": "This is the text content for the page."
                },
            ],
        }
    else:
        layout_content = {
            "layout": [
                {
                    "title": text_label,
                    "type": "text",
                    "text": "This is the text content for the page."
                }
            ],
        }
    return layout_content


def find_existing_description(layout, names):
    """
    Find the existing layout text block with the specified names.

    :param layout: list, the layout content.
    :param names: list, the names to search for.
    :return: str, the text of the matching block, or None if not found.
    """
    for block in layout:
        if block.get("title") in names:
            return block.get("text")
    return None


def load_existing_layout(path):
    """
    Load the existing layout.json file if it exists.
    """
    layout_file = os.path.join(path, 'layout.json')
    if os.path.exists(layout_file):
        try:
            with open(layout_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Error decoding JSON in {layout_file}. Skipping this file.")
    return None


def find_layout_block(layout_content, layout_type, layout_name):
    """
    Find the layout block with the specified type and title.

    :param layout_content: dict, the layout content.
    :param layout_type: str, the type of the layout block.
    :param layout_name: str, the title of the layout block.
    :return: dict, the matching layout block, or None if not found.
    """
    for block in layout_content.get("layout", []):
        if "About" in layout_name:
            if "About" in block.get("title", ""):
                return block
        elif block.get("title") == layout_name:
            return block
    return None


def delete_key_from_json(data, key_to_delete):
    """
    Recursively search for a specific key in a JSON object and delete it.

    :param data: dict or list, the JSON object to search.
    :param key_to_delete: str, the key to delete.
    :return: Modified data with the specified key deleted.
    """
    if isinstance(data, dict):
        # Create a new dictionary excluding the key to delete
        return {
            key: delete_key_from_json(value, key_to_delete)
            for key, value in data.items()
            if key != key_to_delete
        }
    elif isinstance(data, list):
        # Process each item in the list
        return [delete_key_from_json(item, key_to_delete) for item in data]
    else:
        # Base case: Non-iterable types are returned as is
        return data


def generate_prompt(prompts, context, prompt_type, title=None, setup=None):
    """
    Generate an OpenAI-ready prompt from a prompts.json structure, a context dictionary, and a prompt type.

    :param prompts: dict, the parsed prompts.json structure.
    :param context: dict, the context with placeholders for the prompt.
    :param prompt_type: str, the type of prompt to generate (e.g., "metaDescription").
    :param title: str, the specififc title to use within the prompt type (optional).
    :param setup: ScriptSetup instance for logging (optional).
    :return: str, the final prompt ready for OpenAI API execution.
    """
    if prompt_type not in prompts:
        raise ValueError(
            f"Prompt type '{prompt_type}' not found in the prompts.json.")

    title = 'About' if 'About' in title else title
    # Fetch the prompt details
    prompt_data = prompts[prompt_type]
    default_prompt_data = prompt_data.get("default", {})
    named_prompt_data = prompt_data.get(
        "titles", {}).get(title, {}) if title else {}

    # Use the named prompt if it exists, otherwise fall back to the default prompt
    prompt_details = named_prompt_data if named_prompt_data else default_prompt_data

    default_prompt = prompt_details.get("default", "")
    guidelines = prompt_details.get("guidelines", {})
    input_context = prompt_details.get("inputContext", {})
    example = prompt_details.get("example", {})

    # Start building the prompt
    final_prompt = f"### Task\n{default_prompt}\n\n"

    # Add context if available
    if "category_name" in context or "category_description" in context:
        final_prompt += "### Context\n"
        if "category_name" in context:
            final_prompt += f"- Category Name: {context['category_name']}\n"
        if "category_description" in context:
            final_prompt += f"- Description: {
                context['category_description']}\n"
        final_prompt += "\n"

    # Note: Domain Knowledge sections are now explicitly referenced in prompts.json inputContext
    # via {section_name} variable substitution. This ensures clear, explicit control over
    # what context is included and avoids duplicate content in prompts.

    # Add input context if available
    if input_context:
        final_prompt += "### Input Context\n"
        for key, value in input_context.items():
            if value not in [None, "", "null"]:
                key = key.replace("_", " ").capitalize()
                final_prompt += f"- {key}: {value}\n"
        final_prompt += "\n\n"

    # Add guidelines if available
    if guidelines:
        final_prompt += "### Guidelines\n"
        for key, value in guidelines.items():
            # Check for None, empty string, or JSON null
            if value not in [None, "", "null"]:
                if isinstance(value, dict):  # Handle nested guidelines like "structure"
                    key = key.replace("_", " ").capitalize()
                    final_prompt += f"- {key}:\n"
                    for sub_key, sub_value in value.items():
                        # Check for None, empty string, or JSON null
                        if sub_value not in [None, "", "null"]:
                            sub_key = sub_key.replace("_", " ").capitalize()
                            final_prompt += f"  - {sub_key}: {sub_value}\n"
                else:
                    final_prompt += f"- {key.capitalize()}: {value}\n"
        final_prompt += "\n"

    # Add example if available
    if example:
        final_prompt += "### Example\n"
        if "inputContext" in example:
            final_prompt += "#### Input\n"
            for key, value in example["inputContext"].items():
                if value not in [None, "", "null"]:
                    key = key.replace("_", " ").capitalize()
                    final_prompt += f"- {key}: {value}\n"
            final_prompt += "\n"
        if "output" in example:
            final_prompt += f"#### Output\n{example['output']}\n"

    for placeholder, value in context.items():
        # Skip context_sections as it's handled separately below
        if placeholder != 'context_sections':
            final_prompt = final_prompt.replace(
                f"{{{placeholder}}}", str(value))

    # Handle variable substitution from context.md sections
    # Find all {variable_name} patterns and replace with content from ## variable_name sections
    if 'context_sections' in context:
        context_sections = context['context_sections']

        # Find all {variable_name} patterns in the prompt
        # Pattern matches alphanumeric, spaces, underscores, hyphens, and ampersands
        variable_pattern = r'\{([a-zA-Z0-9 _&-]+)\}'
        matches = re.finditer(variable_pattern, final_prompt)

        # Track which variables we've processed to avoid duplicate replacements
        replaced_vars = set()
        missing_vars = set()

        for match in matches:
            variable_name = match.group(1)

            # Skip if we already processed this variable
            if variable_name in replaced_vars or variable_name in missing_vars:
                continue

            # Look up the section in context_sections
            if variable_name in context_sections:
                section_content = context_sections[variable_name]
                final_prompt = final_prompt.replace(
                    f"{{{variable_name}}}", section_content)
                replaced_vars.add(variable_name)
                if setup:
                    setup.logger(
                        f"Replaced variable {{{variable_name}}} with content from context.md section", log_type=LogType.DEBUG)
            else:
                missing_vars.add(variable_name)
                if setup:
                    setup.logger(
                        f"Warning: Variable {{{variable_name}}} not found in context.md sections", log_type=LogType.WARNING)

    return final_prompt


def main():

    default_args = [
        {'name': '--environment', 'type': str, 'required': False,
            'help': 'The environment to use for configuration settings, choose from QA, RC, DEV, PROD.'},
        {'name': '--enable-schedule', 'action': 'store_true',
            'help': 'Enable scheduling of the script. If set, the script will be scheduled to run at the specified time.'},
        {'name': '--remove-schedule', 'action': 'store_true',
            'help': 'Set to remove scheduling of the script. If set, any existing scheduling for the script will be removed.'}
    ]

    # Add additional arguments here, using the format established above.
    additional_args = [
        {'name': '--resetAll', 'action': 'store_true',
            'help': 'If set, the script will overwrite all existing layout.json files and reset their content to default templates.'},
        {'name': '--targetLevel', 'type': str, 'choices': ['lvl1', 'lvl2', 'lvl3'],
         'help': 'Specify a target level (e.g., lvl1, lvl2, lvl3) for processing prompts and layout files.'},
        {'name': '--logUsedPrompts', 'action': 'store_true', 'default': True,
         'help': 'If set, logs all the prompt files used and their precedence during the script execution.'},
        {'name': '--validateLayout', 'action': 'store_true',
         'help': 'Validate the existing layout.json files for required fields and proper structure.'},
        {'name': '--sortLayout', 'action': 'store_true',
         'help': 'Modify the existing layout.json files to encoded order.'},
        {'name': '--basePath', 'type': str, 'required': False,
         'help': 'Manually specify the base path for category layout.json files instead of using the default from config.'},
        {'name': '--mergeOnly', 'action': 'store_true',
         'help': 'Only merge the hierarchy of prompts.json files without generating or modifying layout.json files.'},
        {'name': '--createType', "choices": [
            'text', 'faq', 'metaDescription', 'subCategories', 'product', 'products', 'relatedProducts', 'frequentlyBoughtTogether', 'categories'],
            "help": 'Specify the type of block to create in existing layout files.'},
        {'name': '--timePeriod', 'type': str, 'default': '0d',
         'help': 'Specify the time period for the lastUpdated check (e.g., 1d, 1w, 1m). Default is 2d.'},
        {'name': '--category', 'type': str, 'default': '',
         'help': 'Specify a specific category to operate on. If set, only the specified category will be processed.'},
        {'name': '--excelFilePath', 'type': str, 'required': False,
         'help': 'Optional path to the Excel file to use as input.'},
        {'name': '--categoryBaseLevel', 'type': str, 'default': '',
                 'help': 'Specify a specific base level category to operate on, i.e. ''Building Materials''. If set, only the specified category will be processed. This is a text match on level 1 and level 2 category names.'},
        {'name': '--llm-provider', 'type': str, 'choices': ['openai', 'anthropic', 'google', 'azure'], 'default': 'openai',
         'help': 'LLM provider to use (openai, anthropic, google, azure). Default: openai'},
        {'name': '--llm-model', 'type': str, 'required': False,
         'help': 'Model name to use (e.g., gpt-4o, claude-sonnet-4-20250514, gemini-2.0-flash-exp). If not specified, uses provider default.'},
        {'name': '--llm-api-key', 'type': str, 'required': False,
         'help': 'API key for the LLM provider. If not specified, uses key from config.'},
        {'name': '--azure-endpoint', 'type': str, 'required': False,
         'help': 'Azure endpoint URL (required only for Azure provider).'},
        {'name': '--azure-api-version', 'type': str, 'default': '2025-11-15-preview',
         'help': 'Azure API version. Default: 2025-11-15-preview'},
        {'name': '--azure-deployment-name', 'type': str, 'required': False,
         'help': 'Azure deployment name (for Azure-hosted models, e.g., "claude-opus-4-5"). If not specified, uses the model name.'},
    ]

    '''
    '/Users/keif/Library/CloudStorage/OneDrive-BuyMaterials/General - Development + Product/Product Data/Twenty-Seventh Pass - 20241111.xlsx'
    '''

    setup = ScriptSetup(additional_args=additional_args,
                        description='This script automates taking content from the product list, and then generating AI content for the website.')
    setup.setup_environment()
    setup.display_warnings()
    setup.setup_scheduler()

    reset_all = setup.args.resetAll
    merge_only = setup.args.mergeOnly
    log_used_prompts = setup.args.logUsedPrompts
    target_level = setup.args.targetLevel
    validate_layout = setup.args.validateLayout
    sort_layout = setup.args.sortLayout
    time_period = setup.args.timePeriod
    create_type = setup.args.createType or ['text', 'faq', 'metaDescription']
    specific_category = setup.args.category
    base_category_name = setup.args.categoryBaseLevel

    if not setup.args.excelFilePath:
        excel_file = Interaction.select_file()
    else:
        excel_file = setup.args.excelFilePath

    timer = Timer()

    # Initialize LLM provider based on command-line arguments
    llm_provider_str = setup.args.llm_provider if hasattr(
        setup.args, 'llm_provider') else 'openai'
    llm_provider = LLMProvider(llm_provider_str)

    setup.logger(
        f"DEBUG: LLM Provider: {llm_provider_str}", log_type=LogType.DEBUG)
    setup.logger(
        f"DEBUG: Environment: {setup.args.environment if hasattr(setup.args, 'environment') and setup.args.environment else 'default'}", log_type=LogType.DEBUG)

    # Determine API key
    if hasattr(setup.args, 'llm_api_key') and setup.args.llm_api_key:
        api_key = setup.args.llm_api_key
        setup.logger(f"DEBUG: Using API key from command line args",
                     log_type=LogType.DEBUG)
    else:
        # Fallback to config based on provider
        config_key_map = {
            'openai': 'openAI.key',
            'anthropic': 'anthropic.key',
            'google': 'google.key',
            'azure': 'azure.key'
        }
        config_key = config_key_map.get(llm_provider_str, 'openAI.key')
        api_key = setup.config_loader.get_setting(config_key)
        setup.logger(
            f"DEBUG: Looking for API key at config path: {config_key}", log_type=LogType.DEBUG)
        setup.logger(
            f"DEBUG: API key found: {'Yes' if api_key else 'No'}", log_type=LogType.DEBUG)

        # Special case: For Anthropic, check if Azure-hosted endpoint is configured
        # If so, use the Azure Anthropic key instead
        if llm_provider_str == 'anthropic':
            azure_anthropic_key = setup.config_loader.get_setting(
                'azure.anthropic_key', default=None)
            setup.logger(
                f"DEBUG: Checking for azure.anthropic_key: {'Found' if azure_anthropic_key else 'Not found'}", log_type=LogType.DEBUG)
            if azure_anthropic_key:
                api_key = azure_anthropic_key
                setup.logger(f"DEBUG: Using Azure Anthropic key",
                             log_type=LogType.DEBUG)

    # Determine model
    if hasattr(setup.args, 'llm_model') and setup.args.llm_model:
        # User specified a custom model string
        model_str = setup.args.llm_model
        # Try to find matching LLMModel enum, or use custom value
        try:
            model = LLMModel(model_str)
        except ValueError:
            # Custom model not in enum, create temporary enum-like value
            setup.logger(
                f"Using custom model: {model_str}", log_type=LogType.WARNING)
            # For custom models, we'll need to pass the string directly
            model = type('CustomModel', (), {'value': model_str})()
    else:
        # Use provider defaults
        default_models = {
            LLMProvider.OPENAI: LLMModel.GPT_4O,
            LLMProvider.ANTHROPIC: LLMModel.CLAUDE_SONNET_3_5,
            LLMProvider.GOOGLE: LLMModel.GEMINI_2_0_FLASH,
            LLMProvider.AZURE: LLMModel.AZURE_GPT_4O
        }
        model = default_models.get(llm_provider, LLMModel.GPT_4O)

    # Initialize the appropriate wrapper
    use_legacy_wrapper = llm_provider == LLMProvider.OPENAI and not (
        hasattr(setup.args, 'llm_provider') and setup.args.llm_provider != 'openai')

    if use_legacy_wrapper:
        # Use legacy AIWrapper for backward compatibility with OpenAI-only code
        setup.logger("Using legacy OpenAI wrapper", log_type=LogType.INFO)
        ai_wrapper = AIWrapper(
            key=api_key,
            temperature=0.5,
            max_tokens=MAX_TOKENS,
            top_p=1.0,
            history_enabled=True,
            cast_to_json=False,
            model=ModelEnum(model.value) if hasattr(
                model, 'value') else ModelEnum.GPT_4O
        )
    else:
        # Use new multi-provider wrapper
        setup.logger(
            f"Using multi-provider LLM wrapper: {llm_provider.value} with model {model.value if hasattr(model, 'value') else 'custom'}", log_type=LogType.INFO)

        # Get Azure endpoint from args or config
        if hasattr(setup.args, 'azure_endpoint') and setup.args.azure_endpoint:
            azure_endpoint = setup.args.azure_endpoint
            setup.logger(
                f"DEBUG: Using Azure endpoint from command line: {azure_endpoint}", log_type=LogType.DEBUG)
        else:
            # For Azure provider or Anthropic on Azure, pull from config
            if llm_provider == LLMProvider.AZURE:
                azure_endpoint = setup.config_loader.get_setting(
                    'azure.endpoint')
                setup.logger(
                    f"DEBUG: Azure provider - endpoint from config: {azure_endpoint}", log_type=LogType.DEBUG)
            elif llm_provider == LLMProvider.ANTHROPIC:
                # Check if using Azure-hosted Anthropic
                azure_endpoint = setup.config_loader.get_setting(
                    'azure.anthropic_endpoint', default=None)
                setup.logger(
                    f"DEBUG: Anthropic provider - checking azure.anthropic_endpoint: {azure_endpoint}", log_type=LogType.DEBUG)
            else:
                azure_endpoint = None
                setup.logger(
                    f"DEBUG: No Azure endpoint needed for provider: {llm_provider}", log_type=LogType.DEBUG)

        azure_api_version = setup.args.azure_api_version if hasattr(
            setup.args, 'azure_api_version') else '2024-08-01-preview'
        setup.logger(
            f"DEBUG: Azure API version: {azure_api_version}", log_type=LogType.DEBUG)

        # Get Azure deployment name if specified
        azure_deployment_name = None
        if hasattr(setup.args, 'azure_deployment_name') and setup.args.azure_deployment_name:
            azure_deployment_name = setup.args.azure_deployment_name
            setup.logger(
                f"DEBUG: Azure deployment name from args: {azure_deployment_name}", log_type=LogType.DEBUG)
        else:
            setup.logger(f"DEBUG: No Azure deployment name specified",
                         log_type=LogType.DEBUG)

        ai_wrapper = MultiProviderLLM(
            provider=llm_provider,
            api_key=api_key,
            model=model if isinstance(model, LLMModel) else LLMModel.GPT_4O,
            temperature=0.5,
            max_tokens=MAX_TOKENS,
            history_enabled=True,
            cast_to_json=False,
            azure_endpoint=azure_endpoint,
            azure_api_version=azure_api_version,
            azure_deployment_name=azure_deployment_name
        )

    args_dict = vars(setup.args)
    for key, value in args_dict.items():
        # Don't log API keys
        if 'key' in key.lower() and value:
            setup.logger(f"{key}: ***REDACTED***",  log_type=LogType.DEBUG)
        else:
            setup.logger(f"{key}: {value}",  log_type=LogType.DEBUG)

    if not setup.args.basePath:
        base_path = setup.config_loader.get_setting(
            key_path='categories.layout_json_root')
    else:
        base_path = setup.args.basePath
    setup.logger(f"Base path: {base_path}", log_type=LogType.DEBUG)

    def load_prompts(base_path, target_path):
        """
        Search the hierarchy for prompts.json files and collapse into a single dictionary.
        Files closer to the target path override those closer to the root, but inherit unset keys.
        """
        consolidated_prompts = {}

        # Collect all paths from base_path to target_path
        paths = []
        current_path = target_path
        while True:
            # Insert at the beginning to ensure root is first
            paths.insert(0, current_path)
            if os.path.abspath(current_path) == os.path.abspath(base_path):
                break
            current_path = os.path.dirname(current_path)

        # Traverse paths from root to target
        for path in paths:
            prompts_file = os.path.join(path, 'prompts.json')
            setup.logger(f"Checking for prompts file at {
                prompts_file}", log_type=LogType.DEBUG)

            if os.path.exists(prompts_file):
                try:
                    with open(prompts_file, 'r') as f:
                        prompts_data = json.load(f)

                        if prompts_data.get("override", False):
                            setup.logger(f"Override found in {
                                prompts_file}. Using this file as is.", log_type=LogType.WARN)
                            return prompts_data

                        # Deep merge: specific (consolidated so far) overrides general (current file)
                        consolidated_prompts = deep_merge(
                            consolidated_prompts, prompts_data)

                except json.JSONDecodeError:
                    setup.logger(f"Error decoding JSON in {
                        prompts_file}. Skipping this file.", log_type=LogType.ERROR)

        if not consolidated_prompts:
            setup.logger(
                f"No prompts.json files found in the hierarchy from {base_path} to {target_path}.", log_type=LogType.WARN)
            raise ValueError(
                "No prompts.json files found in the hierarchy from base path to target path.")

        return consolidated_prompts

    def load_context_markdown(base_path, target_path, filename="context.md"):
        """
        Search the hierarchy for markdown context files and merge sections.
        Lower level sections override higher level sections, with inheritance for missing sections.
        """
        def parse_markdown_sections(content):
            """Parse markdown content into sections based on ## headers."""
            sections = {}
            current_section = None
            current_content = []

            for line in content.split('\n'):
                if line.startswith('## '):
                    # Save previous section
                    if current_section:
                        sections[current_section] = '\n'.join(
                            current_content).strip()
                    # Start new section
                    current_section = line[3:].strip()  # Remove '## '
                    current_content = [line]
                elif current_section:
                    current_content.append(line)

            # Save final section
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()

            return sections

        def merge_markdown_sections(base_sections, new_sections):
            """Merge markdown sections with new sections overriding base sections."""
            merged = deepcopy(base_sections)
            for section_name, content in new_sections.items():
                merged[section_name] = content
            return merged

        def reconstruct_markdown(sections):
            """Reconstruct markdown from sections dictionary."""
            return '\n\n'.join(sections.values())

        consolidated_sections = {}

        # Collect all paths from base_path to target_path
        paths = []
        current_path = target_path
        while True:
            # Insert at the beginning to ensure root is first
            paths.insert(0, current_path)
            if os.path.abspath(current_path) == os.path.abspath(base_path):
                break
            current_path = os.path.dirname(current_path)

        # Traverse paths from root to target
        for path in paths:
            context_file = os.path.join(path, filename)
            setup.logger(f"Checking for context file at {
                context_file}", log_type=LogType.DEBUG)

            if os.path.exists(context_file):
                try:
                    with open(context_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            # Parse this file's sections
                            file_sections = parse_markdown_sections(content)

                            # Merge with consolidated sections (file sections override consolidated)
                            consolidated_sections = merge_markdown_sections(
                                consolidated_sections, file_sections)

                            setup.logger(f"Loaded and merged context from {
                                context_file}", log_type=LogType.DEBUG)

                except (IOError, UnicodeDecodeError) as e:
                    setup.logger(f"Error reading context file {
                        context_file}: {e}", log_type=LogType.ERROR)

        # Return both the full markdown and the sections dictionary
        # This allows for variable substitution from context.md sections
        return reconstruct_markdown(consolidated_sections), consolidated_sections

    def parse_categories(df):
        categories = {
            "lvl1": {},
            "lvl2": {},
            "lvl3": {}
        }

        for _, row in df.iterrows():
            lvl1 = str(row['lvl1']).strip()
            lvl2 = str(row.get('lvl2', "")).strip()
            lvl3 = str(row.get('lvl3', "")).strip()

            if lvl1 and str(lvl1) != "nan" and lvl1 not in categories["lvl1"]:
                categories["lvl1"][lvl1] = {"lvl2": {},
                                            "path": os.path.join(base_path, lvl1)}

            if lvl2 and str(lvl2) != "nan":
                if lvl2 not in categories["lvl1"][lvl1]["lvl2"]:
                    categories["lvl1"][lvl1]["lvl2"][lvl2] = {
                        "lvl3": {}, "path": os.path.join(categories["lvl1"][lvl1]["path"], lvl2)}

                if lvl3 and str(lvl3) != "nan":
                    categories["lvl1"][lvl1]["lvl2"][lvl2]["lvl3"][lvl3] = {
                        "path": os.path.join(categories["lvl1"][lvl1]["lvl2"][lvl2]["path"], lvl3)}

        return categories

    def get_random_skus(products_df, cat_name, level, num_skus=1):
        """
        Get random SKUs from a specified category and level.

        :param products_df: DataFrame, the DataFrame containing product data.
        :param cat_name: str, the name of the category to search for.
        :param level: int, the level of the category (1 to 5).
        :param num_skus: int, the number of random SKUs to return (default is 1).
        :return: list, a list of random SKUs (BMSKU) from the specified category.
        """
        # Define the category column based on the level
        cat_column = f'Cat {level}'

        # Filter the DataFrame for the specified category
        filtered_df = products_df[products_df[cat_column] == cat_name]

        # Get a list of SKUs from the filtered DataFrame
        skus = filtered_df['BMSKU'].tolist()

        # Return a random sample of SKUs
        return random.sample(skus, min(num_skus, len(skus)))

    def get_random_descriptions(categories, current_level, lvl1, lvl2=None, num_descriptions=2):
        """
        Get random descriptions from categories one level below the specified current level.

        :param categories: dict, the hierarchical structure of categories.
        :param current_level: int, the current level (1, 2, or 3).
        :param lvl1: str, the lvl1 category name.
        :param lvl2: str, the lvl2 category name (optional, required for current_level 2).
        :param num_descriptions: int, the number of random descriptions to return (default is 2).
        :return: list, a list of descriptions from random categories one level below the current level.
        """
        if current_level == 1:
            # Search for lvl2 categories under the specified lvl1 category
            lvl2_categories = list(categories["lvl1"][lvl1]["lvl2"].keys())
            random_lvl2 = random.sample(lvl2_categories, min(
                num_descriptions, len(lvl2_categories)))
            descriptions = []

            for lvl2 in random_lvl2:
                lvl2_path = categories["lvl1"][lvl1]["lvl2"][lvl2]["path"]
                layout_file = os.path.join(lvl2_path, 'layout.json')
                if os.path.exists(layout_file):
                    with open(layout_file, 'r') as f:
                        layout_data = json.load(f)
                        for block in layout_data.get("layout", []):
                            if block.get("title") in ['About', 'wordyNotForPublish']:
                                descriptions.append(block.get("text"))
                                break

        elif current_level == 2:
            # Search for lvl3 categories under the specified lvl1 and lvl2 categories
            lvl3_categories = list(
                categories["lvl1"][lvl1]["lvl2"][lvl2]["lvl3"].keys())
            random_lvl3 = random.sample(lvl3_categories, min(
                num_descriptions, len(lvl3_categories)))
            descriptions = []

            for lvl3 in random_lvl3:
                lvl3_path = categories["lvl1"][lvl1]["lvl2"][lvl2]["lvl3"][lvl3]["path"]
                layout_file = os.path.join(lvl3_path, 'layout.json')
                if os.path.exists(layout_file):
                    with open(layout_file, 'r') as f:
                        layout_data = json.load(f)
                        for block in layout_data.get("layout", []):
                            if block.get("title") in ['About', 'wordyNotForPublish']:
                                descriptions.append(block.get("text"))
                                break

        elif current_level == 3:
            # Search for lvl3 categories under the specified lvl1 and lvl2 categories
            lvl3_categories = list(
                categories["lvl1"][lvl1]["lvl2"][lvl2]["lvl3"].keys())
            random_lvl3 = random.sample(lvl3_categories, min(
                num_descriptions, len(lvl3_categories)))
            descriptions = []

            for lvl3 in random_lvl3:
                lvl3_path = categories["lvl1"][lvl1]["lvl2"][lvl2]["lvl3"][lvl3]["path"]
                layout_file = os.path.join(lvl3_path, 'layout.json')
                if os.path.exists(layout_file):
                    with open(layout_file, 'r') as f:
                        layout_data = json.load(f)
                        for block in layout_data.get("layout", []):
                            if block.get("title") in ['About', 'wordyNotForPublish']:
                                descriptions.append(block.get("text"))
                                break
        else:
            raise ValueError("Invalid current_level. Must be 1, 2 or 3.")

        return descriptions

    def get_parent_directory(path, levels_up):
        """
        Get the parent directory at a specified level up from the current path.

        :param path: str, the current path.
        :param levels_up: int, the number of levels up to go.
        :return: str, the parent directory at the specified level.
        """
        for _ in range(levels_up):
            path = os.path.dirname(path)
        return os.path.basename(path)

    def process_category(level, title, path, reset_all, merge_only, validate_layout, log_used_prompts, products_df=None, categories=None):
        if specific_category and specific_category != title:
            return

        # Load prompts.json hierarchy and collapse into single dictionary
        prompts = load_prompts(base_path, path)
        # Load markdown context hierarchy and combine into single string + sections dict
        markdown_context, context_sections = load_context_markdown(
            base_path, path)
        existing_layout = None if reset_all else load_existing_layout(path)
        product_content = None

        if existing_layout:
            # Modify existing layout if needed
            layout_content = existing_layout
            setup.logger(f"Loaded existing layout.json from {
                         path}", log_type=LogType.DEBUG)
        else:
            # Create new layout.json structure
            layout_content = create_layout_content(
                level, category=title, text_label="About")
            existing_layout = layout_content
            setup.logger(f"Creating new layout.json for {
                         path}", log_type=LogType.DEBUG)

        # Process the layout content
        placeholders = {
            "category_name": title,
            "markdown_context": markdown_context,
            "context_sections": context_sections,  # Pass sections for variable substitution
        }

        if level in [2] and categories is not None:
            # Get random descriptions from categories one level below the current level
            start_index = 1
            lvl1 = get_parent_directory(path, start_index)
            lvl2 = get_parent_directory(
                path, start_index - 1) if level == 2 else None
            random_descriptions = get_random_descriptions(
                categories, level, lvl1, lvl2, num_descriptions=2)
            setup.logger(f"Random descriptions for {title} (Level {level}): {
                         random_descriptions}", log_type=LogType.DEBUG)
            placeholders["subcategory_description"] = random_descriptions
            prompts = delete_key_from_json(prompts, "example_products")
            prompts = delete_key_from_json(prompts, "existing_description")
            random_descriptions = get_random_descriptions(
                categories, level, lvl1, lvl2, num_descriptions=2)
            placeholders["other_categories_description"] = random_descriptions

        if level in [1] and categories is not None:
            # Get random descriptions from categories one level below the current level
            start_index = 0
            lvl1 = get_parent_directory(path, start_index)
            lvl2 = None
            random_descriptions = get_random_descriptions(
                categories, level, lvl1, lvl2, num_descriptions=2)
            setup.logger(f"Random descriptions for {title} (Level {level}): {
                         random_descriptions}", log_type=LogType.DEBUG)
            placeholders["subcategory_description"] = random_descriptions
            prompts = delete_key_from_json(prompts, "example_products")
            prompts = delete_key_from_json(prompts, "existing_description")
            random_descriptions = get_random_descriptions(
                categories, level, lvl1, lvl2, num_descriptions=2)
            placeholders["other_categories_description"] = random_descriptions

        if level in [3, 4, 5] and products_df is not None:
            # Get random SKUs for the category
            random_skus = get_random_skus(
                products_df, title, level, num_skus=3)
            setup.logger(f"Random SKUs for {title} (Level {level}): {
                         random_skus}", log_type=LogType.DEBUG)

            product_content = 'The following product content is provided in json format:\n\n'
            product_success = False
            for sku in random_skus:
                get_product_response = setup.api_client.get_product(sku)
                if get_product_response["success"]:
                    product_json = get_product_response["response_json"]
                    product_content += f"{product_json}\n\n"
                    product_success = True

            if product_success:
                if product_content:
                    setup.logger(f"Product content generated for {
                        title}", log_type=LogType.DEBUG)
                    placeholders["example_products"] = product_content
                    print(product_content)
            else:
                setup.logger(f"Failed to get product content for {
                             title}", log_type=LogType.WARN)
                prompts = delete_key_from_json(prompts, "example_products")

            prompts = delete_key_from_json(prompts, "subcategory_description")

        if level in [3] and categories is not None:
            # Get random descriptions from categories one level below the current level
            lvl1 = get_parent_directory(path, 2)
            lvl2 = get_parent_directory(path, 1)
            random_descriptions = get_random_descriptions(
                categories, 2, lvl1, lvl2, num_descriptions=2)
            placeholders["other_categories_description"] = random_descriptions

        if merge_only:
            return

        if validate_layout:
            # Validate the layout content
            try:
                Validator.validate_layout(layout_content)
            except Exception as e:
                setup.logger(f"Error validating layout content for {
                             path}: {e}", LogType.ERROR)
                return
            setup.logger(f"Validated layout content for {
                         path}", log_type=LogType.INFO)
            return

        for layout_item in layout_content["layout"]:
            if layout_item.get("type") in create_type:
                layout_type = layout_item.get("type")
                if layout_type in ["faq", "metaDescription"]:
                    names_to_search = [
                        'About', 'wordyNotForPublish', 'longDescription']
                    existing_description = find_existing_description(
                        existing_layout.get("layout", []), names_to_search)

                    if existing_description:
                        setup.logger(f"Found existing description for {title} (Level {level}): {
                                     existing_description}", log_type=LogType.INFO)
                        placeholders["existing_description"] = existing_description
                    else:
                        setup.logger(f"Failed to find existing description for {title} (Level {
                                     level}): {existing_description}", log_type=LogType.WARN)
                        prompts = delete_key_from_json(
                            prompts, "existing_description")

                layout_name = ''
                if layout_type == "text":
                    keys = layout_item.keys()
                    for key in keys:
                        if key == 'title':
                            layout_name = layout_item[key] if 'About' in layout_item[key] else 'About'
                if layout_type == "faq":
                    layout_name = 'FAQ'
                if layout_type == "metaDescription":
                    layout_name = 'Meta Description'

                prompt_to_run = generate_prompt(
                    prompts=prompts, context=placeholders, prompt_type=layout_type, title=layout_name, setup=setup)

                if log_used_prompts:
                    # Debug: Print the final prompt to run
                    setup.logger(prompt_to_run, log_type=LogType.DEBUG)
                    layout_block = find_layout_block(
                        layout_content, layout_type, layout_name)
                    if layout_block:
                        layout_block['prompt_used'] = prompt_to_run
                    else:
                        print(f"Failed to find layout block for {layout_name}")
                        pprint(layout_content)

                layout_content = process_layout(
                    layout_content, prompt_to_run, block_types=[layout_type])

        # Save the layout content to a JSON file
        setup.logger(
            f"About to save layout content to {path}", log_type=LogType.INFO)
        save_content(path, layout_content)
        setup.logger(
            f"Finished saving layout content to {path}", log_type=LogType.INFO)

    def save_content(path, layout_content):
        if not layout_content:
            setup.logger(f"Skipping path {
                         path} because layout content is empty.", log_type=LogType.WARN)
            return

        # Sort the layout content based on the custom order
        if sort_layout:
            if "layout" in layout_content:
                layout_content["layout"].sort(key=get_order_index)
            else:
                layout_content = {"layout": sorted(
                    layout_content, key=get_order_index)}

        os.makedirs(path, exist_ok=True)

        if "layout" not in layout_content:
            layout_content = {"layout": layout_content}
        json_file = os.path.join(path, 'layout.json')
        with open(json_file, 'w') as f:
            json.dump(layout_content, f, indent=4)
        setup.logger(f"Created JSON file at {
                     json_file}", log_type=LogType.DEBUG)

    if not os.path.exists(base_path):
        print(f"Path {base_path} does not exist.")
        return

    def process_layout(layout, prompt_template, block_types=None):
        """
        Process the layout.json objects and generate content based on prompts.

        :param layout: dict, The layout content to process.
        :param prompt_template: str, The template prompt to use for content generation.
        :param block_types: list, Specific block types to process (default: all types in the layout).
        :return: dict, The updated layout content.
        """
        if not isinstance(layout, dict) or "layout" not in layout:
            raise ValueError(
                "Invalid layout structure. 'layout' key must be present and be a dictionary.")

        if block_types:
            if block_types and not all([block_type in layout_block_types for block_type in block_types]):
                raise ValueError(
                    f"Invalid block types specified: {block_types}. Must be one of {layout_block_types}.")

        time_delta = parse_time_period(time_period)
        now = datetime.now()

        for idx, block in enumerate(layout["layout"]):
            block_type = block.get("type")

            if not block_type:
                setup.logger(f"Skipping block at index {
                             idx}: Missing 'type' field.", log_type=LogType.DEBUG)
                continue

            if block_type not in block_types:
                setup.logger(f"Skipping block at index {idx}: Type '{
                    block_type}' not in specified block types.", log_type=LogType.DEBUG)
                continue

            last_updated_str = block.get("lastUpdated")
            if last_updated_str:
                last_updated = datetime.fromisoformat(last_updated_str)
                if now - last_updated < time_delta:
                    setup.logger(f"Skipping block at index {
                                 idx}: Last updated within the specified time period.", log_type=LogType.WARN)
                    continue

            try:
                prompt = prompt_template
                # Simulate generated content (replace this with actual API calls)
                # this is where we'd run openAI call

                content_dict = {
                    # "system_content": prompt,
                    "user_content": prompt
                }

                def callback(result: Dict[str, Any], block=None) -> None:
                    # sku = result["id"]
                    # save_result(sku, result)
                    generated_content = f"Generated content for block {
                        idx} of type '{block_type}'.\nPrompt used:\n{result}"

                    if "type" in block:
                        # Check if response was successful
                        if not result.get('response', {}).get('success', False):
                            setup.logger(
                                f"API call failed for block {idx}: {result.get('response', {}).get('error', 'Unknown error')}", log_type=LogType.ERROR)
                            return

                        generated_content = result['response']['result']
                        setup.logger(
                            f"Received response for block {idx} ({block_type}): {len(generated_content)} chars", log_type=LogType.INFO)

                        if block["type"] == "faq":
                            generated_content = result['response']['result_json']
                        else:
                            generated_content = result['response']['result']

                    # Update the block with the generated content
                    if "text" in block:
                        block["text"] = generated_content
                        setup.logger(
                            f"Updated block {idx} text field with {len(str(generated_content))} chars", log_type=LogType.INFO)
                    else:
                        setup.logger(
                            f"Block {idx} has no 'text' field, keys: {list(block.keys())}", log_type=LogType.WARN)
                    block["lastUpdated"] = datetime.now().isoformat()
                    setup.logger(
                        f"Set lastUpdated for block {idx}", log_type=LogType.INFO)
                is_faq = block["type"] == "faq"
                # Use the appropriate model enum based on wrapper type
                query_model = None
                if isinstance(ai_wrapper, AIWrapper):
                    query_model = ModelEnum.GPT_4O
                elif isinstance(ai_wrapper, MultiProviderLLM):
                    # Use the model already configured in the wrapper
                    query_model = None  # Will use wrapper's default model

                ai_wrapper.async_submit_query(
                    content_dict=content_dict,
                    callback=lambda res: callback(res, block=block),
                    # request_id=str(sku),
                    cast_to_json=is_faq,
                    model=query_model
                )

                ai_wrapper.wait_on_all_async()

            except Exception as e:
                print(f"Error processing block at index {
                    idx} of type '{block_type}': {e}")

        return layout

    # Load the Excel sheet
    products_df = pd.read_excel(excel_file, sheet_name='data')
    categories_df = pd.read_excel(excel_file, sheet_name='category')

    # Parse the DataFrame and organize categories
    categories = parse_categories(categories_df)
    base_category_found_lvl1 = False
    base_category_found_lvl2 = False

    if not target_level:
        # Process lvl3 categories
        for lvl1, lvl1_data in categories["lvl1"].items():
            if base_category_name and base_category_name == lvl1:
                base_category_found_lvl1 = True
                print(f"Found base lvl1 category {base_category_name}")
            if base_category_name and base_category_found_lvl1 and base_category_name != lvl1:
                print(f"{lvl1} Does not match lvl1 base category {
                      base_category_name}")
                continue

            for lvl2, lvl2_data in lvl1_data["lvl2"].items():
                if base_category_name and base_category_name == lvl2:
                    print(f"Found base lvl2 category {base_category_name}")
                    base_category_found_lvl2 = True
                if base_category_name and base_category_found_lvl2 and base_category_name != lvl2:
                    print(f"{lvl2} Does not match lvl1 base category {
                        base_category_name}")
                    continue

                for lvl3, lvl3_data in lvl2_data["lvl3"].items():
                    setup.logger(f"Processing lvl3 category {
                                 lvl3}", log_type=LogType.WARN)
                    process_category(3, lvl3, lvl3_data["path"], reset_all, merge_only, validate_layout,
                                     log_used_prompts, categories=categories, products_df=products_df)

        # Process lvl2 categories
        for lvl1, lvl1_data in categories["lvl1"].items():
            if base_category_name and base_category_name == lvl1:
                base_category_found_lvl1 = True
            if base_category_name and base_category_found_lvl1 and base_category_name != lvl1:
                continue

            for lvl2, lvl2_data in lvl1_data["lvl2"].items():
                if base_category_name and base_category_name == lvl2:
                    base_category_found_lvl2 = True
                if base_category_name and base_category_found_lvl2 and base_category_name != lvl2:
                    continue

                setup.logger(f"Processing lvl2 category {
                             lvl2}", log_type=LogType.WARN)
                process_category(2, lvl2, lvl2_data["path"], reset_all, merge_only,
                                 validate_layout, log_used_prompts, categories=categories)

        # Process lvl1 categories
        for lvl1, lvl1_data in categories["lvl1"].items():
            if base_category_name and base_category_name == lvl1:
                base_category_found_lvl1 = True
            if base_category_name and base_category_found_lvl1 and base_category_name != lvl1:
                continue

            setup.logger(f"Processing lvl1 category {
                         lvl1}", log_type=LogType.WARN)
            process_category(1, lvl1, lvl1_data["path"], reset_all, merge_only,
                             validate_layout, log_used_prompts, categories=categories)

    if target_level == "lvl3":
        for lvl1, lvl1_data in categories["lvl1"].items():
            if base_category_name and base_category_name == lvl1:
                base_category_found_lvl1 = True
            if base_category_name and not base_category_found_lvl1:
                continue

            for lvl2, lvl2_data in lvl1_data["lvl2"].items():
                if base_category_name and base_category_name == lvl2:
                    base_category_found_lvl2 = True
                if base_category_name and not base_category_found_lvl1 and not base_category_found_lvl2:
                    continue

                for lvl3, lvl3_data in lvl2_data["lvl3"].items():
                    process_category(
                        3, lvl3, lvl3_data["path"], reset_all, merge_only, validate_layout, log_used_prompts, products_df)

    if target_level == "lvl2":
        for lvl1, lvl1_data in categories["lvl1"].items():
            if base_category_name and base_category_name == lvl1:
                base_category_found_lvl1 = True
            if base_category_name and not base_category_found_lvl1:
                continue

            for lvl2, lvl2_data in lvl1_data["lvl2"].items():
                if base_category_name and base_category_name == lvl2:
                    base_category_found_lvl2 = True
                if base_category_name and not base_category_found_lvl1 and not base_category_found_lvl2:
                    continue

                process_category(
                    2, lvl2, lvl2_data["path"], reset_all, merge_only, validate_layout, log_used_prompts)

    if target_level == "lvl1":
        for lvl1, lvl1_data in categories["lvl1"].items():
            if base_category_name and base_category_name == lvl1:
                base_category_found_lvl1 = True
            if base_category_name and not base_category_found_lvl1:
                continue

            process_category(
                1, lvl1, lvl1_data["path"], reset_all, merge_only, validate_layout, log_used_prompts)


if __name__ == "__main__":
    main()
