from setuptools import setup

setup(
	name="locatorator",
	version="1.0.0",
	packages=["locatorator"],
	install_requires=["posttools @ git+https://github.com/mjiggidy/posttools.git#egg=posttools","PySide6"],
	entry_points={
		"console_scripts":[
			"locatorator_cli = locatorator.__main__:bootstrap"
		],
        "gui_scripts":[
			"locatorator = locatorator.gui:main"
		]
	}
)