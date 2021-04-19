# Installation
```bash
git clone https://github.com/RaeedAhmed/twitch-py.git
cd twitch-py
```
## Local
Ensure `wget` is installed on your machine, or edit the install script to your liking
```bash
./install
```
## Running the script
### Create a virtual environment
This can be done in a number of ways, but using python built-in `venv` module:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
Installing dependencies and running:
```bash
pip install .
cd twitch_py/
python main.py
```
Go to `localhost:8080` and follow login prompt if not signed in.
