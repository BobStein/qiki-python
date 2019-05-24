import setuptools

with open("readme.html", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="qiki",
    version="0.0.1",
    author="Bob Stein",
    author_email="me@bobste.in",
    description="Unsiloed social web. Rate and relate anything. With any verb. Any number of times.",
    long_description=long_description,
    long_description_content_type="text/html",
    url="https://github.com/BobStein/qiki-python",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 1 - Planning",
        "Environment :: Web Environment",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "License :: Public Domain",
        "Operating System :: OS Independent",
    ],
)
