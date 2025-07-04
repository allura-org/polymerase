import msgspec
from msgspec import Struct
from typing import Self
from result import Result
from enum import Enum

class DataType(Enum):
    HF = "hf"
    JSONL = "jsonl"
    PARQUET = "parquet"

class DataFormat(Enum):
    MESSAGES_COLUMN = "messages_column"
    PROMPT_COLUMN = "prompt_column"

class APIConfig(Struct):
    base_url: str
    model: str
    api_key: str

class ModelConfig(Struct):
    system_prompt: str | None = None
    temperature: float | None = None
    top_p: float | None = None

class DataConfig(Struct):
    path: str
    type: DataType
    format: DataFormat
    limit: int | None = None

class ProcessesConfig(Struct):
    parallel: int

class OutputConfig(Struct):
    path: str
    type: DataType
    format: DataFormat | None = None
    checkpoint_interval: int | None = None

class VerificationConfig(Struct):
    # Placeholder for future verification-specific configurations
    # For example, could specify a script path or module for the verification_fn
    enabled: bool = True # By default, verification is enabled if the section exists

class Config(Struct):
    api: APIConfig
    model: ModelConfig
    data: DataConfig
    processes: ProcessesConfig
    output: OutputConfig | None = None
    verification: VerificationConfig | None = None # Added verification config

    @Result.resultify
    @staticmethod
    def from_toml(path: str) -> Self:
        with open(path, "r") as f:
            config = msgspec.toml.decode(f.read(), type=Config)
        return config