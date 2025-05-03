from setuptools import setup, find_packages

_ = setup(
    name="compliance",
    version="0.1.0",
    description="A Python application with MongoDB integration",
    author="",
    author_email="",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pymongo>=4.6.1",
        "python-dotenv>=1.0.1",
    ],
    python_requires=">=3.11",
) 