if __name__ == "__main__":
	from sys import path as sp
	from os import path
	sp.append(path.abspath(path.join(path.dirname(__file__), '..')))
import modules.state as state
from logging import getLogger
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from datetime import datetime

class scheduleGUI(QWidget):
	def __init__(self):
		self.logger = getLogger(__name__)
		if (obj := state.openGUIs.get("schedule", None)) is not None:
			obj.raise_()
			obj.activateWindow()
			return self.logger.debug("Schedule opened more than once. Refocussed on older schedule window")
		super().__init__()
		self.setWindowTitle("Schedule")
		layout = QVBoxLayout(self)
		layout.addWidget(QLabel("Fullscreen schedule is not implemented yet."))
		state.openGUIs["schedule"] = self
		self.show()
	def closeEvent(self, event):
		state.openGUIs.pop("schedule", None)
		super().closeEvent(event)
