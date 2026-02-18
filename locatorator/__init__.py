import typing, enum, re, copy, dataclasses
from timecode import Timecode, TimecodeRange

class MarkerColors(enum.Enum):
	"""Avid marker colors"""
	
	# Traditional colors
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

CLASSIC_MARKER_SET = {
	MarkerColors.RED,
	MarkerColors.GREEN,
	MarkerColors.BLUE,
	MarkerColors.CYAN,
	MarkerColors.MAGENTA,
	MarkerColors.YELLOW,
	MarkerColors.BLACK,
	MarkerColors.WHITE,
}

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

		if len(m) == 6:

			return cls(
				name = m[0],
				tc_start = m[1],
				track = m[2],
				color = str(m[3]).lower(),
				comment = m[4],
				duration = int(m[5]),
				user = ""
			)
		
		elif len(m) == 8:

			return cls(
				name = m[0],
				tc_start = m[1],
				track = m[2],
				color = str(m[7]).lower(),
				comment = m[4],
				duration = int(m[5]),
				user = m[6]
			)
		
		else:
			raise ValueError("Unknown marker list format")
	
	def __str__(self) -> str:

		# FOR NOW: Always using "new" format
		
		return "\t".join([
			self.name,
			str(self.timecode.start),
			self.track,
			self.color.value.title() if self.color in CLASSIC_MARKER_SET else "Yellow",
			self.comment,
			str(self.timecode.duration.framenumber),
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
		return cls._pat_bad_chars.sub("",text).strip()

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

PAT_VFX_MARKER = re.compile(r"^[a-z]{3}[0-9]{4}", re.IGNORECASE)
"""ABC1234"""

def is_vfx_marker(marker:Marker) -> bool:
	"""Filter VFX markers.  For a moment it's hard-coded to format: `ABC1234`"""
	
	return bool(PAT_VFX_MARKER.match(marker.comment))
	
def get_marker_list_from_file(file_input:typing.TextIO) -> typing.List[Marker]:
	"""Parse a marker list from a file pointer"""

	markers = []

	for idx, line in enumerate(l.rstrip('\n') for l in file_input.readlines()):
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
				change_type = ChangeTypes.CHANGED if relative_offset.framenumber else ChangeTypes.UNCHANGED,
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

def write_change_list(markers_changes:typing.Iterable[MarkerChangeReport], file_output:typing.TextIO, marker_name="Locatorator", marker_track:str="TC1", marker_color:MarkerColors=MarkerColors.WHITE):
	"""Write changes to a new marker list"""

	for marker_change in markers_changes:
		if marker_change.change_type in (ChangeTypes.UNCHANGED, ChangeTypes.DELETED):
			continue

		elif marker_change.change_type == ChangeTypes.ADDED:
			marker_output = Marker(
				name=marker_name,
				color=marker_color,
				tc_start=str(marker_change.marker_new.timecode.start),
				duration=1,
				track=marker_track,
				comment=f"Shot added: {marker_change.marker_new.comment}"
			)

		else:
			marker_output = Marker(
				name=marker_name,
				color=marker_color,
				tc_start=str(marker_change.marker_new.timecode.start),
				duration=1,
				track=marker_track,
				comment=f"Cut change near {marker_change.marker_old.comment} ({'+' if marker_change.relative_offset.framenumber > 0 else ''}{marker_change.relative_offset})"
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