import datetime
import sys, threading
import json
import time

from PyQt5.QtWidgets import QDesktopWidget, QInputDialog, QApplication, QWidget, QLabel, QVBoxLayout, \
    QHBoxLayout, QPushButton, QGridLayout, QTextBrowser


import grpc
import experimentservice_pb2 as pb
import experimentservice_pb2_grpc as rpc

from wrapper.gym_wrapper import GymWrapper

from utils.infinite_iterator import InfiniteIterator


from enums.commands import Command
from enums.status import Status


class ClientApp(QWidget):

    def __init__(self):
        super().__init__()

        self.game_screen = None
        self.config = {
            'level': 'asymmetric_advantages',
            'duration': 120,
            'player': 'Bot'
        }

        self._current_screen = None
        self.conn = None
        self.connect_listener = None
        self.thr_heartbeat = None

        self.inf_iterator = InfiniteIterator()

        self.initUI()
        self.game_wrapper = GymWrapper()
        self.game_wrapper.on_close(self.close)


    def on_connect_pressed(self):
        text, ok = QInputDialog.getText(self, 'Connect', 'Enter IP Address:')

        if text != '':
            address = text
        else:
            address = 'localhost'

        port = 11912

        if ok:
            self.add_log(f'Connecting to {address}:{port}')
            self._on_status_changed(Status.Connecting)

            channel = grpc.insecure_channel(address + ':' + str(port))

            self.conn = rpc.ExperimentServiceStub(channel)

            def connect_on_background():
                try:
                    grpc.channel_ready_future(channel).result(timeout=10)
                    is_connected = True
                except grpc.FutureTimeoutError:
                    is_connected = False

                if not is_connected:
                    self.disconnect_server()
                    return

                # create new listening thread for when new message streams come in
                self.command_listener = threading.Thread(target=self._listen_for_messages, daemon=False)
                self.command_listener.start()

                self.thr_heartbeat = threading.Thread(target=self._heart_beat, daemon=False)
                self.thr_heartbeat.start()

                self._on_status_changed(Status.Connected)
                self.add_log(f'Connected to {address}:{port}')

                # Threading
                self.thr_rendering = threading.Thread(target=self._render_game_loop, args=(self,))
                self.thr_rendering.start()

                self.thr_syncgame = threading.Thread(target=self._send_game_screen, args=(self,))
                self.thr_syncgame.start()

            t1 = threading.Thread(target=connect_on_background, daemon=False)
            t1.start()

    def _heart_beat(self):
        while True:
            if self.conn is not None:
                try:
                    self.conn.HealthCheck(pb.Empty())
                except:
                    pass
            time.sleep(0.1)

    def _listen_for_messages(self):

        try:
            for state in self.conn.ServerSignal(pb.Empty()):  # this line will wait for new messages from the server!

                if state.command == Command.ChangeConfig:
                    self.change_config(json.loads(state.payload))

                elif state.command == Command.StartGame:
                    self.start_game()
                    self.status_lbl.setText(Status.Progressing)

                elif state.command == Command.AbortGame:
                    self.abort_game()
                    self.status_lbl.setText(Status.Connected)
                    self.add_log('Game aborted by server')
                elif state.command == Command.KeyInput:
                    self.game_wrapper.remote_action(int(state.payload))

                elif state.command == Command.Disconnect:
                    self.disconnect_server()
                    self.add_log('Disconnected by server')
                    break
        except:
            self.disconnect_server()

    def change_config(self, config):
        old_config = self.config
        self.config = config

        if old_config['duration'] != self.config['duration']:
            self.duration_lbl.setText(str(self.config['duration']))
            self.add_log(f'Config changed (duration: {old_config["duration"]}->{config["duration"]})')

        self.game_wrapper.set_duration(self.config['duration'])
        self.game_wrapper.set_level(self.config['level'])

    def _on_status_changed(self, state: str):
        if state == Status.Disconnected:
            self.btn_connect.setEnabled(True)
            self.btn_connect.show()
            self.btn_disconnect.hide()
            self.status_lbl.setText(Status.Disconnected)
        elif state == Status.Connecting:
            self.btn_connect.hide()
            self.btn_disconnect.show()
            self.status_lbl.setText(Status.Connecting)
        elif state == Status.Connected:
            self.btn_connect.setEnabled(False)
            self.status_lbl.setText(Status.Connected)
        elif state == Status.Progressing:
            self.status_lbl.setText(Status.Progressing)

    def _on_log_clear_pressed(self):
        self.log_tb.clear()

    def start_game(self):
        self.add_log('Starting an experiment')
        self.game_wrapper.start_game()

    def abort_game(self):
        self.game_wrapper.abort_game()

    def disconnect_server(self):
        self.conn = None
        self.server = None

        self._on_status_changed(Status.Disconnected)

        if hasattr(self, 'thr_syncgame'):
            del self.thr_syncgame
        if hasattr(self, 'thr_rendering'):
            del self.thr_rendering

    def add_log(self, text):
        self.log_tb.append('[' + str(datetime.datetime.now()) + '] ' + text)

    def _create_button(self, text: str, on_clicked):
        btn = QPushButton()
        btn.setText(text)
        if on_clicked is not None:
            btn.clicked.connect(on_clicked)
        return btn

    def _on_disconnect_pressed(self):
        self.disconnect_server()
        self.add_log('Disconnected by user')


    def initUI(self):


        self.status_lbl = QLabel(Status.Disconnected)
        self.level_lbl = QLabel(self.config['level'])
        self.duration_lbl = QLabel(str(self.config['duration']))

        self.log_tb = QTextBrowser()
        self.log_tb.setOpenExternalLinks(True)
        self.log_tb.setFixedWidth(300)

        grid = QGridLayout()

        grid.addWidget(QLabel('Status:'), 0, 0)
        grid.addWidget(QLabel('Duration:'), 1, 0)

        grid.addWidget(self.status_lbl, 0, 1)
        grid.addWidget(self.duration_lbl, 1, 1)

        self.btn_disconnect = self._create_button(text='Disconnect', on_clicked=self._on_disconnect_pressed)
        self.btn_connect = self._create_button(text='Connect', on_clicked=self.on_connect_pressed)

        grid.addWidget(self.btn_connect, 0, 2)
        grid.addWidget(self.btn_disconnect, 0, 2)

        self.btn_disconnect.hide()
        hbox = QHBoxLayout()

        control_box = QVBoxLayout()
        control_box.addLayout(grid)
        control_box.addWidget(QLabel('Log'))
        control_box.addWidget(self.log_tb)

        btn_clear_log = self._create_button(text='Clear', on_clicked=self._on_log_clear_pressed)
        control_box.addWidget(btn_clear_log)
        hbox.addStretch(5)
        hbox.addLayout(control_box)
        hbox.addStretch(5)

        self.setLayout(hbox)

        self.setWindowTitle('Turing-test Experiment Client')

        self.move(QDesktopWidget().availableGeometry().width() - 320, 300)
        self.show()

    def _load_game_level(self, level: str):
        # TODO Implement load a game level in pygame.
        print('on_level_changed', level)

    def _render_game_loop(self, window_context):

        while True:
            if not hasattr(self, 'game_wrapper'): continue
            image = self.game_wrapper.render()
            gs = pb.GameSync()
            gs.screen = image.tobytes()
            window_context.inf_iterator.set_value(gs)

    def _send_game_screen(self, window_context):
        def get_val():
            yield self.inf_iterator.get_value()

        while True:
            if self.inf_iterator.is_null() == False and self.conn is not None:
                try:
                    self.conn.GameSyncSignal(get_val())
                except:
                    self._on_status_changed(Status.Disconnected)
                    break

    def closeEvent(self, event):
        self.game_wrapper.stop()
        self.disconnect_server()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ClientApp()
    sys.exit(app.exec_())
