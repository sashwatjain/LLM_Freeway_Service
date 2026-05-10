from pydantic import BaseModel, Field
from typing import Optional


class Message(BaseModel):
    role: str = Field(examples=["user"])
    content: str = Field(examples=["Hello!"])


class ChatRequest(BaseModel):
    provider: str = Field(examples=["github"])
    model: str = Field(examples=["Ministral-3B"])
    messages: list[Message] = Field(examples=[[{"role": "user", "content": "Hello!"}]])
    system_prompt: Optional[str] = Field(default=None, examples=["You are a helpful assistant."])
    memory: bool = False
    session_id: Optional[str] = Field(default=None, examples=["my-session"])


class ContinueChatRequest(BaseModel):
    messages: list[Message] = Field(examples=[[{"role": "user", "content": "Hello!"}]])
    system_prompt: Optional[str] = Field(default=None, examples=["You are a helpful assistant."])
    memory: bool = False
    session_id: Optional[str] = Field(default=None, examples=["my-session"])
    provider_priority: Optional[list[str]] = Field(default=None, examples=[["openrouter", "groq", "github"]])


class ChatResponse(BaseModel):
    choices: list[dict]
    usage: Optional[dict] = None
    provider: str
    model: str


class ProviderInfo(BaseModel):
    name: str
    configured: bool
    models_count: int = 0


class ModelLimits(BaseModel):
    requests_per_minute: Optional[int] = None
    requests_per_day: Optional[int] = None
    tokens_per_minute: Optional[int] = None


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    limits: ModelLimits = ModelLimits()
