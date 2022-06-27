import datetime, random
import numpy as np
import sys, time
import json
from concurrent import futures
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QInputDialog, QTextBrowser, \
    QHBoxLayout, QPushButton, QGridLayout, QSlider
from PyQt5.QtCore import Qt

import grpc
import experimentservice_pb2 as pb
import experimentservice_pb2_grpc as rpc

from enums.commands import Command
from enums.status import Status

from experiment_service import ExperimentServer

from wrapper.dummy_wrapper import DummyWrapper

from bots.RandomAgent import RandomAgent as Bot

class ServerApp(QWidget):

    def __init__(self):
        super().__init__()

        self.config = {
            'level': 'asymmetric_advantages',
            'duration': 120,
            'player': 'Bot',
            'bot_apm': 80
        }

        self._game_screen = np.zeros((600, 800, 3), dtype=np.uint8)

        self.game_wrapper = DummyWrapper()
        self.game_wrapper.on_action(self._on_human_action)
        self.game_wrapper.on_close(self.close)

        self._bot_last_action = None
        self.bot_instance = Bot()

        self.initUI()

    def _start_service(self):

        port = 11912

        self.server_manager = ExperimentServer()
        self.server_manager.on_client_connected(self.on_client_connected)
        self.server_manager.on_game_sync(self.on_game_sync)
        self.server_manager.on_client_timeout(self.on_client_timeout)

        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        rpc.add_ExperimentServiceServicer_to_server(self.server_manager, self.server)

        self.server.add_insecure_port('[::]:' + str(port))
        self.server.start()

        self.add_log('Starting server. Listening...')

    def _stop_service(self):
        self.server.stop(grace=True)
        self.server_manager.stop()

        if hasattr(self, 'server_manager'):
            del self.server_manager
        self.change_status(Status.Disconnected)
        self.add_log('Stopping server')

    def on_client_timeout(self):
        self._stop_service()
        time.sleep(0.1)
        self._start_service()

    def add_log(self, text):
        self.tb.append('[' + str(datetime.datetime.now()) + '] ' + text)

    def on_client_connected(self, peer):
        self.add_log('Client connected from ' + str(peer))
        self.change_status(Status.Waiting)
        self.sync_config()

    def on_game_sync(self, data):
        image = np.frombuffer(data.screen, dtype=np.uint8).reshape(600, 800, 3)
        self.game_wrapper.set_image(image)

        if self.status_lbl.text() == Status.Progressing:
            self.on_frame_received(image)

    def on_frame_received(self, obs):

        if self.config['player'] == 'Bot':
            if self._bot_last_action is None or (time.time() - self._bot_last_action > self.action_time_gap):
                self._on_request_bot_action(obs)
                self._bot_last_action = time.time()

    def _on_request_bot_action(self, obs):
        action = self.bot_instance.get_action(obs=obs)
        self._on_human_action(action)

    def _on_botapm_changed(self, value):
        self.config['bot_apm'] = value
        self.bot_apm_lbl.setText(str(self.config['bot_apm']))

    def sync_config(self):
        state = pb.State()
        state.command = Command.ChangeConfig
        state.payload = json.dumps(self.config)
        self.server_manager.control_client(state)

    def _on_config_changed(self):
        self.level_lbl.setText(self.config['level'])
        self.duration_lbl.setText(str(self.config['duration']))
        self.player_lbl.setText(self.config['player'])

        self.add_log(f'Configuration changed (level: {str(self.config["level"])}, ' +
                     f'duration: {str(self.config["duration"])}, player: {str(self.config["player"])})')

    def _on_change_game_level_pressed(self):
        text, ok = QInputDialog.getText(self, 'Level', 'Enter Level:')

        if ok and text != '':
            self.config['level'] = text
            self._on_config_changed()
            self.sync_config()

    def _on_change_game_duration_pressed(self):
        text, ok = QInputDialog.getInt(self, 'Duration', 'Enter Duration:')

        if ok:
            self.config['duration'] = text
            self._on_config_changed()
            self.sync_config()

    def _on_change_game_player_pressed(self):
        if self.config['player'] == 'Bot':
            self.config['player'] = 'Human'
        else:
            self.config['player'] = 'Bot'

        self._on_config_changed()
        self.sync_config()

    def change_status(self, state: str):
        self.status_lbl.setText(state)
        self._on_status_changed(state)

    def _on_status_changed(self, state: str):
        if state == Status.Disconnected:
            self.btn_disconnect.setEnabled(False)
            self.btn_start_game.setEnabled(False)
            self.btn_abort_game.setEnabled(False)
        elif state == Status.Connected:
            self.btn_start_game.setEnabled(True)
            self.btn_disconnect.setEnabled(True)
        elif state == Status.Progressing:
            self.btn_start_game.setEnabled(False)
            self.btn_abort_game.setEnabled(True)
        elif state == Status.Waiting:
            self.btn_disconnect.setEnabled(True)
            self.btn_start_game.setEnabled(True)
            self.btn_abort_game.setEnabled(False)
            self._bot_last_action = None

    def _on_game_start_pressed(self):
        state = pb.State()
        state.command = Command.StartGame
        self.server_manager.control_client(state)
        self.change_status(Status.Progressing)

        self.add_log('Started an experiment with below config')
        self.add_log(f'Config - (level: {str(self.config["level"])}, ' +
                     f'duration: {str(self.config["duration"])}, player: {str(self.config["player"])})')

    def _on_game_abort_pressed(self):
        state = pb.State()
        state.command = Command.AbortGame
        self.server_manager.control_client(state)
        self.change_status(Status.Waiting)

        self.add_log('Stopped the progressing experiment')

    def _on_log_clear_pressed(self):
        self.tb.clear()

    def _on_disconnect_pressed(self):
        state = pb.State()
        state.command = Command.Disconnect
        self.server_manager.control_client(state)
        self.change_status(Status.Disconnected)
        self.add_log('Client disconnected by server')

    def _create_button(self, text: str, on_clicked):
        btn = QPushButton()
        btn.setText(text)
        if on_clicked is not None:
            btn.clicked.connect(on_clicked)
        return btn

    def _on_human_action(self, action: int):
        state = pb.State()
        state.command = Command.KeyInput
        state.payload = str(action)
        self.server_manager.control_client(state)

    def initUI(self):

        # t1 = threading.Thread(target=self._render_game_loop, args=(self, ))
        # t1.start()

        self.status_lbl = QLabel()
        self.level_lbl = QLabel(self.config['level'])
        self.duration_lbl = QLabel(str(self.config['duration']))
        self.player_lbl = QLabel(self.config['player'])
        self.bot_apm_lbl = QLabel(str(self.config['bot_apm']))
        self.bot_apm_lbl.setAlignment(Qt.AlignCenter)

        self.tb = QTextBrowser()
        self.tb.setOpenExternalLinks(True)
        self.tb.setFixedWidth(400)

        hbox = QHBoxLayout()

        control_box = QVBoxLayout()
        grid = QGridLayout()

        grid.addWidget(QLabel('Status:'), 0, 0)
        grid.addWidget(QLabel('Level:'), 1, 0)
        grid.addWidget(QLabel('Duration:'), 2, 0)
        grid.addWidget(QLabel('Player:'), 3, 0)
        grid.addWidget(QLabel('Bot APM:'), 4, 0)

        grid.addWidget(self.status_lbl, 0, 1)
        grid.addWidget(self.level_lbl, 1, 1)
        grid.addWidget(self.duration_lbl, 2, 1)
        grid.addWidget(self.player_lbl, 3, 1)
        grid.addWidget(self.bot_apm_lbl, 4, 2)

        self.btn_disconnect = self._create_button(text='Disconnect', on_clicked=self._on_disconnect_pressed)

        btn_level_change = self._create_button(text='Change', on_clicked=self._on_change_game_level_pressed)
        btn_duration_change = self._create_button(text='Change', on_clicked=self._on_change_game_duration_pressed)
        btn_player_change = self._create_button(text='Toggle', on_clicked=self._on_change_game_player_pressed)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(50, 300)
        slider.setSingleStep(5)
        slider.valueChanged.connect(self._on_botapm_changed)
        slider.setValue(self.config['bot_apm'])

        grid.addWidget(self.btn_disconnect, 0, 2)
        grid.addWidget(btn_level_change, 1, 2)
        grid.addWidget(btn_duration_change, 2, 2)
        grid.addWidget(btn_player_change, 3, 2)
        grid.addWidget(slider, 4, 1)


        control_box.addLayout(grid)

        self.btn_start_game = self._create_button(text='Start', on_clicked=self._on_game_start_pressed)
        self.btn_abort_game = self._create_button(text='Abort', on_clicked=self._on_game_abort_pressed)

        control_box.addWidget(self.btn_start_game)
        control_box.addWidget(self.btn_abort_game)

        control_box.addWidget(QLabel('Log'))
        control_box.addWidget(self.tb)

        btn_clear_log = self._create_button(text='Clear', on_clicked=self._on_log_clear_pressed)
        control_box.addWidget(btn_clear_log)
        hbox.addStretch(5)
        hbox.addLayout(control_box)
        hbox.addStretch(5)

        self.setLayout(hbox)

        self.setWindowTitle('Turing-test Experiment Server')

        self.move(0, 300)
        self.show()

        self.change_status(Status.Disconnected)
        self._start_service()

    def closeEvent(self, event):
        self.game_wrapper.stop()
        self._stop_service()

    @property
    def action_time_gap(self):
        return 60 / self.config['bot_apm']


if __name__ == '__main__':
   app = QApplication(sys.argv)
   ex = ServerApp()
   sys.exit(app.exec_())
