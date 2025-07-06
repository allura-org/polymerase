from result import Result
from messages import Request
from ifbench import instructions_registry
from typing import Any
import msgspec

@Result.resultify
def verify_request(request: Request, *, backend: str | None = "ifbench") -> bool:
    """Verify a request's response using the specified backend."""

    if backend is None:
        return True
    row = request.metadata or {}

    instructions = None
    kwargs_list = None
    if "ground_truth" in row and row["ground_truth"] is not None:
        gt = row["ground_truth"]
        if isinstance(gt, str):
            try:
                gt = msgspec.json.decode(gt.encode())
            except Exception:
                pass
        if isinstance(gt, list) and len(gt) > 0:
            inst_entry = gt[0]
            instructions = inst_entry.get("instruction_id")
            kwargs_list = inst_entry.get("kwargs")

    if instructions is None and "instruction_id_list" in row:
        instructions = row.get("instruction_id_list")
        kwargs_list = row.get("kwargs")

    instructions = instructions or []
    kwargs_list = kwargs_list or []

    if not instructions:
        return True

    # extract prompt and assistant response
    prompt = None
    for m in request.messages:
        if m.role == "user":
            prompt = m.content
            break
    response = None
    for m in reversed(request.messages):
        if m.role == "assistant":
            response = m.content
            break

    if prompt is None or response is None:
        return False

    follow_results: list[bool] = []
    for idx, instruction_id in enumerate(instructions):
        instruction_cls = instructions_registry.INSTRUCTION_DICT.get(instruction_id)
        if instruction_cls is None:
            follow_results.append(False)
            continue

        inst = instruction_cls(instruction_id)
        kwargs: dict[str, Any] = {}
        if idx < len(kwargs_list) and kwargs_list[idx] is not None:
            kwargs = {k: v for k, v in kwargs_list[idx].items() if v is not None}

        inst.build_description(**kwargs)
        args = inst.get_instruction_args()
        if args and "prompt" in args:
            inst.build_description(prompt=prompt, **kwargs)

        if response.strip() and inst.check_following(response):
            follow_results.append(True)
        else:
            follow_results.append(False)

    return all(follow_results)
