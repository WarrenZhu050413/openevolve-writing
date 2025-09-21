"""
Claude Code SDK interface for LLMs
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions, CLINotFoundError, ProcessError

from openevolve.config import LLMConfig
from openevolve.llm.base import LLMInterface

logger = logging.getLogger(__name__)


class ClaudeCodeLLM(LLMInterface):
    """LLM interface using Claude Code SDK"""

    def __init__(
        self,
        model_cfg: Optional[dict] = None,
    ):
        self.model = model_cfg.name  # "opus" or "sonnet"
        self.system_message = model_cfg.system_message
        self.temperature = model_cfg.temperature
        self.max_tokens = model_cfg.max_tokens
        self.timeout = model_cfg.timeout
        self.retries = model_cfg.retries
        self.retry_delay = model_cfg.retry_delay
        
        # Map simple names to model names if needed by Claude Code SDK
        # For now, we'll let the SDK handle model selection automatically
        
        # Claude Code SDK options
        self.options = ClaudeCodeOptions(
            system_prompt=self.system_message,
            max_turns=1  # Single turn for evolution
        )
        
        # Only log unique models to reduce duplication
        if not hasattr(logger, "_initialized_models"):
            logger._initialized_models = set()

        if self.model not in logger._initialized_models:
            logger.info(f"Initialized Claude Code LLM with model: {self.model}")
            logger._initialized_models.add(self.model)

    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from a prompt"""
        return await self.generate_with_context(
            system_message=self.system_message,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )

    async def generate_with_context(
        self, system_message: str, messages: List[Dict[str, str]], **kwargs
    ) -> str:
        """Generate text using a system message and conversational context"""
        
        # Update system prompt if different from initialization
        if system_message != self.system_message:
            self.options = ClaudeCodeOptions(
                system_prompt=system_message,
                max_turns=1
            )
        
        # Get the user message (last in the conversation)
        user_message = messages[-1]["content"] if messages else ""
        
        # Set up retry logic
        retries = kwargs.get("retries", self.retries)
        retry_delay = kwargs.get("retry_delay", self.retry_delay)
        
        for attempt in range(retries + 1):
            try:
                response = await self._call_claude_api(user_message)
                return response
            except asyncio.TimeoutError:
                if attempt < retries:
                    logger.warning(f"Timeout on attempt {attempt + 1}/{retries + 1}. Retrying...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"All {retries + 1} attempts failed with timeout")
                    raise
            except Exception as e:
                if attempt < retries:
                    logger.warning(
                        f"Error on attempt {attempt + 1}/{retries + 1}: {str(e)}. Retrying..."
                    )
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"All {retries + 1} attempts failed with error: {str(e)}")
                    raise

    async def _call_claude_api(self, prompt: str) -> str:
        """Make the actual Claude Code SDK call"""
        try:
            async with ClaudeSDKClient(options=self.options) as client:
                await client.query(prompt)
                
                # Collect all response content
                response_parts = []
                async for message in client.receive_response():
                    if hasattr(message, 'content'):
                        for block in message.content:
                            if hasattr(block, 'text'):
                                response_parts.append(block.text)
                
                response_text = ''.join(response_parts)
                
                # Logging
                logger.debug(f"Claude prompt: {prompt[:100]}...")
                logger.debug(f"Claude response: {response_text[:100]}...")
                
                return response_text
                
        except CLINotFoundError:
            logger.error("Claude Code CLI not found. Please install: npm install -g @anthropic-ai/claude-code")
            raise
        except ProcessError as e:
            logger.error(f"Claude Code process error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Claude Code SDK error: {str(e)}")
            raise