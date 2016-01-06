# Copyright 2015 Technische Universitaet Berlin
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import subprocess
import logging

__author__ = 'beb'


class Client(object):
    def exe_vsctl(self, args):
        # vsctl_args = ["ovs-vsctl"] + args
        pass

    def set_manager(self):
        # Implement subprocess to run this cmd on remote machine for other hosts, or define as prerequisite that has to
        #  be configured manually?
        subprocess.check_call(["sudo", "ovs-vsctl", "set-manager", "ptcp:6640"])
        pass

    def set_manager(self):
        # Implement subprocess to run this cmd on remote machine for other hosts, or define as prerequisite that has to
        #  be configured manually?
        subprocess.check_call(["sudo", "ovs-vsctl", "set-controller", "br-int", "ptcp:6633"])
        pass

    def get_port(self):
        pass

    def set_port(self, hypervisor_ip, port_id, action, action_id):
        subprocess.check_call(["sudo", "ovs-vsctl", "--db=tcp:%s:6640" % hypervisor_ip, "set", "port", "%s" % port_id,
                               "%s=%s" % (action, action_id)])

    def list_ports(self, hypervisor_ip):
        ports = subprocess.check_output(["sudo", "ovs-vsctl", "--format=json", "--db=tcp:%s:6640" % hypervisor_ip,
                                         "--columns=name,qos,tag", "list", "port"])
        return ports

    def list_port(self, hypervisor_ip, port_id):
        port = subprocess.check_output(["sudo", "ovs-vsctl", "--format=json", "--db=tcp:%s:6640" % hypervisor_ip,
                                         "--columns=name,qos,tag", "list", "port", "%s" %port_id])
        return port


    def list_interfaces(self, hypervisor_ip):
        interfaces = subprocess.check_output(["sudo", "ovs-vsctl", "--format=json", "--db=tcp:%s:6640" % hypervisor_ip,
                                              "--columns=name,external-ids,other-config", "list", "interface"])
        return interfaces

    def create_queue(self, hypervisor_ip, min_rate, max_rate):
        queue_id = subprocess.check_output(["sudo", "ovs-vsctl", "--db=tcp:%s:6640" % hypervisor_ip, "create", "queue",
                                            "other-config:min-rate=%d" % min_rate,
                                            "other-config:max-rate=%d" % max_rate])
        return queue_id.strip('\n')

    def set_qos_ovs(self,hypervisor_ip,qos_id,queue_id,queue_number): #will return None if everything works fine
        cmd = "sudo ovs-vsctl --db=tcp:" + hypervisor_ip + ":6640 add qos " + qos_id + " queues " + queue_number + "=" + queue_id

        return subprocess.check_output(cmd.split())

    def list_queues(self, hypervisor_ip):
        queues = subprocess.check_output(["sudo", "ovs-vsctl", "--format=json", "--db=tcp:%s:6640" % hypervisor_ip,
                                          "list", "queue"])
        return queues

    # def list_queue(self, hypervisor_ip, queue_id):
    #     queue = subprocess.check_output(["sudo", "ovs-vsctl", "--format=json", "--db=tcp:%s:6640" % hypervisor_ip,
    #                                       "list", "queue", "%s" % queue_id])
    #     return queue

    def create_qos(self, hypervisor_ip, queue_string, queues):
        cmd = "sudo ovs-vsctl --db=tcp:" + hypervisor_ip + ":6640 create qos type=linux-htb " + queue_string + " " + queues
        qos_id = subprocess.check_output(cmd.split())
        return qos_id.strip('\n')

    def del_queue(self, hypervisor_ip, qos_id,queue_id,queue_number):
        return subprocess.check_call(["sudo", "ovs-vsctl", "--db=tcp:%s:6640" % hypervisor_ip, "remove", "qos", "%s" % qos_id,"queues", "%s" % queue_number, "--", "destroy","queue","%s" % queue_id])

    def del_qos(self, hypervisor_ip, qos_id):
        return subprocess.check_call(["sudo", "ovs-vsctl", "--db=tcp:%s:6640" % hypervisor_ip, "destroy", "qos", "%s" % qos_id])

    # def del_all_qos(self, hypervisor_ip):  is not possible to delete all qoses if the vm's are still running, is possible to delete a QoS if the vm is already terminated
    #     subprocess.check_call(["sudo", "ovs-vsctl", "--db=tcp:%s:6640" % hypervisor_ip, "--all", "destroy", "qos"])

    def list_qoss(self, host_ip):
        qoss = subprocess.check_output(["sudo", "ovs-vsctl", "--format=json", "--db=tcp:%s:6640" % host_ip,
                                        "--columns=_uuid,queues,type", "list", "qos"])
        return qoss

    def list_qosandqueue(self,hypervisor_ip,qos_id):
        cmd = "sudo ovs-vsctl --format=json --db=tcp:" + hypervisor_ip + ":6640 --columns=queues list qos " + qos_id
        return subprocess.check_output(cmd.split())
    # def list_qos(self, host_ip, qos_id):
    #     qos = subprocess.check_output(["sudo", "ovs-vsctl", "--format=json", "--db=tcp:%s:6640" % host_ip,
    #                                     "--columns=_uuid,queues,type", "list", "qos", "%s" % qos_id])
    #     return qos


    """
    adding a flow for bridge internal with port
    sudo ovs-ofctl add-flow tcp:192.168.41.45 "dl_type=0x0800,nw_dst=10.0.0.23,nw_proto=6,tp_dst=5001,priority=2,actions=enqueue:28:2"
    """
    def add_flow_to_queue(self, hypervisor_ip, src_ip, destination_ip, protocol, priority, ovs_port_number, queue_port):

        ret = {}
        protocoll = ""

        if protocol == "tcp":
            protocoll = "6"
        elif protocol == "udp":
            protocoll = "17"

        flow = "dl_type=0x0800,nw_dst=" + destination_ip + ",nw_src=" + src_ip + ",nw_proto=" + protocoll + ",priority=" + priority + "actions=enqueue:" \
               + ovs_port_number + ":" + queue_port
        logging.debug('Flow to be added to the switch: %s', flow )
        output = subprocess.check_output(["sudo", "ovs-ofctl", "add-flow", "tcp:%s" % hypervisor_ip, flow])

        logging.debug("Output %s", output)

        ret['nw_src'] = src_ip
        ret['nw_dst'] = destination_ip
        ret['nw_proto'] = protocol
        ret['priority'] = priority
        return ret

    def remove_flow_dest(self,hypervisor_ip,destination_ip, protocol):

        if protocol == "tcp":
            protocol = "6"
        elif protocol == "udp":
            protocol = "17"

        flow = "dl_type=0x800,nw_dst=" + destination_ip + ",nw_proto=" + protocol

        ret = subprocess.check_output(["sudo","ovs-ofctl","del-flows","tcp:%s" % hypervisor_ip,flow])
        return ret #will be null always

    def remove_flow_src(self,hypervisor_ip,src_ip, protocol):

        if protocol == "tcp":
            protocol = "6"
        elif protocol == "udp":
            protocol = "17"

        flow = "dl_type=0x800,nw_src=" + src_ip + ",nw_proto=" + protocol

        ret = subprocess.check_output(["sudo","ovs-ofctl","del-flows","tcp:%s" % hypervisor_ip,flow])
        return ret #will be null if success, other values otherwise

    """
    sudo ovs-ofctl queue-stats tcp:192.168.41.45
    """
    def list_queue_stats(self, hypervisor_ip):
        queue_stats = subprocess.check_output(["sudo", "ovs-ofctl", "queue-stats", "tcp:%s" % hypervisor_ip])
        return queue_stats

    """
    sudo ovs-ofctl dump-ports-desc tcp:192.168.41.45
    """
    def list_port_desc(self, hypervisor_ip):
        port_desc = subprocess.check_output(["sudo", "ovs-ofctl", "dump-ports-desc", "tcp:%s" % hypervisor_ip])
        return port_desc

    def dump_flows(self):
        cmd = "sudo ovs-ofctl dump-flows br-int"
        flows_string = subprocess.check_output(cmd.split())
        return flows_string

    """
    Setting ability to send flow rules to the switches remotely
    ovs-vsctl set-controller br-int ptcp:6633
    """

    """
    sudo ovs-vsctl del-controller br-int
    """
