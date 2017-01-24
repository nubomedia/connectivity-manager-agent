Connectivity Manager Agent
=====================================================================================

This project is part of NUBOMEDIA project: [NUBOMEDIA](http://www.nubomedia.eu/)

### Install

1. Compile and Install the Connectivity Manager Agent:
    ```bash
    sudo ./cm-agent.sh install	
    ```
This command checks that all the dependencies are installed on the host machine, for example git, python-pip, setuptools and installs all the required Python packages (using pip) in a virtual environment.
After doing that it compiles the source code and install the CM Agent to /opt/nubomedia/cm-agent.


2. Initialization of Agent config file: After installation you need to update the config file to reflect the correct OpenStack credentials
    ```bash
	sudo ./cm-agent.sh init
    ```
This command set the username and password for the usage of the Openstack environment. It is strongly required to set it. Or else it has to be edited manually in /etc/nubomedia/cm-agent.properties!

3. Make sure all Hosts within the tenant have opened the port 6640 for accessing the OVSDB via port and run the following command to allow it to be accessed remotely:
    ```bash
	sudo ovs-vsctl set-manager ptcp:6640
    ```
4. Make sure that controller for Openflow has been set for all compute and controller nodes running
    ```bash
    sudo ovs-vsctl set-controller br-int ptcp:6633
    ```
 
5. Manually start a screen session (it can't be started automatically because of the use of virtualenv's).
	```bash
	screen -m -d -S cm-agent
	```

6. Now within the screen session start the CM Agent using:
    ```bash
	sudo ./cm-agent.sh start
	```

The API of the CM Agent is now served on Port 8091.



What is NUBOMEDIA
-----------------

This project is part of [NUBOMEDIA], which is an open source cloud Platform as a
Service (PaaS) which makes possible to integrate Real Time Communications (RTC)
and multimedia through advanced media processing capabilities. The aim of
NUBOMEDIA is to democratize multimedia technologies helping all developers to
include advanced multimedia capabilities into their Web and smartphone
applications in a simple, direct and fast manner. To accomplish that objective,
NUBOMEDIA provides a set of APIs that try to abstract all the low level details
of service deployment, management, and exploitation allowing applications to
transparently scale and adapt to the required load while preserving QoS
guarantees.

Documentation
-------------

The [NUBOMEDIA] project provides detailed documentation including tutorials,
installation and [Development Guide].

Source
------

Source code for other NUBOMEDIA projects can be found in the [GitHub NUBOMEDIA
Group].

News
----

Follow us on Twitter @[NUBOMEDIA Twitter].

Issue tracker
-------------

Issues and bug reports should be posted to [GitHub Issues].

Licensing and distribution
--------------------------

Licensed under the Apache License, Version 2.0 (the "License"); you may not use
this file except in compliance with the License. You may obtain a copy of the
License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

Contribution policy
-------------------

You can contribute to the NUBOMEDIA community through bug-reports, bug-fixes,
new code or new documentation. For contributing to the NUBOMEDIA community,
drop a post to the [NUBOMEDIA Public Mailing List] providing full information
about your contribution and its value. In your contributions, you must comply
with the following guidelines

* You must specify the specific contents of your contribution either through a
  detailed bug description, through a pull-request or through a patch.
* You must specify the licensing restrictions of the code you contribute.
* For newly created code to be incorporated in the NUBOMEDIA code-base, you
  must accept NUBOMEDIA to own the code copyright, so that its open source
  nature is guaranteed.
* You must justify appropriately the need and value of your contribution. The
  NUBOMEDIA project has no obligations in relation to accepting contributions
  from third parties.
* The NUBOMEDIA project leaders have the right of asking for further
  explanations, tests or validations of any code contributed to the community
  before it being incorporated into the NUBOMEDIA code-base. You must be ready
  to addressing all these kind of concerns before having your code approved.

Support
-------

The NUBOMEDIA community provides support through the [NUBOMEDIA Public Mailing List].

[orchestrator]:http://openbaton.github.io
[vnfm]:https://github.com/nubomedia/nubomedia-msvnfm
[cma]:https://github.com/nubomedia/connectivity-manager-agent.git
[spring.io]:https://spring.io/
[bootstrap]:https://raw.githubusercontent.com/nubomedia/connectivity-manager/master/bootstrap
[Apache 2.0 License]: https://www.apache.org/licenses/LICENSE-2.0.txt
[Development Guide]: http://nubomedia.readthedocs.org/
[GitHub Issues]: https://github.com/nubomedia/bugtracker/issues
[GitHub NUBOMEDIA Group]: https://github.com/nubomedia
[NUBOMEDIA Logo]: http://www.nubomedia.eu/sites/default/files/nubomedia_logo-small.png
[NUBOMEDIA Twitter]: https://twitter.com/nubomedia
[NUBOMEDIA Public Mailing list]: https://groups.google.com/forum/#!forum/nubomedia-dev
[NUBOMEDIA]: http://www.nubomedia.eu
[LICENSE]:./LICENSE
