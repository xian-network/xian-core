import asyncio

class ProcessingQueue:
    def __init__(self):
        self.running = False
        self.paused = False
        self.allow_append = True
        self.currently_processing = False

        self.queue = []

    def __len__(self):
        return len(self.queue)

    def __getitem__(self, index):
        try:
            return self.queue[index]
        except IndexError:
            return None

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def pause(self):
        self.paused = True

    def unpause(self):
        self.paused = False

    def disable_append(self):
        self.allow_append = False

    def enable_append(self):
        self.allow_append = True

    def start_processing(self):
        self.currently_processing = True

    def stop_processing(self):
        self.currently_processing = False

    @property
    def active(self):
        return self.running and not self.paused

    async def stopping(self):
        while self.currently_processing:
            await asyncio.sleep(0.1)

    async def pausing(self):
        while self.currently_processing:
            await asyncio.sleep(0.1)

    def flush(self):
        self.queue = []

    def append(self, item):
        self.queue.append(item)

    async def process_next(self):
        raise NotImplementedError