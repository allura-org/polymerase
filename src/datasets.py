import polars as pl
from result import Result, Err, Ok, is_err
from config import DataType, DataFormat, Config
from messages import Request, Message

@Result.resultify
def load_hf_dataset(path: str) -> pl.DataFrame:
    path_string = f"hf://datasets/{path}@refs%2Fconvert%2Fparquet/**/*.parquet"
    return pl.read_parquet(path_string)

@Result.resultify
def load_jsonl_dataset(path: str) -> pl.DataFrame:
    return pl.read_ndjson(path)

@Result.resultify
def load_parquet_dataset(path: str) -> pl.DataFrame:
    return pl.read_parquet(path)

@Result.resultify
def convert_to_request(df: pl.DataFrame, config: Config) -> list[Request]:
    format = config.data.format
    system_prompt = config.model.system_prompt
    
    match format:
        case DataFormat.MESSAGES_COLUMN:
            # FIXME: won't work, we need to convert the list of dicts a proper Message[]
            if system_prompt is not None:
                return [Request(messages=([Message(role="system", content=system_prompt)] + messages), temperature=config.model.temperature, top_p=config.model.top_p) for messages in df["messages"].to_list()]
            else:
                return [Request(messages=messages, temperature=config.model.temperature, top_p=config.model.top_p) for messages in df["messages"].to_list()]
        case DataFormat.PROMPT_COLUMN:
            if system_prompt is not None:
                return [Request(messages=[Message(role="system", content=system_prompt), Message(role="user", content=prompt)], temperature=config.model.temperature, top_p=config.model.top_p) for prompt in df["prompt"].to_list()]
            else:
                # FIXME: we should support a `system_prompt` column
                return [Request(messages=[Message(role="user", content=prompt)], temperature=config.model.temperature, top_p=config.model.top_p) for prompt in df["prompt"].to_list()]
        case _:
            raise ValueError(f"Invalid dataset format: {format}")

def load_dataset(config: Config) -> Result[list[Request]]:
    path = config.data.path
    type = config.data.type
    
    match type:
        case DataType.HF:
            ds = load_hf_dataset(path)
        case DataType.JSONL:
            ds = load_jsonl_dataset(path)
        case DataType.PARQUET:
            ds = load_parquet_dataset(path)
        case _:
            return Err(ValueError(f"Invalid dataset type: {type}"))
    
    if is_err(ds):
        return Err(ds.unwrap_err())
        
    df = ds.unwrap()

    if config.data.limit is not None and config.data.limit > 0:
        limit = min(config.data.limit, len(df))
        df = df.slice(0, limit)

    return convert_to_request(df, config)

@Result.resultify
def convert_requests_to_dataframe(requests: list[Request], format: DataFormat) -> pl.DataFrame:
    """Convert a list of Request objects back to DataFrame format"""
    match format:
        case DataFormat.MESSAGES_COLUMN:
            # Convert messages to list of dicts for each request
            data: list[dict] = []
            for request in requests:
                messages_dict = [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "reasoning": msg.reasoning
                    }
                    for msg in request.messages if msg.content != None
                ]
                data.append({"messages": messages_dict})
            print(data[0])
            return pl.DataFrame(data)
        case DataFormat.PROMPT_COLUMN:
            # Extract prompts and responses
            data: list[dict] = []
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
                
                row = {"prompt": prompt, "response": response, "reasoning": reasoning}
                data.append(row)
            return pl.DataFrame(data)
        case _:
            raise ValueError(f"Invalid output format: {format}")

@Result.resultify
def save_dataframe(df: pl.DataFrame, path: str, type: DataType) -> None:
    """Save a DataFrame to the specified path and format"""
    match type:
        case DataType.JSONL:
            df.write_ndjson(path)
        case DataType.PARQUET:
            df.write_parquet(path)
        case DataType.HF:
            # For HF, we'll save as parquet locally
            # TODO: Could implement actual HF dataset push later
            parquet_path = path.replace('.hf', '.parquet') if path.endswith('.hf') else f"{path}.parquet"
            df.write_parquet(parquet_path)
        case _:
            raise ValueError(f"Invalid output type: {type}")

def save_requests(requests: list[Request], config: Config) -> Result[None]:
    """Convert requests to DataFrame and save to file"""
    if config.output is None:
        return Err(ValueError("No output configuration provided"))
    
    # Use output format if specified, otherwise fall back to input format
    output_format = config.output.format if config.output.format is not None else config.data.format
    
    df_result = convert_requests_to_dataframe(requests, output_format)
    if is_err(df_result):
        return Err(df_result.unwrap_err())
    
    df = df_result.unwrap()
    save_result = save_dataframe(df, config.output.path, config.output.type)
    if is_err(save_result):
        return Err(save_result.unwrap_err())
    
    return Ok(None)
