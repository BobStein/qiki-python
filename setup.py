import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("qiki/version.py", "r") as fh:
    version = fh.read().strip().strip('"')

setuptools.setup(
    name="qiki",
    version=version,
    author="Bob Stein",
    author_email="bob.stein@qiki.info",
    description="Unsiloed social web. Rate and relate anything. Any number of times. With any verb.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/BobStein/qiki-python",
    packages=setuptools.find_packages(),
    platforms=['any'],
    # license="CC0 1.0 Universal (CC0 1.0) Public Domain Dedication",
    # NOTE:  Saying the license in two places causes the Meta section on PyPI to double up:
    #        License: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication
    #                (CC0 1.0 Universal (CC0 1.0) Public Domain Dedication)
    classifiers=[
        "Development Status :: 1 - Planning",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: Wiki",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: Message Boards",
        "Topic :: Office/Business :: Groupware",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Other/Nonlisted Topic",
            # rating, reviewing, commenting, opinions
            # social
            # societal
            # governance
            # collaboration
            # networking
            # consensus
            # research
            # democracy
            # economics, economy, big data
            # emergence, disruption, reinvention
    ],
)
