from result import Result, Ok, is_ok
from http_client import AsyncHttpClient
import trio
from primitives import AsyncKVStore, AsyncQueue
from messages import Request
from config import Config
from verification import verify_request
from logbar import LogBar
from logbar.progress import ProgressBar
from datasets import load_dataset
from output import save_requests, convert_requests_to_dataframe, save_dataframe

@Result.resultify_async
async def worker(
    http_client: AsyncHttpClient,
    input_queue: AsyncQueue[Request],
    verify_queue: AsyncQueue[Request],
    log: LogBar,
    config: Config,
) -> None:
    """Process requests and send results to the verification queue."""
    while True:
        request = await input_queue.dequeue()
        response = await request.unwrap().req(http_client, config.api.model)
        if is_ok(response):
            await verify_queue.enqueue(response.unwrap())
        else:
            log.error(
                f"Failed to process request, readding to input queue: {response.unwrap_err()}"
            )
            await input_queue.enqueue(request.unwrap())

@Result.resultify_async
async def output_worker(
    output_queue: AsyncQueue[Request],
    kv_store: AsyncKVStore[str, int],
    config: Config,
    log: LogBar,
    total_requests: int,
    completed_requests: list[Request],
) -> None:
    """Collect completed requests from the output queue."""

    while True:
        while (await output_queue.size()).unwrap() > 0:
            request = await output_queue.dequeue()
            completed_requests.append(request.unwrap())

        completed_count = (await kv_store.get("requests_completed")).unwrap()
        if completed_count >= total_requests and len(completed_requests) >= total_requests:
            break

        await trio.sleep(0.1)

    if config.output is not None:
        log.info("Saving output data...")
        save_result = save_requests(completed_requests, config)
        if save_result._error is None:
            log.info(
                f"Successfully saved {len(completed_requests)} requests to {config.output.path}"
            )
        else:
            log.error(f"Failed to save output: {save_result.unwrap_err()}")


@Result.resultify_async
async def verification_worker(
    kv_store: AsyncKVStore[str, int],
    input_queue: AsyncQueue[Request],
    verify_queue: AsyncQueue[Request],
    output_queue: AsyncQueue[Request],
    log: LogBar,
    pb: ProgressBar,
) -> None:
    """Verify requests and route them to the appropriate queue."""

    while True:
        request_res = await verify_queue.dequeue()
        request = request_res.unwrap()

        verified = verify_request(request)
        if is_ok(verified) and verified.unwrap():
            await output_queue.enqueue(request)
            await kv_store.set(
                "requests_completed",
                (await kv_store.get("requests_completed")).unwrap() + 1,
            )
            pb.next()
            pb.draw()
        else:
            log.error("Request failed verification, returning to input queue")
            await input_queue.enqueue(request)


@Result.resultify_async
async def checkpoint_worker(
    kv_store: AsyncKVStore[str, int],
    config: Config,
    log: LogBar,
    total_requests: int,
    completed_requests: list[Request],
) -> None:
    """Periodically save a checkpoint of completed requests."""

    if config.output is None or config.output.checkpoint_interval is None:
        return None

    interval = config.output.checkpoint_interval
    last_saved = 0
    checkpoint_path = f"{config.output.path}.checkpoint"

    while True:
        completed_count = (await kv_store.get("requests_completed")).unwrap()

        if completed_count - last_saved >= interval and len(completed_requests) > 0:
            output_format = (
                config.output.format if config.output.format is not None else config.data.format
            )
            df_result = convert_requests_to_dataframe(completed_requests, output_format)
            if df_result._error is None:
                df = df_result.unwrap()
                save_result = save_dataframe(df, checkpoint_path, config.output.type)
                if save_result._error is None:
                    last_saved = completed_count
                    log.info(
                        f"Checkpoint saved ({completed_count} responses) to {checkpoint_path}"
                    )
                else:
                    log.error(f"Failed to save checkpoint: {save_result.unwrap_err()}")
            else:
                log.error(f"Failed to convert checkpoint dataframe: {df_result.unwrap_err()}")

        if completed_count >= total_requests:
            break

        await trio.sleep(0.1)

async def main() -> Result[None]:
    config = Config.from_toml("./config.toml").unwrap()
    http_client = AsyncHttpClient(base_url=config.api.base_url, headers={"Authorization": f"Bearer {config.api.api_key}"})
    kv_lock = trio.Lock()
    queue_lock = trio.Lock()
    verify_lock = trio.Lock()
    output_lock = trio.Lock()
    kv_store = AsyncKVStore[str, int](default_value=0, lock=kv_lock)
    input_queue = AsyncQueue[Request](lock=queue_lock)
    verify_queue = AsyncQueue[Request](lock=verify_lock)
    output_queue = AsyncQueue[Request](lock=output_lock)
    log = LogBar(name="main")

    ds = load_dataset(config).unwrap()
    for request in ds:
        await input_queue.enqueue(request)
    
    size = (await input_queue.size()).unwrap()
    log.info(f"Queued {size} requests")
    pb = log.pb(range(size)).subtitle("Processing requests")
    pb.draw()

    completed_requests: list[Request] = []

    async with trio.open_nursery() as nursery:
        # Start worker processes
        for _ in range(config.processes.parallel):
            nursery.start_soon(worker, http_client, input_queue, verify_queue, log, config)

        # Start verification worker(s)
        verify_parallel = (
            config.processes.verify_parallel
            if config.processes.verify_parallel is not None
            else config.processes.parallel
        )
        for _ in range(verify_parallel):
            nursery.start_soon(
                verification_worker,
                kv_store,
                input_queue,
                verify_queue,
                output_queue,
                log,
                pb,
            )

        # Start workers that handle output
        if config.output is not None:
            nursery.start_soon(output_worker, output_queue, kv_store, config, log, size, completed_requests)

            if config.output.checkpoint_interval is not None:
                nursery.start_soon(checkpoint_worker, kv_store, config, log, size, completed_requests)

    # Cursor, trio automatically joins the nursery. We don't need to do anything here.

    log.info("All requests completed!")

    return Ok(None)

if __name__ == "__main__":
    trio.run(main, restrict_keyboard_interrupt_to_checkpoints=True) # type: ignore // what the fuck?
