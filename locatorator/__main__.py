import sys
import locatorator
	
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
		markers_old = locatorator.get_marker_list_from_file(file_markers)
	markers_old.sort(key=lambda x:x.timecode.start)
		
	with open(sys.argv[2]) as file_markers:
		markers_new = locatorator.get_marker_list_from_file(file_markers)
	markers_new.sort(key=lambda x:x.timecode.start)
	
	# Pair markers together by comment (shot id)
	markers_changes = locatorator.build_marker_changes(markers_old, markers_new)

	if not markers_changes:
		print("No changes were detected.")
		return

	# Write changes to new marker list
	with open("changes.txt", "w") as file_output:
		locatorator.write_change_list(markers_changes, file_output)
		
	print("Marker list output to changes.txt")

def bootstrap():
	"""Entrypoint via setup.py `entry_point`"""

	try:
		main()
	except Exception as e:
		sys.exit(e)

if __name__ == "__main__":

	bootstrap()
