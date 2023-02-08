import sys, typing, enum, re, copy, pathlib
from posttools.timecode import Timecode, TimecodeRange

"""
Fields:

name
Start TC
Track
Color
Comment
Duration (frames)
"""

class MarkerList:
	"""A list of markers (do I need this really?)"""
	pass

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
		return self._track
	
	@property
	def color(self) -> MarkerColors:
		return self._color
	
	@property
	def comment(self) -> str:
		return self._comment
		
	@classmethod
	def from_string(cls, line:str) -> "Marker":
		"""Create a marker from a line in a marker list"""
		m = line.split('\t')
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

def main() -> None:
	"""Markers"""

	if len(sys.argv) < 3:
		sys.exit(f"Usage: {__file__} markerlist.txt comparelist.txt")
	
	markers_orig = []
	
	path_orig = pathlib.Path(sys.argv[1])

	# Get the first 'un as a list
	with open(sys.argv[1]) as file_markers:
		for idx, line in enumerate(l.rstrip('\n') for l in file_markers.readlines()):
			marker = Marker.from_string(line)
			# Filter only blue markers
			if marker.color != MarkerColors.BLUE:
				continue
			markers_orig.append(marker)
	
	# Sort markers by TC
	markers_orig.sort()
		
	# Get the second 'un as a dict
	markers_comp = {}
	with open(sys.argv[2]) as file_compare:

		for idx, line in enumerate(l.rstrip('\n') for l in file_compare.readlines()):
			marker = Marker.from_string(line)
			if marker.color != MarkerColors.BLUE:
				continue
			elif marker.comment in markers_comp:
				print("Uh..")
				exit
			markers_comp[marker.comment] = marker
	
	# Build tuplet
	markers = []
	change_list = []
	for marker in markers_orig:
		if marker.comment in markers_comp:
			marker_comp = markers_comp[marker.comment]
			markers.append((marker, marker_comp))
	print("")
	print("Shot ID                  Old Version      New Version   Offset since last change")
	print("---------------------    -----------      -----------   ------------------------")
	
	running_offset = Timecode(0)
	for orig, comp in markers:
		offset = comp.timecode.start - orig.timecode.start
		if offset != running_offset:
			print("Cut change at ", orig.comment,": ", orig.timecode.start, " -> ", comp.timecode.start, " (", str(offset - running_offset).rjust(12), ")")
			change_list.append(Marker(
				name="Locatorator",
				tc_start=str(comp.timecode.start),
				track="TC1",
				color=MarkerColors.WHITE.value,
				comment=f"Cut change: {(offset-running_offset).framenumber} frames since {path_orig.stem}",
				duration=1
			))
			running_offset = offset

	print("")

	with open("output.txt","w") as file_output:
		for marker in change_list:
			print(marker, file=file_output)

if __name__ == "__main__":

	main()