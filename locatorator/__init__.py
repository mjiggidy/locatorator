import typing, enum, re, copy, dataclasses
from timecode import Timecode, TimecodeRange

class MarkerListFormats(enum.Enum):
	"""Marker list formats supported"""

	MARKER_LIST_V1 = enum.auto()
	MARKER_LIST_V2 = enum.auto()

MarkerListParsers:dict[MarkerListFormats, re.Pattern] = {
	MarkerListFormats.MARKER_LIST_V1: re.compile(r"^(?P<name>.+?)\t(?P<tc_start>[0-9:;]+?)\t(?P<track>.+?)\t(?P<color>[a-z]+?)\t(?P<comment>.*)\t(?P<duration>[0-9]+?)$", re.IGNORECASE),
	MarkerListFormats.MARKER_LIST_V2: re.compile(r"^(?P<name>.+?)\t(?P<tc_start>[0-9:;]+?)\t(?P<track>.+?)\t(?P<legacy_color>[a-z]+?)\t(?P<comment>.*)\t(?P<duration>[0-9]+?)\t(?P<user>.*?)\t(?P<color>[a-z]+?)$", re.IGNORECASE)
}
"""Regex parsers per supported marker list format"""

PAT_VFX_MARKER = re.compile(r"^[a-z]{2,4}[0-9]{3,4}", re.IGNORECASE)
"""Pattern for matching a VFX ID marker comment"""

class MarkerColors(enum.Enum):
	"""Avid marker colors"""
	
	# Legacy colors (Avid 3.0+)
	RED     = "red"
	GREEN   = "green"
	BLUE    = "blue"
	CYAN    = "cyan"
	MAGENTA = "magenta"
	YELLOW  = "yellow"
	BLACK   = "black"
	WHITE   = "white"

	# Extended colors (2024.6+)
	PINK    = "pink"
	FOREST  = "forest"
	DENIM   = "denim"
	VIOLET  = "violet"
	PURPLE  = "purple"
	ORANGE  = "orange"
	GREY    = "grey"
	GOLD    = "gold"

LEGACY_MARKER_SET = {
	MarkerColors.RED,
	MarkerColors.GREEN,
	MarkerColors.BLUE,
	MarkerColors.CYAN,
	MarkerColors.MAGENTA,
	MarkerColors.YELLOW,
	MarkerColors.BLACK,
	MarkerColors.WHITE,
}
"""Legacy marker colors Avid 3.0+"""

EXTENDED_MARKER_SET = {
	MarkerColors.PINK,
	MarkerColors.FOREST,
	MarkerColors.DENIM,
	MarkerColors.VIOLET,
	MarkerColors.PURPLE,
	MarkerColors.ORANGE,
	MarkerColors.GREY,
	MarkerColors.GOLD,
}
"""Extended marker colors available in Avid 2024.6"""

class ChangeTypes(enum.IntEnum):
	"""Types of changes between marker lists"""

	UNCHANGED = enum.auto()
	"""Marker position has not changed"""

	CHANGED   = enum.auto()
	"""Marker position has changed"""

	ADDED     = enum.auto()
	"""Marker has been added in the new version"""

	DELETED   = enum.auto()
	"""Marker has been deleted from the new version"""


class Marker:
	"""An Avid Marker/Locator"""

	_pat_bad_chars = re.compile("[\n\t]")

	def __init__(self, *, name:str, tc_start:typing.Union[str,Timecode], track:str, color:typing.Union[str,MarkerColors], comment:str, duration:int, user:str=""):

		self._name    = self._sanitize_string(name)
		self._tc      = TimecodeRange(start=Timecode(tc_start), duration=Timecode(duration))
		self._track   = self._sanitize_string(track)
		self._color   = MarkerColors(color)
		self._comment = self._sanitize_string(comment)
		self._user    = self._sanitize_string(user)
	
	@property
	def name(self) -> str:
		"""The name of the marker"""
		return self._name
	
	@property
	def timecode(self) -> TimecodeRange:
		"""The timecode range of the marker"""
		return copy.copy(self._tc)
	
	@property
	def track(self) -> str:
		"""The track on which this marker is set"""
		return self._track
	
	@property
	def color(self) -> MarkerColors:
		"""The marker color"""
		return self._color
	
	@property
	def comment(self) -> str:
		"""The marker comment"""
		return self._comment
	
	@property
	def is_spanned(self) -> bool:
		"""Is this a spanned marker"""
		return self.timecode.duration.frame_number > 1
		
	@classmethod
	def from_string(cls, line:str) -> "Marker":
		"""Create a marker from a line in a marker list"""
		m = line.split('\t')
		"""
		Fields:
		name
		Start TC
		Track
		Color
		Comment
		Duration (frames)
		"""

		for parser in MarkerListParsers.values():

			if match := parser.match(line):

				return cls(
					name = match.group("name"),
					tc_start = match.group("tc_start"),
					track = match.group("track"),
					color = match.group("color").lower(),
					comment = match.group("comment"),
					duration = match.group("duration"),
					user = match.group("user") if "user" in match.groupdict() else "",
				)
		
		else:
			raise ValueError("Unknown marker list format")
	
	def __str__(self) -> str:

		# NOTE FOR NOW: Always using "new" format
		
		return "\t".join([
			self.name,
			str(self.timecode.start),
			self.track,
			self.color.value.title() if self.color in LEGACY_MARKER_SET else "Yellow",
			self.comment,
			str(self.timecode.duration.frame_number),
			self._user,
			self.color.value.title()
		])

	def __repr__(self) -> str:
		return f"<{self.__class__.__name__} name={self.name} timecode={self.timecode.start} comment={self.comment}"
	
	def __eq__(self, other) -> bool:
		
		if isinstance(other, self.__class__):
			return self.timecode.start == other.timecode.start
		else:
			return self.timecode.start == other
	
	def __lt__(self, other) -> bool:

		if isinstance(other, self.__class__):
			return self.timecode.start < other.timecode.start
		else:
			return self.timecode.start < other

	def __hash__(self) -> str:
		return hash(self.name, self.track, self.timecode, self.comment)
		
	
	@classmethod
	def _sanitize_string(cls, text:str) -> str:
		"""Don't try anything silly"""


		return str().join(s if str(s).isprintable() else " " for s in  text)

@dataclasses.dataclass
class MarkerChangeReport:
	"""A comparison between two markers for the same shot"""

	change_type:ChangeTypes
	"""The type of change between markers"""
	marker_old:typing.Optional[Marker] = None
	"""The marker from the old list"""
	marker_new:typing.Optional[Marker] = None
	"""The marker from the new list"""
	relative_offset:typing.Optional[Timecode] = None
	"""Adjusted/relative change between the two lists"""

def is_vfx_marker(marker:Marker) -> bool:
	"""Filter VFX markers.  For a moment it's hard-coded to format: `ABC1234`"""
	
	return bool(PAT_VFX_MARKER.match(marker.comment))
	
def get_marker_list_from_file(file_input:typing.TextIO) -> typing.List[Marker]:
	"""Parse a marker list from a file pointer"""

	markers = []

	for idx, line in enumerate(map(lambda l: l.rstrip('\n'), file_input)):
		try:
			marker = Marker.from_string(line)
		except Exception as e:
			raise ValueError(f"Cannot parse marker on line {idx+1}: {e}")

		# TODO: Add filtering? Ex: Filter only blue markers
		# if marker.color != MarkerColors.BLUE:
		#	continue

		# NOTE FOR NOW: Hard coding to ABC1234
		if is_vfx_marker(marker):
			markers.append(marker)
	
	return markers

def build_marker_lookup(marker_list:typing.Iterable[Marker]) -> dict[str, Marker]:
	"""Build a dict based on marker comments"""

	marker_lookup = {}
	for marker in marker_list:
		# TODO: Think about shot IDs occurring more than once in a list
		if marker.comment in marker_lookup:
			raise ValueError(f"Shot ID \"{marker.comment}\" was found more than once in the same list.")
		marker_lookup[marker.comment.lower()] = marker
	
	return marker_lookup

def build_marker_changes(markers_old:typing.Iterable[Marker], markers_new:typing.Iterable[Marker]) -> typing.List[MarkerChangeReport]:
	"""Build matches of old and new markers"""

	# TODO: This still feels like it's doing too much

	marker_lookup_old = build_marker_lookup(markers_old)

	running_offset = Timecode(0) # The total number of frames offset from the beginning
	marker_pairs = []

	for marker_new in markers_new:

		# TODO: Rework as `if marker_new.comment.lower() not in marker_lookup_old:`?
		marker_old = marker_lookup_old.get(marker_new.comment.lower())
		absolute_offset = marker_new.timecode.start - marker_old.timecode.start if marker_old else 0
		relative_offset = absolute_offset-running_offset

		if not marker_old:
			change_report = MarkerChangeReport(
				change_type = ChangeTypes.ADDED,
				marker_new = marker_new
			)
		else:
			change_report = MarkerChangeReport(
				change_type = ChangeTypes.CHANGED if relative_offset.frame_number else ChangeTypes.UNCHANGED,
				marker_old = marker_old,
				marker_new = marker_new,
				relative_offset = relative_offset
			)
			del marker_lookup_old[marker_new.comment.lower()]

		if relative_offset != 0:
			running_offset = absolute_offset

		marker_pairs.append(change_report)
	
	# Add any remaining shots in marker_lookup_old that went unmatched to the markers_new list
	for _, marker_old in marker_lookup_old.items():
		marker_pairs.append(MarkerChangeReport(
				change_type = ChangeTypes.DELETED,
				marker_old = marker_old
		))
	
	return marker_pairs

def write_change_list(markers_changes:typing.Iterable[MarkerChangeReport], file_output:typing.TextIO, marker_name="Locatorator", marker_track:str="TC1", marker_color:MarkerColors=MarkerColors.WHITE, change_types:typing.Iterable[ChangeTypes]|None=None):
	"""Write changes to a new marker list"""

	change_types = set(change_types) or {ChangeTypes.ADDED, ChangeTypes.CHANGED, ChangeTypes.DELETED}

	for marker_change in markers_changes:

		if marker_change.change_type not in change_types:
			continue

		if marker_change.change_type == ChangeTypes.ADDED:
			comment=f"Shot added: {marker_change.marker_new.comment}"
		
		elif marker_change.change_type == ChangeTypes.CHANGED:
			comment=f"Cut change near {marker_change.marker_old.comment} ({'+' if marker_change.relative_offset.frame_number > 0 else ''}{marker_change.relative_offset})"
		
		elif marker_change.change_type == ChangeTypes.DELETED:
			comment=f"Shot removed since last cut: {marker_change.marker_old.comment}"
		
		elif marker_change.change_type == ChangeTypes.UNCHANGED:
			comment=f"Shot unchanged since last cut: {marker_change.marker_old.comment}"
		
		else:
			raise ValueError(f"Unknown Change Type: {marker_change.change_type}")

		marker_output = Marker(
			name=marker_name,
			color=marker_color,
			tc_start=str(marker_change.marker_new.timecode.start if marker_change.marker_new else marker_change.marker_old.timecode.start),
			duration=1,
			track=marker_track,
			comment=comment
		)

		print(marker_output, file=file_output)
	
def print_change_list(markers_changes) -> None:
	"""Print changes to screen"""

	print("")
	print("Shot ID               Old Version    New Version   Offset since last change")
	print("--------------------- -----------    -----------   ------------------------")

	for _, comment in markers_changes:
		print(comment)
	
	print("")