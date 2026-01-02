"""
Setup script for qbit2track
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="qbit2track",
    version="1.0.0",
    author="qbit2track",
    author_email="",
    description="Extract torrents from qBittorrent and prepare for private tracker upload",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/qbit2track",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: File Sharing",
        "Topic :: Multimedia :: Video",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "qbit2track=qbit2track.cli:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "qbit2track": ["config/*.yaml"],
    },
)
