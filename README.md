# Multiplayer Turing-test Framework
The implementation of the paper, `A Turing-test Framework for Multiplayer Games (under review)`.  
This framework has two software; server for an experiment and client for a participant. (See the demo in below.)
All source code is in Python 3 and you can customize this framework into your own Turing-test experiment.  
For the multiplayer Turing-test, this framework supports network connection for remote joining.

# Demonstration
![Demonstration](./screenshot/demo.gif)

The left-side one is the server for experimenter, and the right-side one is a client software for a participant.  
Once a participant connected to the server, the experimenter can control all settings related to the Turing-test experiment; are sync with the client automatically.  
The environment could be replaced to other ones, though it doesn't support multiplaying feature originally. Our framework could extend your single-player environment into a multiplayer interface.
In our demonstration, a multiplayer game `Overcooked!` is used for sample. If you want to change the environment, it will be okay.

A detailed documentation will be deployed upon the paper accepted.

# Installation
### Requirement
- [Download Anaconda](https://www.anaconda.com/)
```bash
conda create -n turingtest python=3.8
conda activate turingtest
pip3 install -r requirements.txt
```

### Launch
**Starting a server**
```bash
python3 server.py
```
**Starting a client** (You can run the client software on other PC and connect via IP address.)
```
python3 client.py
```


# Disclaimer
Disclaimer
All the contents in the `overcooked_ai_py` directory are from the original repository of [HumanCompatibleAI/overcooked_ai](https://github.com/HumanCompatibleAI/overcooked_ai)