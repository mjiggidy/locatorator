from PySide6 import QtWidgets, QtCore, QtGui
from posttools import timecode
import sys, pathlib, typing
import locatorator

MARKER_COMMENT_COLUMN_NAME = "Shot ID"
EXPORT_TRACK_OPTIONS = ("TC1","V1","V2","V3","V4","V5","V6","V7","V8")
EXPORT_DEFAULT_MARKER_NAME = "Locatorator"
EXPORT_DEFAULT_MARKER_COLOR = "white"

class MarkerIcons:

	sig_new_icon_created = QtCore.Signal(str)
	icons = {}

	@classmethod
	def prepare_icon(cls, marker_color:str):
		"""Draw marker icon"""
		
		pm = QtGui.QPixmap(64, 64)
		pm.fill(QtGui.QColor(0,0,0,0))

		painter = QtGui.QPainter(pm)
		color   = QtGui.QColor(marker_color)
		painter.setBrush(QtGui.QBrush(color))
		painter.drawEllipse(0, 0, pm.width(), pm.height())
		painter.end()

		cls.icons[marker_color] = QtGui.QIcon(pm.scaledToHeight(6, QtCore.Qt.TransformationMode.SmoothTransformation))
	#	cls.sig_new_icon_created.emit(marker_color)

class MarkerViewer(QtWidgets.QTreeWidget):

	sig_changes_ready = QtCore.Signal()

	def __init__(self):
		super().__init__()

		self._headerlabels=[
			MARKER_COMMENT_COLUMN_NAME,
			"Old TC",
			"New TC",
			"Offset"
		]

		self._setup()
	
	def _setup(self):

		self.setIndentation(0)
		self.setHeaderLabels(self._headerlabels)
		self.setAlternatingRowColors(True)
		self.setUniformRowHeights(True)
		self.setSortingEnabled(True)

	def set_changelist(self, markers_changes:typing.Iterable[typing.Tuple[locatorator.Marker, locatorator.Marker, timecode.Timecode]]) -> None:

		self.clear()

		changelist = []

		for marker_old, marker_new, relative_offset in markers_changes:

			marker_comment = marker_old.comment if marker_old else marker_new.comment
			tc_old = str(marker_old.timecode.start) if marker_old else ""
			tc_new = str(marker_new.timecode.start) if marker_new else ""
			change = ""
			
			if marker_old and marker_new:
				change = str(relative_offset)
				if relative_offset > 0:
					change = "+" + change
			
			elif marker_old:
				change = "Shot Removed"
			
			else:
				change = "Shot Added"

			changelist_item = QtWidgets.QTreeWidgetItem([
				marker_comment,
				tc_old,
				tc_new,
				change				
			])

			for idx, header in enumerate(self._headerlabels):
				if header != MARKER_COMMENT_COLUMN_NAME:
					changelist_item.setTextAlignment(idx, QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignCenter)
			
			changelist_item.setIcon(0, MarkerIcons.icons.get(marker_new.color.name.lower() if marker_new else marker_old.name.lower(), "red"))
			
			changelist.append(changelist_item)

		self.addTopLevelItems(changelist)
		
		for idx, header in enumerate(self._headerlabels):
			if header != MARKER_COMMENT_COLUMN_NAME:
				self.resizeColumnToContents(idx)

		self.sortByColumn(self._headerlabels.index("New TC"), QtCore.Qt.SortOrder.AscendingOrder)

		self.sig_changes_ready.emit()

class OutputFileGroup(QtWidgets.QGroupBox):
	"""Marker list export groupbox"""

	sig_export_requested = QtCore.Signal(str, locatorator.MarkerColors, str, str)
	"""User has requested an export"""

	sig_export_canceled = QtCore.Signal()
	"""Export did not complete"""
	sig_export_complete = QtCore.Signal(str)

	def __init__(self):
		super().__init__()

		self._layout = QtWidgets.QHBoxLayout()
		self._cmb_color = QtWidgets.QComboBox()
		self._cmb_track = QtWidgets.QComboBox()
		self._btn_export = QtWidgets.QPushButton()
		self._txt_name = QtWidgets.QLineEdit()
	
		self._setup()

	def _setup(self):

		self.setLayout(self._layout)
		
		for color in MarkerIcons.icons:
			self._cmb_color.addItem(MarkerIcons.icons.get(color),"",color)
		# TODO: Oh boy test this
		self._cmb_color.setCurrentIndex(list(MarkerIcons.icons.keys()).index(EXPORT_DEFAULT_MARKER_COLOR))
		self._cmb_color.setToolTip("Exported Marker Color")
		self.layout().addWidget(self._cmb_color)

		for track in EXPORT_TRACK_OPTIONS:
			self._cmb_track.addItem(track)
		self._cmb_track.setToolTip("Track for Exported Markers")
		self.layout().addWidget(self._cmb_track)

		self._txt_name.setText(EXPORT_DEFAULT_MARKER_NAME)
		self._txt_name.setToolTip("Name of Exported Markers")
		self.layout().addWidget(self._txt_name)

		self._btn_export.setText("Export Marker List...") 
		self._btn_export.setEnabled(False)
		self.layout().addWidget(self._btn_export)

		self._btn_export.clicked.connect(self._export_markers)

	@QtCore.Slot()
	def allow_export(self, allowed:bool):
		"""Allow us to do our thang here"""
		self._btn_export.setEnabled(allowed)
	
	@QtCore.Slot()
	def _export_markers(self, markers:typing.Iterable[locatorator.Marker]) -> None:
		"""Export a given marker list"""

		path_output = QtWidgets.QFileDialog.getSaveFileName(self, "Choose a location to save your markers", filter="Marker Lists (*.txt);;All Files (*)")[0]
		
		if not path_output:
			self.sig_export_canceled.emit()
			return
		
		self.sig_export_requested.emit(path_output, locatorator.MarkerColors(self._cmb_color.currentData()), self._cmb_track.currentText(), self._txt_name.text())

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

	sig_changes_ready   = QtCore.Signal()
	sig_changes_cleared = QtCore.Signal()

	def __init__(self):
		super().__init__()
		self._prep_marker_icons()

		self._changes_loaded = False

		self._layout = QtWidgets.QVBoxLayout()
		self._grp_list_inputs = InputListGroup()
		self._tree_viewer = MarkerViewer()
		self._exporter = OutputFileGroup()

		self._locked = False
		self._path_old = pathlib.Path()
		self._path_new = pathlib.Path()

		self._markerlist = []

		self._setup()
	
	def _setup(self):
		self.setLayout(self._layout)
		self.layout().addWidget(self._grp_list_inputs)
		self.layout().addWidget(self._tree_viewer)
		self.layout().addWidget(self._exporter)

		self._grp_list_inputs.sig_paths_chosen.connect(self._set_paths)
		
		#self._tree_viewer.sig_changes_ready.connect(self.sig_changes_ready)
		self.sig_changes_ready.connect(self._validate_changes)
		self.sig_changes_cleared.connect(lambda:self._exporter.allow_export.emit(False))
		
		self._exporter.sig_export_requested.connect(self._save_marker_list)
	
	@QtCore.Slot()
	def _validate_changes(self):
		"""Marker lists have successfully loaded"""
		
		# Ensure at least one change has a non-zero delta or "Shot Added/Removed" message
		self._exporter.allow_export(
			any(m[2] for m in self._markerlist)
		)

		self._changes_loaded = True
	
	@QtCore.Slot()
	def _save_marker_list(self, path_output:str, marker_color:locatorator.MarkerColors=locatorator.MarkerColors.WHITE, marker_track:str="TC1", marker_name:str=EXPORT_DEFAULT_MARKER_NAME):
		"""Export a marker change list"""

		with open(path_output, "w") as file_output:
			for marker_old, marker_new, tc_delta in self._markerlist:
				if marker_old and marker_new and tc_delta:
					marker_output = locatorator.Marker(
						name=marker_name,
						color=marker_color,
						tc_start=str(marker_new.timecode.start),
						duration=1,
						track=marker_track,
						comment=f"Cut change near {marker_new.comment}: {tc_delta} ({marker_old.timecode.start} -> {marker_new.timecode.start})"
					)
				elif not marker_old:
					marker_output = locatorator.Marker(
						name=marker_name,
						color=marker_color,
						tc_start=str(marker_new.timecode.start),
						duration=1,
						track=marker_track,
						comment=f"Shot added: {marker_new.comment}"
					)
				else:
					marker_output = locatorator.Marker(
						name=marker_name,
						color=marker_color,
						tc_start=str(marker_old.timecode.start),
						duration=1,
						comment=f"Shot removed: {marker_old.comment}"
					)
				print(marker_output, file=file_output)
		
	
	def _set_paths(self, path_old:str, path_new:str):
		"""Update the program paths and run the comparison"""
		# TODO: Split this out?

		# Clear out the marker list model
		self._markerlist = []

		self._path_old = pathlib.Path(path_old)
		self._path_new = pathlib.Path(path_new)

		with self._path_old.open() as file_old:
			markers_old = locatorator.get_marker_list_from_file(file_old)

		with self._path_new.open() as file_new:
			markers_new = locatorator.get_marker_list_from_file(file_new)
		
		self._markerlist = locatorator.build_marker_changes(markers_old, markers_new)

		self._tree_viewer.set_changelist(self._markerlist)

		self.sig_changes_ready.emit()
	
	def _prep_marker_icons(self):
		"""Prepare marker icons based on Marker Colors"""
		for marker_color in (m.lower() for m in locatorator.MarkerColors._member_names_):
			MarkerIcons.prepare_icon(marker_color)
	
class MainWindow(QtWidgets.QMainWindow):
	"""Main Program Window"""

	def __init__(self):
		super().__init__()

		self.wdg_main = MainWidget()

		self._setup()
	
	def _setup(self) -> None:
		"""Setup the main window"""

		self.setCentralWidget(self.wdg_main)
		self.setWindowTitle("Locatorator")
		self.setMinimumWidth(450)

def main() -> int:
	"""Launch the QApplication"""
	app = QtWidgets.QApplication(sys.argv)

	wnd_main = MainWindow()
	wnd_main.show()

	return app.exec()

if __name__ == "__main__":

	sys.exit(main())