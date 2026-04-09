from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="llm-diagnostic-reasoning",
    version="1.0.0",
    author="Zhangjian",
    author_email="zhangjian@zju.edu.cn",
    description="🔥 让AI像专家一样诊断 | 3种创新方法 | 跨领域通用",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Zhangjian-zju/llm-diagnostic-reasoning",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "anthropic>=0.18.0",
        "openai>=1.0.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "matplotlib>=3.7.0",
        "networkx>=3.0",
        "streamlit>=1.30.0",
        "plotly>=5.18.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "diagnose=diagnose:main",
        ],
    },
)
