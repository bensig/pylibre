from setuptools import setup, find_packages

setup(
    name="pylibre",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "python-dotenv",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "pylibre=pylibre.cli:main",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A Python client for interacting with the Libre blockchain",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/pylibre",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires=">=3.7",
)
