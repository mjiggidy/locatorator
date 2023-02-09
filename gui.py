from PySide6 import QtWidgets, QtCore, QtGui
import sys, pathlib, typing
import locatorator

class MarkerViewer(QtWidgets.QTreeWidget):

	def __init__(self):
		super().__init__()

		self._setup()
	
	def _setup(self):

		self.setHeaderLabels(
			[
				"Shot ID",
				"Old TC",
				"New TC",
				"Offset"
			]
		)
		self.setAlternatingRowColors(True)
		self.setSortingEnabled(True)

class InputFileChooser(QtWidgets.QWidget):

	sig_path_changed = QtCore.Signal(str)

	def __init__(self, label:str=""):
		super().__init__()

		self._layout = QtWidgets.QGridLayout()
		self._lbl_label = QtWidgets.QLabel(label)
		self._txt_filepath = QtWidgets.QLineEdit()
		self._btn_browse = QtWidgets.QPushButton(text="...")

		self._setup()

	def _setup(self):

		self.setLayout(self._layout)
		self.layout().setContentsMargins(0,0,0,0)
		self.setAcceptDrops(True)

		self.layout().addWidget(self._lbl_label, 0, 0)
		self.layout().addWidget(self._txt_filepath, 1, 0)
		self.layout().addWidget(self._btn_browse, 1, 1)

		self._txt_filepath.textChanged.connect(lambda:self.sig_path_changed.emit(self.get_specified_path()))
		self._btn_browse.clicked.connect(self._set_specified_path_from_browser)

	def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:

		if event.mimeData().hasFormat("text/uri-list"):
			self._txt_filepath.setFocus()
			event.acceptProposedAction()

	def dropEvent(self, event:QtGui.QDropEvent) -> None:
		event.acceptProposedAction()
		try:
			dropped_path = event.mimeData().text()
			if dropped_path.startswith("file://"):
				dropped_path = dropped_path[len("file://"):]
			self._txt_filepath.setText(str(pathlib.Path(dropped_path)))
		except:
			pass
	
	def _set_specified_path_from_browser(self) -> None:
		self._txt_filepath.setFocus()
		new_path = QtWidgets.QFileDialog.getOpenFileName(self, "Choose a marker list...", self.get_specified_path(), "Marker Lists (*.txt);;All Files (*)")[0]
		self._txt_filepath.setText(new_path or self._txt_filepath.text())
	
	def get_specified_path(self) -> str:
		"""Get the path chosen by the user"""
		return self._txt_filepath.text().strip()
	
class InputListGroup(QtWidgets.QGroupBox):

	sig_paths_chosen = QtCore.Signal(str, str)

	def __init__(self):
		super().__init__()

		self._layout = QtWidgets.QVBoxLayout()
		self._input_old_markers = InputFileChooser(label="Old Markers:")
		self._input_new_markers = InputFileChooser(label="New Markers:")
		self._btn_compare = QtWidgets.QPushButton()

		self._setup()

	def _setup(self):

		self.setLayout(self._layout)

		self.layout().addWidget(self._input_old_markers)
		self.layout().addWidget(self._input_new_markers)

		self._btn_compare.setText("Compare Marker Lists")
		self._btn_compare.setEnabled(False)
		self.layout().addWidget(self._btn_compare)

		self._input_old_markers.sig_path_changed.connect(self._paths_changed)
		self._input_new_markers.sig_path_changed.connect(self._paths_changed)

		self._btn_compare.clicked.connect(
			lambda:self.sig_paths_chosen.emit(*self.get_specified_paths()))
	
	def get_specified_paths(self) -> typing.Tuple[str,str]:
		"""Get the paths currently chosen"""
		return (self._input_old_markers.get_specified_path(), self._input_new_markers.get_specified_path())

	
	def _paths_changed(self):
		"""Inform the people"""
		path_old = self._input_old_markers.get_specified_path()
		path_new = self._input_new_markers.get_specified_path()
		self._btn_compare.setEnabled(bool(path_old and path_new))




class MainWidget(QtWidgets.QWidget):

	def __init__(self):
		super().__init__()

		self._layout = QtWidgets.QVBoxLayout()
		self._grp_list_inputs = InputListGroup()
		self._tree_viewer = MarkerViewer()

		self._locked = False
		self._path_old = pathlib.Path()
		self._path_new = pathlib.Path()

		self._setup()
	
	def _setup(self):

		self.setLayout(self._layout)
		self.layout().addWidget(self._grp_list_inputs)
		self.layout().addWidget(self._tree_viewer)

		self._grp_list_inputs.sig_paths_chosen.connect(self._set_paths)
	
	def _set_paths(self, path_old:str, path_new:str):

		self._path_old = pathlib.Path(path_old)
		self._path_new = pathlib.Path(path_new)

		with self._path_old.open() as file_old:
			markers_old = locatorator.get_marker_list_from_file(file_old)

		with self._path_new.open() as file_new:
			markers_new = locatorator.get_marker_list_from_file(file_new)
		
		changes = locatorator.build_marker_changes(markers_old, markers_new)

		for marker_old, marker_new, _ in changes:

			self._tree_viewer.addTopLevelItem(QtWidgets.QTreeWidgetItem([
				marker_new.comment,
				str(marker_old.timecode.start),
				str(marker_new.timecode.start),
				str(marker_new.timecode.start-marker_old.timecode.start)
			]))
	
class MainWindow(QtWidgets.QMainWindow):
	 
	def __init__(self):
		super().__init__()

		self.wdg_main = MainWidget()

		self._setup()
	
	def _setup(self) -> None:
		"""Setup the main window"""

		self.setCentralWidget(self.wdg_main)
		self.setWindowTitle("Locatorator")
		self.setMinimumWidth(500)



def main():
	app = QtWidgets.QApplication(sys.argv)

	wnd_main = MainWindow()
	wnd_main.show()

	return app.exec()

if __name__ == "__main__":

	sys.exit(main())