.. _intro:

Getting Started
===============

To make use of this project you will need a desktop Computer or Laptop. 
Linux, Windows and MacOS are all supported.

To get going you will need to install the following software on your 
Computer:

- The Minecraft Java Client (with Minecraft account purchase)
- Visual Studio Code
- Python
- Docker
- Minecraft Interactive World Builder library

.. note::
    The tutorials for this project are intended to be accessible for
    complete beginners. However, this first step of getting all of the 
    software installed requires a little bit of knowledge of the basics of
    your operating system. 

    For this first step, I recommend that novices get a little help from 
    someone with computer experience.


The Minecraft Java Client
-------------------------

You will need to purchase a license for Minecraft from Microsoft.

Go to this site to buy your copy, if you do not already have one:

    https://www.minecraft.net/en-us/store/minecraft-java-bedrock-edition-pc

Once you have a license, download the Java client to
the computer where you will be trying out Minecraft Interactive World Builder
(MCIWB). This is the download link for the Java client:
    
        https://www.minecraft.net/en-us/download

Microsoft has now bundled the Java and Bedrock editions together. 
We are using the Java edition here but this project could be adapted to
work fir either.

Visual Studio Code
------------------

This is the tool we will use to edit our Python code. If you are already
a developer then you can use your preferred tool instead. The tutorials
will use Visual Studio Code, so if you are new to programming this is 
a recommended install.

This is free, open-source software.

This link provides downloads for all flavours of VSCode:
    
    https://code.visualstudio.com/download


Python
------

The Python Programming Language is also free an open-source.

This is essential for working with MCIWB. On Linux you will likely already 
have it installed. Note that this project has been tested with
Python 3.9 and 3.10 but other versions may also be OK.

Windows
~~~~~~~

Download the Windows Installer (64-bit) for the latest version from this link:

    https://www.python.org/downloads/Windows

Mac
~~~

Download the macOS 64-bit universal2 installer for the latest version 
from this link:

    https://www.python.org/downloads/macos

Linux
~~~~~

See these instructions if you do not already have a Python installation:
    
    https://docs.python-guide.org/starting/install3/linux/

Note the the above discuss an older version of Python. You should install
Python3.10 if it is available for your system. Python 3.9 is also OK.


Docker
------

Docker is a tool that allows you to run your Minecraft Server in a container.
This makes it easy to run and avoids having to manually install the server
code.
You do not need to understand too much about this since MCIWB will automatically
use docker on your behalf.

The easiest way to install Docker is to use Docker Desktop which is free to
use for individuals.

Instructions for installation are here:

    https://docs.docker.com/get-docker/


Minecraft Interactive World Builder library
-------------------------------------------

The final component is this project itself. This needs to be added to the 
Python installation we already made above.

The Package Installer for Python (Pip) is used to get MCIWB from the package 
registry called Pypi.

To perform these steps you will need to open a command line 
console on your computer and 
type the commands listed below.

First get pip:

    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python get-pip.py

Now use pip to get MCIWB:

    pip install mciwb

TODO: verify this works on WINDOWS!
TODO: how to make sure python is on the path??? 
