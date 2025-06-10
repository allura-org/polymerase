from result import Result, Ok, is_ok
from http_client import AsyncHttpClient
import trio
from primitives import AsyncKVStore, AsyncQueue
from messages import Request
from config import Config
from logbar import LogBar
from logbar.progress import ProgressBar
from datasets import load_dataset
from output import save_requests

@Result.resultify_async
async def worker(http_client: AsyncHttpClient, kv_store: AsyncKVStore[str, int], input_queue: AsyncQueue[Request], output_queue: AsyncQueue[Request], log: LogBar, pb: ProgressBar, config: Config):
    while True:
        request = await input_queue.dequeue()
        response = await request.unwrap().req(http_client, config.api.model)
        if is_ok(response):
            await output_queue.enqueue(response.unwrap())
            await kv_store.set("requests_completed", (await kv_store.get("requests_completed")).unwrap() + 1)
            pb.next()
            pb.draw()
        else:
            log.error(f"Failed to process request, readding to input queue: {response.unwrap_err()}")
            await input_queue.enqueue(request.unwrap())

@Result.resultify_async
async def output_worker(output_queue: AsyncQueue[Request], kv_store: AsyncKVStore[str, int], config: Config, log: LogBar, total_requests: int):
    """Worker that collects completed requests and saves them to file"""
    completed_requests = []
    
    while True:
        # Check if all requests are completed
        completed_count = (await kv_store.get("requests_completed")).unwrap()
        
        # Collect all available requests from output queue
        while (await output_queue.size()).unwrap() > 0:
            request = await output_queue.dequeue()
            completed_requests.append(request.unwrap())
        
        # If we have all requests, save and exit
        if completed_count >= total_requests and len(completed_requests) == total_requests:
            if config.output is not None:
                log.info("Saving output data...")
                save_result = save_requests(completed_requests, config)
                if save_result._error is None:
                    log.info(f"Successfully saved {len(completed_requests)} requests to {config.output.path}")
                else:
                    log.error(f"Failed to save output: {save_result.unwrap_err()}")
            break
        
        # Small delay to avoid busy waiting
        await trio.sleep(0.1)

async def main() -> Result[None]:
    config = Config.from_toml("./config.toml").unwrap()
    http_client = AsyncHttpClient(base_url=config.api.base_url, headers={"Authorization": f"Bearer {config.api.api_key}"})
    kv_lock = trio.Lock()
    queue_lock = trio.Lock()
    output_lock = trio.Lock()
    kv_store = AsyncKVStore[str, int](default_value=0, lock=kv_lock)
    input_queue = AsyncQueue[Request](lock=queue_lock)
    output_queue = AsyncQueue[Request](lock=output_lock)
    log = LogBar(name="main")

    ds = load_dataset(config).unwrap()
    for request in ds:
        await input_queue.enqueue(request)
    
    size = (await input_queue.size()).unwrap()
    log.info(f"Queued {size} requests")
    pb = log.pb(range(size)).subtitle("Processing requests")
    pb.draw()

    async with trio.open_nursery() as nursery:
        # Start worker processes
        for _ in range(config.processes.parallel):
            nursery.start_soon(worker, http_client, kv_store, input_queue, output_queue, log, pb, config)
        
        # Start output worker if output config is provided
        if config.output is not None:
            nursery.start_soon(output_worker, output_queue, kv_store, config, log, size)

    # Cursor, trio automatically joins the nursery. We don't need to do anything here.

    log.info("All requests completed!")

    return Ok(None)

if __name__ == "__main__":
    trio.run(main, restrict_keyboard_interrupt_to_checkpoints=True) # type: ignore // what the fuck?