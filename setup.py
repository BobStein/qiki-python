import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("qiki/version.py", "r") as fh:
    version = fh.read().strip().strip('"')

setuptools.setup(
    name="qiki",
    version=version,
    author="Bob Stein",
    author_email="me@bobste.in",
    description="Unsiloed social web. Rate and relate anything. Any number of times. With any verb.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/BobStein/qiki-python",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 1 - Planning",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: Public Domain",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: Wiki",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: Message Boards",
        "Topic :: Office/Business :: Groupware",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Other/Nonlisted Topic",
            # rating
            # reviewing
            # commenting
            # social
            # societal
            # governance
            # collaboration
            # consensus
            # economics
            # research
            # emergence, disruption, reinvention, hyper-democracy
    ],
)



