from setuptools import setup, find_packages

setup(
    name="paper-notes",
    version="1.0.0",
    description="研究生论文阅读笔记管理工具",
    packages=find_packages(),
    install_requires=[
        "PyPDF2>=3.0.0",
        "python-dateutil>=2.8.0",
    ],
    entry_points={
        "console_scripts": [
            "paper-notes=paper_notes.cli:main",
        ],
    },
    python_requires=">=3.8",
)
