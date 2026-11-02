from json import load as jload, dump as jdump
from pathlib import Path
from logging import getLogger
from typing import Literal
from hashlib import sha1

class DuplicateError(BaseException): 
	pass
class CodeMissingError(BaseException):
	pass

ClassKey = Literal["room", "teacher", "name"]
CLASS_KEYS = {"room", "teacher", "name"}

class Classes(dict):
	# NOTE: Changes are only temporary until save() is called explicitly
	def __init__(self):
		self._logger = getLogger(__name__)
		self.path = Path("config") / "classes.json"
		self.path.parent.mkdir(parents=True, exist_ok=True)
		if (not self.path.exists()):
			self._logger.warning("Class list file not found, creating default.")
			data = {}
			self.save()
		else:
			with open(self.path, "r", encoding="utf-8") as f:
				data = jload(f)
				self._logger.info("Class list loaded")
		super().__init__(data)

	def __genKey(self, **data:str):
		return str(sha1(f"{data["name"].strip().lower()}\0{data["room"].strip().lower()}\0{data["teacher"].strip().lower()}"))

	def save(self):
		with self.path.open("w", encoding="utf-8") as f:
			jdump(self, f, indent=4, ensure_ascii=False)

	def __rename(self, old_code:str):
		if old_code not in self:
			raise CodeMissingError(f"Old class ID '{old_code}' does not exist")
		data = self[old_code]
		new_code = self.__genKey(data)
		self.add(new_code, **data)
		self.remove(old_code)

	def add(self, **data:str):
		code = self.__genKey(**data)
		if code in self:
			raise DuplicateError(f"Class '{code}' already exists")
		self[code] = data

	def set(self, _class:str, key:ClassKey, value:str):
		if key not in CLASS_KEYS:
			raise ValueError(f"Invalid class key: {key}")
		if _class not in self:
			raise CodeMissingError(f"Class '{_class}' does not exist")
		self[_class][key] = value
		self.__rename(_class)

	def remove(self, _class:str):
		if _class not in self:
			raise CodeMissingError(f"Class '{_class}' does not exist")
		self.pop(_class)