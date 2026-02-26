from PySide6 import QtWidgets, QtCore, QtGui
import sys, pathlib, typing
import locatorator
from locatorator import PAT_VFX_MARKER

MARKER_COMMENT_COLUMN_NAME = "Shot ID"
EXPORT_TRACK_OPTIONS = ("TC1","V1","V2","V3","V4","V5","V6","V7","V8")
EXPORT_DEFAULT_MARKER_NAME = "Locatorator"
EXPORT_DEFAULT_MARKER_COLOR = "white"
DEFAULT_MARKER_COLOR = "red"

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
			"TC Offset",
			"Frame Offset"
		]

		self._setup()
	
	def _setup(self):

		self.setIndentation(0)
		self.setHeaderLabels(self._headerlabels)
		self.setColumnHidden(self._headerlabels.index("Frame Offset"), True)
		self.setAlternatingRowColors(True)
		self.setUniformRowHeights(True)
		self.setSortingEnabled(True)

	def set_changelist(self, markers_changes:typing.Iterable[locatorator.MarkerChangeReport]) -> None:

		self.clear()

		changelist = []

		font_monospace = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont).family()

		for marker_change in markers_changes:
			
			if marker_change.change_type == locatorator.ChangeTypes.DELETED:
				marker_comment = marker_change.marker_old.comment
				marker_color = MarkerIcons.icons.get(marker_change.marker_old.color.name.lower(), DEFAULT_MARKER_COLOR)
				tc_old = str(marker_change.marker_old.timecode.start)
				tc_new = ""
				change = "Shot Removed"
			
			elif marker_change.change_type == locatorator.ChangeTypes.ADDED:
				marker_comment = marker_change.marker_new.comment
				marker_color = MarkerIcons.icons.get(marker_change.marker_new.color.name.lower(), DEFAULT_MARKER_COLOR)
				tc_old = ""
				tc_new = str(marker_change.marker_new.timecode.start)
				change = "Shot Added"

			else:
				marker_comment = marker_change.marker_old.comment
				marker_color = MarkerIcons.icons.get(marker_change.marker_new.color.name.lower(), DEFAULT_MARKER_COLOR)
				tc_old = str(marker_change.marker_old.timecode.start)
				tc_new = str(marker_change.marker_new.timecode.start)
				change = str(marker_change.relative_offset)
				# Add signed positive TC
				if marker_change.relative_offset > 0:
					change = "+" + change
			
			
			changelist_item = QtWidgets.QTreeWidgetItem([
				PAT_VFX_MARKER.match(marker_comment).group(),
				#marker_comment,
				tc_old,
				tc_new,
				change,
				str(marker_change.change_type.value)
			], marker_change.change_type.value)

			changelist_item.setFont(1, font_monospace)
			changelist_item.setFont(2, font_monospace)

			# Align Timecodes right|cener
			for idx, header in enumerate(self._headerlabels):
				if header != MARKER_COMMENT_COLUMN_NAME:
					changelist_item.setTextAlignment(idx, QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignCenter)
			
			# Set marker icon according to the color in the marker list
			changelist_item.setIcon(0, marker_color)
			if marker_change.change_type == locatorator.ChangeTypes.UNCHANGED:
				for col in range(len(self._headerlabels)):
					changelist_item.setForeground(col, QtGui.QColor(QtCore.Qt.GlobalColor.gray)
				)

			changelist.append(changelist_item)

		self.addTopLevelItems(changelist)
		
		for idx, header in enumerate(self._headerlabels):
			if header != MARKER_COMMENT_COLUMN_NAME:
				self.resizeColumnToContents(idx)

		self.sortByColumn(self._headerlabels.index("New TC"), QtCore.Qt.SortOrder.AscendingOrder)

		self.sig_changes_ready.emit()

	def hide_non_changes(self, hidden:bool):
		"""Filter"""

		col_framechange = self._headerlabels.index("Frame Offset")
		max_items = self.topLevelItemCount()

		for item in (self.topLevelItem(x) for x in range(max_items)):
			if item.text(col_framechange) == str(locatorator.ChangeTypes.UNCHANGED.value):
				item.setHidden(hidden)
	
	def setFilters(self, filters:typing.Iterable[locatorator.ChangeTypes]):

		#col_framechange = self._headerlabels.index("Frame Offset")

		filter_values = [f.value for f in filters]

		for item in (self.topLevelItem(x) for x in range(self.topLevelItemCount())):	
			item.setHidden( item.type() not in filter_values)



class OutputFileGroup(QtWidgets.QGroupBox):
	"""Marker list export groupbox"""

	sig_export_requested = QtCore.Signal(locatorator.MarkerColors, str, str, set)
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

		self._change_filters = ExportFiltersWidget()

		self._settings = QtCore.QSettings()
	
		self._setup()

	def _setup(self): 

		self.setLayout(self._layout)
		self.layout().setContentsMargins(0,0,0,0)
		
		for color in MarkerIcons.icons:
			self._cmb_color.addItem(MarkerIcons.icons.get(color),"",color)
		# TODO: Oh boy test this
		self._cmb_color.setCurrentIndex(list(MarkerIcons.icons.keys()).index(str(self._settings.value("export/markercolor", EXPORT_DEFAULT_MARKER_COLOR))))
		self._cmb_color.setToolTip("Exported Marker Color")
		self.layout().addWidget(self._cmb_color)

		self._cmb_track.addItems(track for track in EXPORT_TRACK_OPTIONS)
		self._cmb_track.setCurrentIndex(EXPORT_TRACK_OPTIONS.index(str(self._settings.value("export/markertrack",EXPORT_TRACK_OPTIONS[0]))))
		self._cmb_track.setToolTip("Track for Exported Markers")
		self.layout().addWidget(self._cmb_track)

		self._txt_name.setText(str(self._settings.value("export/markername", EXPORT_DEFAULT_MARKER_NAME)))
		self._txt_name.setPlaceholderText(str(EXPORT_DEFAULT_MARKER_NAME))
		self._txt_name.setToolTip("Name of Exported Markers")
		self.layout().addWidget(self._txt_name)

		self._btn_export.setText("Export Marker List...") 
		self._btn_export.setEnabled(False)
		self.layout().addWidget(self._btn_export)

		self._cmb_color.currentIndexChanged.connect(lambda: self._settings.setValue("export/markercolor", self._cmb_color.currentData()))
		self._cmb_track.currentTextChanged.connect(lambda trk: self._settings.setValue("export/markertrack", trk))
		self._txt_name.editingFinished.connect(lambda: self._settings.setValue("export/markername", self._txt_name.text().strip() or EXPORT_DEFAULT_MARKER_NAME))
		self._btn_export.clicked.connect(self._export_markers)


	@QtCore.Slot()
	def allow_export(self, allowed:bool):
		"""Allow us to do our thang here"""
		self._btn_export.setEnabled(allowed)
	
	@QtCore.Slot()
	def _export_markers(self) -> None:
		"""Export a given marker list"""
		self.sig_export_requested.emit(locatorator.MarkerColors(self._cmb_color.currentData()), self._cmb_track.currentText(), self._txt_name.text(), self._change_filters.enabledFilters())

class InputFileChooser(QtWidgets.QWidget):
	"""Choose an input file"""

	sig_path_changed = QtCore.Signal(str)

	def __init__(self, label:str=""):
		super().__init__()

		self._layout = QtWidgets.QGridLayout()
		self._lbl_label = QtWidgets.QLabel(label)
		self._txt_filepath = QtWidgets.QLineEdit()
		self._btn_browse = QtWidgets.QPushButton(text="...")

		self._start_folder_path = ""

		self._setup()

	def _setup(self):

		self.setLayout(self._layout)
		self.layout().setContentsMargins(0,0,0,0)
		self.layout().setVerticalSpacing(0)
		self.setAcceptDrops(True)

		self._txt_filepath.setPlaceholderText("Drag-and-drop or browse for a marker list")

		self.layout().addWidget(self._lbl_label, 0, 0)
		self.layout().addWidget(self._txt_filepath, 1, 0)
		self.layout().addWidget(self._btn_browse, 1, 1)


		self._txt_filepath.textChanged.connect(lambda:self.sig_path_changed.emit(self.get_specified_path()))
		self._btn_browse.clicked.connect(self._set_specified_path_from_browser)

	def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
		"""Respond to dragged files"""

		if event.mimeData().hasFormat("text/uri-list") and event.mimeData().urls()[0].isLocalFile():
			self._txt_filepath.setFocus()
			event.acceptProposedAction()

	def dropEvent(self, event:QtGui.QDropEvent) -> None:
		"""Allow dropped files"""
		event.acceptProposedAction()
		try:
			dropped_uri = event.mimeData().urls()[0]
			if not dropped_uri.isLocalFile():
				return
			dropped_path = dropped_uri.toLocalFile()
			self.set_specified_path(dropped_path)
		except:
			pass
	
	def set_start_folder_path(self, path_default:str):
		"""Set the initial path for the file browser dialog"""
		self._start_folder_path = path_default
	
	def _set_specified_path_from_browser(self) -> None:
		"""Open a file browser and set the path from a chosen file"""
		self._txt_filepath.setFocus()
		new_path = QtWidgets.QFileDialog.getOpenFileName(self, "Choose a marker list...", self.get_specified_path() or self._start_folder_path, "Marker Lists (*.txt);;All Files (*)")[0]
		self.set_specified_path(new_path or self._txt_filepath.text())
	
	def set_specified_path(self, user_path:str) -> None:
		"""Set the path as chosen by the user"""
		try:

			path = str(pathlib.Path(user_path))
			self.set_start_folder_path(path)
		except:
			path = user_path

		self._txt_filepath.setText(path)
	
	def get_specified_path(self) -> str:
		"""Get the path chosen by the user"""
		return self._txt_filepath.text().strip()

class InputListGroup(QtWidgets.QGroupBox):
	"""Get old and neew marker lists"""

	sig_paths_chosen = QtCore.Signal(str, str)

	def __init__(self):
		super().__init__()

		self._layout = QtWidgets.QVBoxLayout()
		self._input_old_markers = InputFileChooser(label="Old Markers:")
		self._input_new_markers = InputFileChooser(label="New Markers:")
		self._btn_compare = QtWidgets.QPushButton()

		self._settings = QtCore.QSettings()

		self._setup()

	def _setup(self):

		self.setLayout(self._layout)

		self._input_old_markers.set_start_folder_path(self._settings.value("import/oldpath",""))
		self._input_new_markers.set_start_folder_path(self._settings.value("import/newpath", ""))

		self.layout().addWidget(self._input_old_markers)
		self.layout().addWidget(self._input_new_markers)

		self._btn_compare.setText("Compare Marker Lists")
		self._btn_compare.setDefault(True)
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

		self._settings.setValue("import/oldpath",path_old)
		self._settings.setValue("import/newpath",path_new)

class MainWidget(QtWidgets.QWidget):

	sig_changes_ready   = QtCore.Signal()
	sig_changes_failed  = QtCore.Signal()
	sig_changes_cleared = QtCore.Signal()

	def __init__(self):
		super().__init__()
		self._prep_marker_icons()

		self._changes_loaded = False

		self._layout = QtWidgets.QVBoxLayout()
		self._grp_list_inputs = InputListGroup()
		self._tree_viewer = MarkerViewer()
		self._exporter = OutputFileGroup()

		self._chk_show_hidden = QtWidgets.QCheckBox()

		self._filters = ExportFiltersWidget()

		self._locked = False
		self._path_old = pathlib.Path()
		self._path_new = pathlib.Path()

		self._markerlist = []

		self._settings = QtCore.QSettings()

		self._setup()
	
	def _setup(self):
		self.setLayout(self._layout)
		self.layout().addWidget(self._grp_list_inputs)
		
#		self._chk_show_hidden.setText("Show Non-Changes")
#		self._chk_show_hidden.setCheckState(self._settings.value("viewer/showhidden",QtCore.Qt.CheckState.Unchecked))
#		self.layout().addWidget(self._chk_show_hidden)
		self.layout().addWidget(self._filters)
		self.layout().addWidget(self._tree_viewer)
		self.layout().addWidget(self._exporter)

		self._grp_list_inputs.sig_paths_chosen.connect(self._set_paths)
		
		#self._tree_viewer.sig_changes_ready.connect(self.sig_changes_ready)
		self.sig_changes_ready.connect(self._validate_changes)
		self.sig_changes_cleared.connect(lambda:self._exporter.allow_export.emit(False))

		self._filters.sig_filters_changed.connect(self._tree_viewer.setFilters)
		
#		self._chk_show_hidden.stateChanged.connect(lambda show_hidden: self._tree_viewer.hide_non_changes(not show_hidden))
#		self._chk_show_hidden.stateChanged.connect(lambda show_hidden: self._settings.setValue("viewer/showhidden", QtCore.Qt.CheckState(show_hidden)))
		self._exporter.sig_export_requested.connect(self._save_marker_list)
	
	@QtCore.Slot()
	def _validate_changes(self):
		"""Marker lists have successfully loaded"""
		
		# Export list will only contain changes or additions (no unchanged or deletions)
		self._exporter.allow_export(
			any(m.change_type in (locatorator.ChangeTypes.CHANGED, locatorator.ChangeTypes.ADDED) for m in self._markerlist)
		)

		self._tree_viewer.setFilters(self._filters.enabledFilters())

		self._changes_loaded = True
	
	@QtCore.Slot()
	def _save_marker_list(self, marker_color:locatorator.MarkerColors=locatorator.MarkerColors.WHITE, marker_track:str="TC1", marker_name:str=EXPORT_DEFAULT_MARKER_NAME):
		"""Export a marker change list"""

		path_output = QtWidgets.QFileDialog.getSaveFileName(self, "Choose a location to save your markers", dir=self._suggest_output_path(), filter="Marker Lists (*.txt);;All Files (*)")[0]
		
		if not path_output:
			return

		try:
			with open(path_output, "w") as file_output:
				locatorator.write_change_list(
					markers_changes=self._markerlist,
					file_output=file_output,
					marker_name=marker_name,
					marker_track=marker_track,
					marker_color=marker_color,
					change_types=self._filters.enabledFilters()
				)

		except Exception as e:
			QtWidgets.QMessageBox.critical(self, "Error Saving Change List",f"<strong>Cannot save the new marker list:</strong><br/>{e}")
			return
		
		self._settings.setValue("export/lastoutputpath",path_output)
	
	def _suggest_output_path(self) -> str:
		"""Suggest an output path"""
		try:
			return str(
				pathlib.Path(
					self._settings.value("export/lastoutputpath","./changes.txt")
				).with_name(self._path_old.stem.strip() + " vs " + self._path_new.stem + ".txt")
			)
		except Exception as e:
			print(e)
			return "changes.txt"

	def _set_paths(self, path_old:str, path_new:str):
		"""Update the program paths and run the comparison"""
		# TODO: Split this out?

		# Clear out the marker list model
		self._markerlist = []
		self._tree_viewer.clear()


		try:
			self._path_old = pathlib.Path(path_old)
			with self._path_old.open() as file_old:
				markers_old = locatorator.get_marker_list_from_file(file_old)
		except Exception as e:
			self.sig_changes_failed.emit()
			QtWidgets.QMessageBox.critical(self, "Error Loading Marker List",f"<strong>Cannot load the &quot;Old&quot; marker list:</strong><br/>{e}")
			self.sig_changes_failed.emit()
			return

		try:
			self._path_new = pathlib.Path(path_new)
			with self._path_new.open() as file_new:
				markers_new = locatorator.get_marker_list_from_file(file_new)
		except Exception as e:
			self.sig_changes_failed.emit()
			QtWidgets.QMessageBox.critical(self, "Error Loading Marker List",f"<strong>Cannot load the &quot;New&quot; marker list:</strong><br/>{e}")
			self.sig_changes_failed.emit()
			return
				
		try:
			self._markerlist = locatorator.build_marker_changes(markers_old, markers_new)
			self._tree_viewer.set_changelist(self._markerlist)
		except Exception as e:
			self.sig_changes_failed.emit()
			QtWidgets.QMessageBox.critical(self, "Error Comparing Changes",f"<strong>Cannot compare marker lists:</strong><br/>{e}")
			self.sig_changes_failed.emit()
			return

		self.sig_changes_ready.emit()
	
	def _prep_marker_icons(self):
		"""Prepare marker icons based on Marker Colors"""
		for marker_color in (m.lower() for m in locatorator.MarkerColors._member_names_):
			MarkerIcons.prepare_icon(marker_color)

class AboutWindow(QtWidgets.QDialog):
	"""About window"""

	def __init__(self):

		super().__init__()

		self._layout = QtWidgets.QGridLayout()
		self._lbl_icon = QtWidgets.QLabel()

		self._lbl_program = QtWidgets.QLabel("<strong>Locatorator</strong>")
		self._lbl_author = QtWidgets.QLabel("By Michael Jordan &lt;<a href=\"mailto:michael@glowingpixel.com\">michael@glowingpixel.com</a>&gt;")
		self._lbl_description = QtWidgets.QLabel("Compare two Avid marker lists to discover the fun and interesting changes between them.")
		self._lbl_version = QtWidgets.QLabel(f"Version {QtWidgets.QApplication.instance().applicationVersion()}")

		self._lbl_all = QtWidgets.QLabel(f"""<p>
		<strong>Locatorator</strong><br/>
		By Michael Jordan &lt;<a href=\"mailto:michael@glowingpixel.com\">michael@glowingpixel.com</a>&gt;</p>
		<p>Compare two Avid marker lists to discover the fun and interesting changes between them.</p>
		<p>Github: <a href=\"https://github.com/mjiggidy/locatorator/\">https://github.com/mjiggidy/locatorator/</a><br/>
		Homepage: <a href=\"https://glowingpixel.com/\">https://glowingpixel.com/</a><br/>
		Donations: <a href=\"https://ko-fi.com/lilbinboy\">https://ko-fi.com/lilbinboy</a></p>
		<p>Version {QtWidgets.QApplication.instance().applicationVersion()}</p>""")

		self._icon = QtGui.QPixmap(":/icons/resources/icon.png")
		self._btn_close = QtWidgets.QPushButton("Ok")

		self._setup()

	def _setup(self) -> None:

		self.setWindowTitle("About Locatorator")
		self.setFixedWidth(450)
		self.setLayout(self._layout)
		self.layout().setHorizontalSpacing(24)

		self._lbl_icon.setPixmap(self._icon)
		self._lbl_icon.setFixedSize(48,48)
		self._lbl_icon.setScaledContents(True)

		self._lbl_all.setWordWrap(True)
		self._lbl_all.setOpenExternalLinks(True)

		self.layout().addWidget(self._lbl_icon, 0, 0, QtGui.Qt.AlignmentFlag.AlignTop)
		self.layout().addWidget(self._lbl_all, 0, 1, QtGui.Qt.AlignmentFlag.AlignTop)
		self.layout().addWidget(self._btn_close, 1,1)
		#self.layout().addWidget(self._lbl_description, 1, 1)
		#self.layout().addWidget(self._lbl_description, 2, 1)

		self._btn_close.clicked.connect(self.close)

class ExportFiltersWidget(QtWidgets.QWidget):

	sig_filters_changed = QtCore.Signal(set)

	def __init__(self):

		super().__init__()

		self.setLayout(QtWidgets.QHBoxLayout())
		self.layout().setContentsMargins(0,0,0,0)
		self.layout().setSpacing(0)

		settings = QtCore.QSettings()

		self._change_types = {change_type: QtWidgets.QCheckBox() for change_type in locatorator.ChangeTypes}

		for change_type, change_check in self._change_types.items():

			change_check.setText(change_type.name.title())
			change_check.setChecked(settings.value("filters/" + change_type.name, True, bool))
			change_check.stateChanged.connect(self.filtersChanged)
			self.layout().addWidget(change_check)
	
	def enabledFilters(self) -> set[locatorator.ChangeTypes]:

		return {c for c in self._change_types if self._change_types[c].isChecked()}
	
	@QtCore.Slot()
	def filtersChanged(self):
		
		for change_type in locatorator.ChangeTypes:
			QtCore.QSettings().setValue("filters/" + change_type.name, change_type in self.enabledFilters())
		
		self.sig_filters_changed.emit(self.enabledFilters())

class MainWindow(QtWidgets.QMainWindow):
	"""Main Program Window"""

	def __init__(self):
		super().__init__()

		self.wdg_main = MainWidget()

		self.wnd_about = AboutWindow()

		self._setup()
	
	def _setup(self) -> None:
		"""Setup the main window"""

		self.setCentralWidget(self.wdg_main)
		self.setWindowTitle("Locatorator")
		self.setMinimumWidth(500)

		menu_help = QtWidgets.QMenu("&Help")
		menu_help.addAction("About", self.wnd_about.exec)

		self.menuBar().addMenu(menu_help)

def main() -> int:
	"""Launch the QApplication"""
	
	app = QtWidgets.QApplication(sys.argv)
	app.setOrganizationName("GlowingPixel")
	app.setApplicationName("Locatorator")
	app.setApplicationVersion("1.4.0")
	

	app.setWindowIcon(QtGui.QPixmap(":/icons/resources/icon.png"))

	wnd_main = MainWindow()
	wnd_main.show()

	return app.exec()

if __name__ == "__main__":

	sys.exit(main())