import setuptools
from version import __version__

setuptools.setup(
    name = "jvmdumps",
    version = __version__,
    author = "Enrique Velasco",
    author_email = "enrique.velasco@servexternos.gruposantander.com",
    description = "Microservice for generating memory dumps from pods.",
    long_description = "With this microservice, pod heapdumps and treaddumps can be generated to analyze problems",
    long_description_content_type = "text/markdown",
    url = "http://mypythonpackage.com",
    packages = setuptools.find_packages(),
    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires = [
    ],
    python_requires = '>=3.9',
)
