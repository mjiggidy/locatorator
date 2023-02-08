from setuptools import setup

setup(
	name="locatorator",
	version="1.0.0",
	packages=["locatorator"],
	install_requires=["posttools @ git+https://github.com/mjiggidy/posttools.git#egg=posttools"],
	entry_points={
		"console_scripts":[
			"locatorator = locatorator.__main__:bootstrap"
		]
	}
)