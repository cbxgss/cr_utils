from setuptools import setup, find_packages

setup(
    name='cr_utils',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        "litellm==1.67.0.post1",
        "omegaconf>=2.3.0",
        "openai>=1.74.0",
        "pandas>=2.2.3",
        "psutil>=7.0.0",
        "tenacity>=9.1.2",
        "prettytable>=3.16.0",
        "ipdb>=0.13.13",
    ],
    author='Rong Cheng',
    author_email='chengrong@tju.edu.cn',
    description='cr_utils',
    license='MIT',
    keywords='sample setuptools development',
    url='https://github.com/cbxgss/cr_utils.git'
)