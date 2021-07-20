# nwauto-toolkit
all the good things of network automation

Setup environment
=================

I'll be using Windows environment, but the dependencies should support Linux as well

1. Clone the repository
> git clone <link to repo>

2. Create the virtual environment (requires Python >=3.8.10)
> Use the system python pip to install poetry
> pip install poetry
> poetry env use python
> poetry install

3. Activate the shell in the VSCODE
> poetry shell
> code .

4. Optional add other packages to the virtual environment

> poetry add requests

5. Optional Update the virtual environment with the latest changes in the repository 

> git pull
> poetry update