import sys, typing, enum, re, copy, pathlib
from posttools.timecode import Timecode, TimecodeRange

class MarkerColors(enum.Enum):
	"""Avid marker colors"""
	RED     = "red"
	GREEN   = "green"
	BLUE    = "blue"
	CYAN    = "cyan"
	MAGENTA = "magenta"
	YELLOW  = "yellow"
	BLACK   = "black"
	WHITE   = "white"

class Marker:
	"""An Avid Marker/Locator"""

	_pat_bad_chars = re.compile("[\n\t]")

	def __init__(self, *, name:str, tc_start:typing.Union[str,Timecode], track:str, color:typing.Union[str,MarkerColors], comment:str, duration:int):

		self._name    = self._sanitize_string(name)
		self._tc      = TimecodeRange(start=Timecode(tc_start), duration=Timecode(duration))
		self._track   = self._sanitize_string(track)
		self._color   = MarkerColors(color)
		self._comment = self._sanitize_string(comment)
	
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
		return self.timecode.duration.framenumber > 1
		
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
		return cls(
			name = m[0],
			tc_start = m[1],
			track = m[2],
			color = m[3],
			comment = m[4],
			duration = int(m[5])
		)
	
	def __str__(self) -> str:
		return "\t".join([
			self.name,
			str(self.timecode.start),
			self.track,
			self.color.value,
			self.comment,
			str(self.timecode.duration.framenumber)
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

		markers.append(marker)
	
	return markers

def build_marker_lookup(marker_list:typing.Iterable[Marker]) -> dict[str, Marker]:
	"""Build a dict based on marker comments"""

	marker_lookup = {}
	for marker in marker_list:
		# TODO: Think about shot IDs occurring more than once in a list
		if marker.comment in marker_lookup:
			raise ValueError(f"Shot ID \"{marker.comment}\" was found more than once")
		marker_lookup[marker.comment.lower()] = marker
	
	return marker_lookup

def build_marker_changes(markers_old:typing.Iterable[Marker], markers_new:typing.Iterable[Marker]) -> typing.List[typing.Tuple[Marker, str]]:
	"""Build matches of old and new markers"""

	# TODO: This still feels like it's doing too much

	marker_lookup = build_marker_lookup(markers_old)

	running_offset = Timecode(0)
	marker_pairs = []

	for marker_new in markers_new:

		marker_old = marker_lookup.get(marker_new.comment.lower())
		local_offset = marker_new.timecode.start - marker_old.timecode.start if marker_old else 0
		adjusted_offset = local_offset-running_offset
		
		if marker_old is None:
			change_details = f"New shot ID added: {marker_new.comment} at {marker_new.timecode.start}"

		elif adjusted_offset != 0:
			change_details = f"Cut change at {marker_old.comment}: {marker_old.timecode.start} -> {marker_new.timecode.start}   {'' if adjusted_offset < Timecode(0) else '+'}{adjusted_offset}"
			running_offset = local_offset


		else:
			continue

		marker_pairs.append(
			(marker_new, change_details,)
		)
	
	return marker_pairs

def write_change_list(markers_changes:typing.Iterable[typing.Tuple[Marker,str]], file_output:typing.TextIO, marker_name="Locatorator", marker_track:str="TC1", marker_color:MarkerColors=MarkerColors.WHITE):
	"""Write changes to a new marker list"""

	for marker, comment in markers_changes:
		print(
			Marker(
				name=marker_name,
				tc_start = str(marker.timecode.start),
				track=marker_track,
				color=marker_color,
				comment=comment,
				duration=1
			),
			file=file_output
		)
	
def print_change_list(markers_changes) -> None:
	"""Print changes to screen"""

	print("")
	print("Shot ID               Old Version    New Version   Offset since last change")
	print("--------------------- -----------    -----------   ------------------------")

	for _, comment in markers_changes:
		print(comment)
	
	print("")

def main() -> None:
	"""Markers"""

	if len(sys.argv) < 3:
		sys.exit(f"Usage: {__package__} markerlist.txt comparelist.txt")

	# Load in the marker lists
	with open(sys.argv[1]) as file_markers:
		markers_old = get_marker_list_from_file(file_markers)
	markers_old.sort(key=lambda x:x.timecode.start)
		
	with open(sys.argv[2]) as file_markers:
		markers_new = get_marker_list_from_file(file_markers)
	markers_new.sort(key=lambda x:x.timecode.start)
	
	# Pair markers together by comment (shot id)
	markers_changes = build_marker_changes(markers_old, markers_new)

	if not markers_changes:
		print("No changes were detected.")
		return

	# Write changes to new marker list
	with open("changes.txt", "w") as file_output:
		write_change_list(markers_changes, file_output)

	print_change_list(markers_changes)

	print("Marker list output to changes.txt")

def bootstrap():
	"""Entrypoint via setup.py `entry_point`"""

	try:
		main()
	except Exception as e:
		sys.exit(e)

if __name__ == "__main__":

	bootstrap()
