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

async def worker(
    http_client: AsyncHttpClient,
    input_queue: AsyncQueue[Request],
    verify_queue: AsyncQueue[Request],
    log: LogBar,
    config: Config,
    shutdown_event: trio.Event,
) -> None:
    """Process requests and send results to the verification queue."""
    while not shutdown_event.is_set():
        try:
            request = await input_queue.dequeue()
            response = await request.req(http_client, config.api.model)
            await verify_queue.enqueue(response)
        except IndexError:
            await trio.sleep(0.1)
            continue
        except Exception as e:
            if not shutdown_event.is_set():
                log.error(f"Worker error: {e}, requeuing request")
                try:
                    await input_queue.enqueue(request)
                except NameError:
                    pass
            break

async def output_worker(
    output_queue: AsyncQueue[Request],
    kv_store: AsyncKVStore[str, int],
    config: Config,
    log: LogBar,
    total_requests: int,
    completed_requests: list[Request],
    shutdown_event: trio.Event,
) -> None:
    """Collect completed requests from the output queue."""

    while not shutdown_event.is_set():
        try:
            while await output_queue.size() > 0:
                request = await output_queue.dequeue()
                completed_requests.append(request)

            completed_count = await kv_store.get("requests_completed")
            processed_count = await kv_store.get("requests_processed")

            if completed_count >= total_requests and len(completed_requests) >= total_requests:
                break

            if processed_count >= total_requests and completed_count == 0:
                log.warning("All requests processed but none completed - possible verification failures")
                break

            await trio.sleep(0.1)
        except Exception as e:
            if not shutdown_event.is_set():
                log.error(f"Output worker error: {e}")
            break

    if config.output is not None:
        log.info("Saving output data...")
        try:
            save_requests(completed_requests, config)
            log.info(
                f"Successfully saved {len(completed_requests)} requests to {config.output.path}"
            )
        except Exception as e:
            log.error(f"Failed to save output: {e}")


async def verification_worker(
    kv_store: AsyncKVStore[str, int],
    input_queue: AsyncQueue[Request],
    verify_queue: AsyncQueue[Request],
    output_queue: AsyncQueue[Request],
    log: LogBar,
    pb: ProgressBar,
    shutdown_event: trio.Event,
) -> None:
    """Verify requests and route them to the appropriate queue."""

    while not shutdown_event.is_set():
        try:
            request = await verify_queue.dequeue()

            retry_count = await kv_store.get(f"retry_count_{id(request)}")
            if retry_count >= 3:
                log.warning(f"Request exceeded retry limit, discarding")
                processed_count = await kv_store.get("requests_processed")
                await kv_store.set("requests_processed", processed_count + 1)
                continue

            verified = verify_request(request)
            if verified:
                await output_queue.enqueue(request)
                completed_count = await kv_store.get("requests_completed")
                await kv_store.set("requests_completed", completed_count + 1)
                pb.next()
                pb.draw()
            else:
                retry_count += 1
                await kv_store.set(f"retry_count_{id(request)}", retry_count)
                log.error(f"Request failed verification (attempt {retry_count}/3), returning to input queue")
                await input_queue.enqueue(request)
        except IndexError:
            await trio.sleep(0.1)
            continue
        except Exception as e:
            if not shutdown_event.is_set():
                log.error(f"Verification worker error: {e}")
            break


async def checkpoint_worker(
    kv_store: AsyncKVStore[str, int],
    config: Config,
    log: LogBar,
    total_requests: int,
    completed_requests: list[Request],
    shutdown_event: trio.Event,
) -> None:
    """Periodically save a checkpoint of completed requests."""

    if config.output is None or config.output.checkpoint_interval is None:
        return

    interval = config.output.checkpoint_interval
    last_saved = 0
    # Create checkpoint path with proper file extension
    base_path = config.output.path
    if base_path.endswith('.jsonl'):
        checkpoint_path = base_path.replace('.jsonl', '.checkpoint.jsonl')
    elif base_path.endswith('.parquet'):
        checkpoint_path = base_path.replace('.parquet', '.checkpoint.parquet')
    else:
        checkpoint_path = f"{base_path}.checkpoint"

    while not shutdown_event.is_set():
        try:
            completed_count = await kv_store.get("requests_completed")
            processed_count = await kv_store.get("requests_processed")

            if completed_count - last_saved >= interval and len(completed_requests) > 0:
                output_format = (
                    config.output.format if config.output.format is not None else config.data.format
                )
                df = convert_requests_to_dataframe(completed_requests, output_format)
                save_dataframe(df, checkpoint_path, config.output.type)
                last_saved = completed_count
                log.info(
                    f"Checkpoint saved ({completed_count} responses) to {checkpoint_path}"
                )

            if completed_count >= total_requests or processed_count >= total_requests:
                break

            await trio.sleep(0.1)
        except Exception as e:
            if not shutdown_event.is_set():
                log.error(f"Checkpoint worker error: {e}")
                # Don't break on error, continue trying to checkpoint
                await trio.sleep(1)  # Wait longer after an error

async def main():
    config = Config.from_toml("./config.toml")
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

    ds = load_dataset(config)
    for request in ds:
        await input_queue.enqueue(request)

    size = await input_queue.size()
    log.info(f"Queued {size} requests")
    pb = log.pb(range(size)).subtitle("Processing requests")
    pb.draw()

    completed_requests: list[Request] = []
    shutdown_event = trio.Event()

    async with trio.open_nursery() as nursery:
        # Start worker processes
        for _ in range(config.processes.parallel):
            nursery.start_soon(worker, http_client, input_queue, verify_queue, log, config, shutdown_event)

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
                shutdown_event,
            )

        # Start workers that handle output
        if config.output is not None:
            nursery.start_soon(output_worker, output_queue, kv_store, config, log, size, completed_requests, shutdown_event)

            if config.output.checkpoint_interval is not None:
                nursery.start_soon(checkpoint_worker, kv_store, config, log, size, completed_requests, shutdown_event)

        # Monitor completion and trigger shutdown
        async def monitor_completion():
            while True:
                completed_count = await kv_store.get("requests_completed")
                processed_count = await kv_store.get("requests_processed")

                if completed_count >= size or processed_count >= size:
                    shutdown_event.set()
                    break

                await trio.sleep(0.5)

        nursery.start_soon(monitor_completion)

    log.info("All requests completed!")

if __name__ == "__main__":
    trio.run(main, restrict_keyboard_interrupt_to_checkpoints=True)
