if __name__ == "__main__":
	from sys import path as sp
	from os import path
	sp.append(path.abspath(path.join(path.dirname(__file__), '..')))
import modules.state as state
from logging import getLogger
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QSpinBox, QVBoxLayout

logger = getLogger(__name__)

class delayGUI(QDialog):
	def __init__(self):
		self.logger = getLogger(__name__)
		if (obj := state.openGUIs.get("delay", None)) is not None:
			obj.raise_()
			obj.activateWindow()
			return self.logger.debug("Delay window opened more than once. Refocussed on older window")
		super().__init__(state.clock)
		loc = state.settings.localization
		self.setWindowTitle(loc.delaySetting.title)
		layout = QVBoxLayout(self)
		layout.addWidget(QLabel(loc.delaySetting.label))
		self.delaySpin = QSpinBox(self)
		self.delaySpin.setRange(-3600, 3600)
		self.delaySpin.setValue(state.settings.schedule.delay)
		layout.addWidget(self.delaySpin)
		layout.addWidget(QLabel(loc.delaySetting.help))
		saveBtn = QPushButton(loc.delaySetting.btn)
		saveBtn.clicked.connect(self.saveValue)
		layout.addWidget(saveBtn)
		state.openGUIs["delay"] = self
		self.show()
		self.raise_()
		self.activateWindow()
	def saveValue(self):
		state.settings.schedule.delay = self.delaySpin.value()
		state.settings.schedule.save()
		self.closeWindow()
	def closeWindow(self):
		state.openGUIs.pop("delay", None)
		self.close()
	def closeEvent(self, event):
		state.openGUIs.pop("delay", None)
		super().closeEvent(event)
