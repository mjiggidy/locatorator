import sys, typing, enum, re, copy
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
	pass

class MarkerColor(enum.Enum):
	"""Avid marker colors"""
	RED = "red"
	GREEN = "green"
	BLUE = "blue"
	CYAN = "cyan"
	MAGENTA = "magenta"
	YELLOW = "yellow"
	BLACK = "black"
	WHITE = "white"

class Marker:

	_pat_bad_chars = re.compile("[\n\t]")

	def __init__(self, *, name:str, tc_start:typing.Union[str,Timecode], track:str, color:typing.Union[str,MarkerColor], comment:str, duration:int):

		self._name    = self._sanitize_string(name)
		self._tc      = TimecodeRange(start=Timecode(tc_start), duration=Timecode(duration))
		self._track   = self._sanitize_string(track)
		self._color   = MarkerColor(color)
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
	def color(self) -> MarkerColor:
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
			str(self.timecode.duration.frames)
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
		return hash(self.name, self.timecode, self.comment)
		
	
	@classmethod
	def _sanitize_string(cls, text:str) -> str:
		"""Don't try anything silly"""
		return cls._pat_bad_chars.sub("",text).strip()

def main() -> None:
	"""Markers"""

	if len(sys.argv) < 2:
		sys.exit(f"Usage: {__file__} markerlist.txt")
	
	with open(sys.argv[1]) as file_markers:

		markers = []

		for idx, line in enumerate(l.rstrip('\n') for l in file_markers.readlines()):
			markers.append(Marker.from_string(line))

			print(sorted(markers))

if __name__ == "__main__":

	main()