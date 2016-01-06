Connectivity Manager Agent
=====================================================================================

1. Compile and Install the Connectivity Manager Agent:
⋅⋅⋅    ``
    sudo ./cm-agent.sh install	
    ``
⋅⋅⋅This command checks that all the dependencies are installed on the host machine, for example git, python-pip, setuptools and installs all the required Python packages (using pip) in a virtual environment.
⋅⋅⋅After doing that it compiles the source code and install the CM Agent to /opt/nubomedia/cm-agent.


2. Initialization of Agent config file: After installation you need to update the config file to reflect the correct OpenStack credentials
⋅⋅⋅    ``
	sudo ./cm-agent.sh init
    ``
⋅⋅⋅This command set the username and password for the usage of the Openstack environment. It is strongly required to set it. Or else it has to be edited manually in /etc/nubomedia/cm-agent.properties!

3. Make sure all Hosts within the tenant have opened the port 6640 for accessing the OVSDB via port and run the following command to allow it to be accessed remotely:
⋅⋅⋅    ``
	sudo ovs-vsctl set-manager ptcp:6640
    ``
4. Make sure that controller for Openflow has been set for all compute and controller nodes running
    ``
    sudo ovs-vsctl set-controller br-int ptcp:6633
    ``
 
5. Manually start a screen session (it can't be started automatically because of the use of virtualenv's).
⋅⋅⋅	``
	screen -m -d -S cm-agent
	``

6. Now within the screen session start the CM Agent using:
⋅⋅⋅    ``
	sudo ./cm-agent.sh start
	``

The API of the CM Agent is now served on Port 8091.