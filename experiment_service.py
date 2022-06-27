from collections import deque
import time, threading

import experimentservice_pb2 as pb
import experimentservice_pb2_grpc as rpc


class ExperimentServer(rpc.ExperimentServiceServicer):  # inheriting here from the protobuf rpc file which is generated

    def __init__(self):
        self.state_queue = deque()

        self._on_client_connected = None
        self._on_client_timeout = None
        self._on_game_sync = None

        self._latest_hit = None
        self._check_timeout()

    def stop(self):
        self._run_check = False

    def _check_timeout(self):
        self._run_check = True
        def _update_time():
            while self._run_check:
                if self._latest_hit is not None:
                    if time.time() - self._latest_hit > 2:
                        self._on_client_timeout()
                time.sleep(0.1)

        t1 = threading.Thread(target=_update_time, daemon=False)
        t1.start()

    def on_client_connected(self, callback):
        self._on_client_connected = callback

    def on_client_timeout(self, callback):
        self._on_client_timeout = callback

    def on_game_sync(self, callback):
        self._on_game_sync = callback

    def ServerSignal(self, request: pb.Empty, context):

        self._on_client_connected(context.peer())

        while True:
            if len(self.state_queue):
                state = self.state_queue.popleft()
                yield state
            else:
                time.sleep(0.01)

    def GameSyncSignal(self, request_iterator: pb.GameSync, context):
        for game_sync in request_iterator:  # this line will wait for new messages from the server!
            self._on_game_sync(game_sync)
        return pb.Empty()

    def HealthCheck(self, request: pb.Empty, context):
        self._latest_hit = time.time()
        return pb.Empty()

    def control_client(self, state: pb.State):
        self.state_queue.append(state)
