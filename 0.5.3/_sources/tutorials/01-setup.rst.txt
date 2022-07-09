.. _intro:

01 Setup
========

To use Minecraft Interactive World Builder (MCIWB) you will need a desktop 
Computer or Laptop. Linux, Windows and MacOS are all supported.

To get going you first need to install the following software on your 
Computer:

- The Minecraft Java Client (with Minecraft account purchase)
- Docker Desktop
- Visual Studio Code
- Python
- Minecraft Interactive World Builder Python package

.. warning::
    The tutorials for this project are intended to be accessible for
    complete beginners. However, this first step of getting all of the 
    software installed may need a little bit of knowledge of the basics of
    your operating system. 

    For Tutorial 01, I recommend that novices get a little help from 
    someone with computer experience. This setup tutorial need only 
    be done once (per computer) and the remaining tutorials should not
    require prior knowledge.


The Minecraft Java Client
-------------------------

If you already have the Minecraft Java Client installed proceed to `vscode`.

You will need to purchase a license for Minecraft from Microsoft.

Go to this site to buy your copy, if you do not already have one:

    https://www.minecraft.net/en-us/store/minecraft-java-bedrock-edition-pc  

Once you have a license, download the Java client to
the computer where you will be trying out Minecraft Interactive World Builder
(MCIWB). This is the download link for the Java client:
    
        https://www.minecraft.net/en-us/download

Microsoft has now bundled the Java and Bedrock editions together. 
We are using the Java edition here but this project could be adapted to
work for either.

When you start Minecraft you will be asked to login with your Microsoft details,
note that the 'Mojang Login' option is only for legacy users who have not
yet migrated.

When you have successfully launched the Minecraft Launcher, you will see a
a screen like the following. Leave this screen open and move on to the rest
of the tutorial. We will come back here and connect to a Minecraft server in a
later step.

    .. image:: ../images/launcher.png
        :alt: Minecraft Launcher
        :width: 600px
        :align: left

.. _vscode:

Docker Desktop
--------------

Docker is a tool that allows you to run your Minecraft Server in a container.
This makes it easy to run and avoids having to manually install the server
code.
You do not need to understand too much about this since MCIWB will automatically
use docker on your behalf.

The easiest way to install Docker is to use Docker Desktop which is free to
use for individuals.

Windows:
    Docker Desktop requires WSL2 and a linux distribution to go with it.
    So you should first install Ubuntu 22.04 LTS from here 
    - https://apps.microsoft.com/store/detail/ubuntu-2204-lts/9PN20MSR04DW

All Platforms:
    Instructions for Docker Desktop installation for all platforms are here:
    - https://docs.docker.com/get-docker/

For mciwb to work you will need Docker Desktop to be running before you 
start Visual Studio Code. So start it from the start menu before moving to 
the next step.

To make things easier next time you could go into settings (accessed
via the cog icon in the title bar) and tick the option 
``Start Docker Desktop when you log in``.


Visual Studio Code
------------------

This is the tool we will use to edit our Python code. If you are already
a developer then you can use your preferred IDE instead. The tutorials
will use Visual Studio Code, so if you are new to programming this is 
a recommended install.

VSCode is free, open-source software.

This link provides downloads for all flavours of VSCode:
    
    https://code.visualstudio.com/download


Command Line
------------

From now on we are going to start using the command line. You are free to use
whatever terminal program you like, however I recommend that you use the 
integrated terminal inside of Visual Studio Code.

Here we will set up our initial VSCode work folder and get a command line
prompt.

.. note::

    **Windows Users: Important**

    We are going to use 'Windows Subsystem for Linux 2' or WSL2.
    Go here first to get VSCode connected to WSL2: 
    `wsl2`

To get set up we are going to launch VSCode

Python
------

The Python Programming Language is also free an open-source.

This is essential for working with MCIWB. On Linux you will likely already 
have it installed. Note that this project has been tested with
Python 3.9 and 3.10 but other versions may also be OK.

Use the following links to Download and install Python:

Windows:
    Use the Microsoft store link here
    https://apps.microsoft.com/store/detail/python-310/9PJPW5LDXLZ5

Mac:
    Download the macOS 64-bit universal2 installer for the latest version 
    from this link: https://www.python.org/downloads/macos

Linux:
    See these instructions if you do not already have a Python installation:
    https://docs.python-guide.org/starting/install3/linux/.
    (These instruction discuss an older version of Python. You 
    should install Python3.10 if it is available for your system. 
    Python 3.9 is also OK.)


mciwb
-----

First create yourself a work folder in your Documents. The procedure is 
similar for all operating systems.

- Hit the command or Windows Key and type ``documents``
- This should show your Documents folder
- Right click in the Documents folder and select ``New Folder``
- Type a new name for your folder ``mciwb_work``
- Launch VSCode 
  - Menu bar -> File -> Open Folder
  - Select the folder you created in the previous step
  - Click ``Yes, I trust the authors`` (because you will be the author)
  - Menu bar -> Terminal -> New terminal

You should now have a VSCode Window open with a command prompt 
(also know as a terminal) at the bottom
like the following (image from Windows OS):

    .. image:: ../images/vscode_hello.png
        :alt: VSCode Startup
        :width: 600px
        :align: left

Minecraft Interactive World Builder library
-------------------------------------------

The final component is this project itself. This needs to be added to the 
Python installation we already made above. Again, this is free open open-source
software.

The Package Installer for Python (Pip) is used to get MCIWB from the package 
registry called Pypi.

Using the command prompt type in the following commands: 

First get pip:

    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python get-pip.py

Now use pip to get MCIWB:

    pip install --user mciwb

Windows:
    This is really annoying, but Windows has an appallingly complicated way
    of setting up paths. You will need to take a look at this tutorial
    to get the next step to work.  
    TODO TODO TODO    
    WARNING: The script mciwb.exe is installed in 'C:\Users\giles\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.10_qbz5n2kfra8p0\LocalCache\local-packages\Python310\Scripts' which is not on PATH.
    wsl --install -d Ubuntu




TODO: verify this works on WINDOWS!
TODO: how to make sure python is on the path??? 
