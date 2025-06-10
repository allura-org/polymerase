import polars as pl
from result import Result, Err, Ok
from config import DataType, DataFormat, Config
from messages import Request
from typing import Any

def convert_requests_to_dataframe(requests: list[Request], format: DataFormat) -> Result[pl.DataFrame]:
    """Convert a list of Request objects back to DataFrame format"""
    try:
        if format == DataFormat.MESSAGES_COLUMN:
            # Convert messages to list of dicts for each request
            data = []
            for request in requests:
                messages_list = []
                for msg in request.messages:
                    msg_dict = {
                        "role": msg.role,
                        "content": msg.content
                    }
                    if msg.reasoning is not None:
                        msg_dict["reasoning"] = msg.reasoning
                    messages_list.append(msg_dict)
                data.append({"messages": messages_list})
            return Ok(pl.DataFrame(data))
        
        elif format == DataFormat.PROMPT_COLUMN:
            # Extract prompts and responses
            data = []
            for request in requests:
                # Find the user prompt (skip system message if present)
                prompt: str | None = None
                response: str | None = None
                reasoning: str | None = None
                
                for msg in request.messages:
                    if msg.role == "user" and prompt is None:
                        prompt = msg.content
                    elif msg.role == "assistant":
                        response = msg.content
                        reasoning = msg.reasoning
                        break
                
                row: dict[str, Any] = {"prompt": prompt}
                if response is not None:
                    row["response"] = response
                if reasoning is not None:
                    row["reasoning"] = reasoning
                    
                data.append(row)
            return Ok(pl.DataFrame(data))
        
        else:
            return Err(ValueError(f"Invalid output format: {format}"))
            
    except Exception as e:
        return Err(e)

def save_dataframe(df: pl.DataFrame, path: str, type: DataType) -> Result[None]:
    """Save a DataFrame to the specified path and format"""
    try:
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
            return Err(ValueError(f"Invalid output type: {type}"))
        
        return Ok(None)
        
    except Exception as e:
        return Err(e)

def save_requests(requests: list[Request], config: Config) -> Result[None]:
    """Convert requests to DataFrame and save to file"""
    if config.output is None:
        return Err(ValueError("No output configuration provided"))
    
    # Use output format if specified, otherwise fall back to input format
    output_format = config.output.format if config.output.format is not None else config.data.format
    
    # Convert to DataFrame
    df_result = convert_requests_to_dataframe(requests, output_format)
    if df_result._error is not None:
        return Err(df_result.unwrap_err())
    
    df = df_result.unwrap()
    
    # Save DataFrame
    save_result = save_dataframe(df, config.output.path, config.output.type)
    if save_result._error is not None:
        return Err(save_result.unwrap_err())
    
    return Ok(None) 