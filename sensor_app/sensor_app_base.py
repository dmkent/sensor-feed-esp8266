"""Abstract feed handler."""

class SensorApplication:
    DEFAULT_EVENT_PERIOD = 300 # seconds

    def __init__(self, event_periods, debug):
        """Setup the application"""
        self._events = []

        self.should_bail = False
        self.debug = debug
        self.event_periods = event_periods

    def log(self, current_time, message):
        """Simple logging to stout."""
        if self.debug:
            print(self.localtime(current_time), message)

    def event_schedule_dtime(self, dtime, event):
        """
            Add a new event to the queue to be triggered at specific date/time.
        
            Trigger date/time is specified in epoch seconds. i.e. response from
            ``utime.time()``.
        """
        self._events.append((dtime, event))

    def event_schedule_offset(self, offset_secs, event):
        """
            Add a new event to the queue to be triggered ``offset_secs`` from current time.
        """
        dtime_secs = self.time() + offset_secs
        self._events.append((dtime_secs, event))

    def event_period(self, value):
        """Look-up period in event_periods, default if not found."""
        return self.event_periods.get(value, self.DEFAULT_EVENT_PERIOD)

    def run(self):
        """Main event loop. Will run loop until ``should_bail`` is True."""
        self.should_bail = False
        while not self.should_bail:
            self.loop()

    def loop(self):
        """The inner-event loop."""
        # Do house-keeping
        self.pre_event_handler()

        # Get current time
        current_time = self.time()

        # loop over list of pending events
        triggered = []
        for i in range(len(self._events)):
            # if current time greater than event trigger time then
            # trigger event
            if self._events[i][0] <= current_time:
                # call the event callback.
                self._events[i][1](current_time)
                triggered.append(i)

        # remove handled events
        for i in triggered[::-1]:
            del self._events[i]       

        # sleep a bit
        self.sleep(1)

    def time(self):
        """Get current time."""
        raise NotImplementedError

    def sleep(self, seconds):
        """Delay for seconds."""
        raise NotImplementedError

    def localtime(self, timeval):
        """Format timeval as localtime struct."""
        raise NotImplementedError

    def init_events(self):
        """Trigger initial events."""
        pass

    def pre_event_handler(self):
        """Perform any housekeeping in event loop."""
        pass