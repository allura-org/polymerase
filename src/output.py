import polars as pl
from config import DataType, DataFormat, Config
from messages import Request
from typing import Any

def convert_requests_to_dataframe(requests: list[Request], format: DataFormat) -> pl.DataFrame:
    """Convert a list of Request objects back to DataFrame format"""
    if format == DataFormat.MESSAGES_COLUMN:
        # Convert messages to list of dicts for each request
        data = []
        for request in requests:
            messages_list = []
            for msg in request.messages:
                # Handle both Message objects and dictionaries
                if hasattr(msg, 'role'):
                    # It's a Message object
                    msg_dict = {
                        "role": msg.role,
                        "content": msg.content
                    }
                    if hasattr(msg, 'reasoning') and msg.reasoning is not None:
                        msg_dict["reasoning"] = msg.reasoning
                elif isinstance(msg, dict):
                    # It's already a dict, ensure it has the required fields
                    msg_dict = {
                        "role": msg.get("role", "unknown"),
                        "content": msg.get("content", "")
                    }
                    if "reasoning" in msg and msg["reasoning"] is not None:
                        msg_dict["reasoning"] = msg["reasoning"]
                else:
                    # Skip invalid message types
                    continue

                messages_list.append(msg_dict)
            data.append({"messages": messages_list})
        return pl.DataFrame(data)

    elif format == DataFormat.PROMPT_COLUMN:
        # Extract prompts and responses
        data = []
        for request in requests:
            # Find the user prompt (skip system message if present)
            prompt: str | None = None
            response: str | None = None
            reasoning: str | None = None

            for msg in request.messages:
                # Handle both Message objects and dictionaries
                if hasattr(msg, 'role'):
                    role, content, msg_reasoning = msg.role, msg.content, getattr(msg, 'reasoning', None)
                elif isinstance(msg, dict):
                    role, content, msg_reasoning = msg.get("role", "unknown"), msg.get("content", ""), msg.get("reasoning")
                else:
                    continue

                if role == "user" and prompt is None:
                    prompt = content
                elif role == "assistant":
                    response = content
                    reasoning = msg_reasoning
                    break

            row: dict[str, Any] = {"prompt": prompt}
            if response is not None:
                row["response"] = response
            if reasoning is not None:
                row["reasoning"] = reasoning

            data.append(row)
        return pl.DataFrame(data)

    else:
        raise ValueError(f"Invalid output format: {format}")

def save_dataframe(df: pl.DataFrame, path: str, type: DataType) -> None:
    """Save a DataFrame to the specified path and format"""
    if type == DataType.JSONL:
        df.write_ndjson(path)
    elif type == DataType.PARQUET:
        df.write_parquet(path)
    elif type == DataType.HF:
        # For HF, we'll save as parquet locally
        # TODO: Could implement actual HF dataset push later
        parquet_path = path.replace('.hf', '.parquet') if path.endswith('.hf') else f"{path}.parquet"
        df.write_parquet(parquet_path)
    else:
        raise ValueError(f"Invalid output type: {type}")

def save_requests(requests: list[Request], config: Config) -> None:
    """Convert requests to DataFrame and save to file"""
    if config.output is None:
        raise ValueError("No output configuration provided")

    # Use output format if specified, otherwise fall back to input format
    output_format = config.output.format if config.output.format is not None else config.data.format

    # Convert to DataFrame
    df = convert_requests_to_dataframe(requests, output_format)

    # Save DataFrame
    save_dataframe(df, config.output.path, config.output.type) 
