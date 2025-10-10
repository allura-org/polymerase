import polars as pl
from config import DataType, DataFormat, Config
from messages import Request, Message

def load_hf_dataset(path: str) -> pl.DataFrame:
    path_string = f"hf://datasets/{path}@refs%2Fconvert%2Fparquet/**/*.parquet"
    return pl.read_parquet(path_string)

def load_jsonl_dataset(path: str) -> pl.DataFrame:
    return pl.read_ndjson(path)

def load_parquet_dataset(path: str) -> pl.DataFrame:
    return pl.read_parquet(path)

def convert_to_request(df: pl.DataFrame, config: Config) -> list[Request]:
    format = config.data.format
    system_prompt = config.model.system_prompt
    prefill = config.model.prefill

    match format:
        case DataFormat.MESSAGES_COLUMN:
            requests = []
            for messages_list in df["messages"].to_list():
                # Convert dict messages to Message objects
                message_objects = []
                for msg_dict in messages_list:
                    if isinstance(msg_dict, dict):
                        message = Message(
                            role=msg_dict["role"],
                            content=msg_dict["content"],
                            reasoning=msg_dict.get("reasoning")
                        )
                        message_objects.append(message)
                    else:
                        # Assume it's already a Message object
                        message_objects.append(msg_dict)

                if system_prompt is not None:
                    system_msg = Message(role="system", content=system_prompt)
                    message_objects = [system_msg] + message_objects

                if prefill is not None:
                    # FIXME: somehow do provider-specific handling
                    prefill_msg = Message(role="assistant", content=prefill)
                    message_objects = message_objects + [prefill_msg]


                requests.append(Request(
                    messages=message_objects,
                    temperature=config.model.temperature,
                    top_p=config.model.top_p
                ))
            return requests
        case DataFormat.PROMPT_COLUMN:
            if system_prompt is not None:
                return [Request(messages=[Message(role="system", content=system_prompt), Message(role="user", content=prompt)], temperature=config.model.temperature, top_p=config.model.top_p) for prompt in df["prompt"].to_list()]
            else:
                # FIXME: we should support a `system_prompt` column
                return [Request(messages=[Message(role="user", content=prompt)], temperature=config.model.temperature, top_p=config.model.top_p) for prompt in df["prompt"].to_list()]
        case _:
            raise ValueError(f"Invalid dataset format: {format}")

def load_dataset(config: Config) -> list[Request]:
    path = config.data.path
    type = config.data.type

    match type:
        case DataType.HF:
            df = load_hf_dataset(path)
        case DataType.JSONL:
            df = load_jsonl_dataset(path)
        case DataType.PARQUET:
            df = load_parquet_dataset(path)
        case _:
            raise ValueError(f"Invalid dataset type: {type}")

    if config.data.limit is not None and config.data.limit > 0:
        limit = min(config.data.limit, len(df))
        df = df.slice(0, limit)

    return convert_to_request(df, config)
