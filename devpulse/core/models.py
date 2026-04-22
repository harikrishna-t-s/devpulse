"""Pydantic models for data validation."""
from typing import Optional
from pydantic import BaseModel, HttpUrl, Field, field_validator


class Article(BaseModel):
    """Article model for validation."""
    title: str = Field(..., min_length=1, max_length=500)
    url: HttpUrl
    content: str = Field(default="", max_length=10000)
    source: str = Field(..., min_length=1, max_length=100)
    published: Optional[str] = None
    
    @field_validator('content')
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        """Sanitize content by removing excessive whitespace."""
        if not v:
            return ""
        return " ".join(v.split())


class Source(BaseModel):
    """Source configuration model."""
    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1)
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Basic URL validation."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v


class ScoringConfig(BaseModel):
    """Scoring configuration model."""
    threshold: int = Field(default=50, ge=0, le=1000)
    weights: dict = Field(default_factory=dict)
    freshness_boost: int = Field(default=20, ge=0, le=100)


class NLPConfig(BaseModel):
    """NLP configuration model."""
    enabled: bool = True
    components: dict = Field(default_factory=dict)
    settings: dict = Field(default_factory=dict)
    model_path: str = "models"
    corpus_path: str = "corpus"
