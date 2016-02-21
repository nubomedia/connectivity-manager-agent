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

import logging
import json
import re
from clients.keystone import Client as KeystoneClient
from clients.nova import Client as NovaClient
from clients.neutron import Client as NeutronClient
from clients.ovs import Client as OVSClient

__author__ = 'beb'


class Agent(object):
    def __init__(self):
        self.cloud = Cloud()

    @property
    def list_hypervisors(self):
        cloud_info = {'hypervisors':[]}
        interfaces = {}
        qoss = {}
        queues = {}
        port = {}
        queue_rates = {}
        hypervisors_servers = {}
        hypervisors = self.cloud.read_hypervisor_info()
        logging.info('Getting list of hypervisors: %s', hypervisors)
        servers = self.cloud.read_server_info()
        logging.info('Getting list of servers: %s', servers)

        server_ips = self.cloud.get_server_ips()
        logging.info('Getting list of all server IPs: %s', server_ips)

        for kh, vh in hypervisors.items():
            hypervisor_info = {}
            hypervisor_info['name'] = kh
            hypervisor_info['cpu_total'] = vh.get('cpu_total')
            hypervisor_info['cpu_used'] = vh.get('cpu_used')
            hypervisor_info['id'] = vh.get('id')
            hypervisor_info['instances'] = vh.get('instances')
            hypervisor_info['ip'] = vh.get('ip')
            hypervisor_info['ram_total'] = vh.get('ram_total')
            hypervisor_info['ram_used'] = vh.get('ram_used')
            hypervisor_info['servers'] = []

            hypervisors_servers[kh] = self.cloud.get_server_hypervisor_info(servers, kh)
            logging.info('Getting list of servers matched with hypervisor: %s', hypervisors_servers)

            interfaces[kh] = Host(kh).list_interfaces_hypervisor(hypervisors)
            logging.info('Interfaces for %s: %s', kh, interfaces)

            queues[kh] = Host(kh).list_queues_hypervisor(vh.get('ip'))
            logging.info('Queues for %s: %s', kh, queues)

            queue_rates[kh] = self.cloud.get_queue_rates(vh.get('ip'))
            logging.info('Queue rates for %s: %s', kh, queue_rates)

            qoss[kh] = Host(kh).list_qos_hypervisor(vh.get('ip'))
            logging.info('QoS\'s for %s: %s', kh, qoss)

            port[kh] = Host(kh).list_port_desc_hypervisor(vh.get('ip'))
            logging.info('Port desc\'s for %s: %s', kh, port)

            for hs in hypervisors_servers[kh]:
                host_info = {}
                host_info['id'] = hs
                for ks, vs in servers.items():
                    if ks == hs:
                        host_info['name'] = vs.get('name')
                        for ki, vi in server_ips.items():
                            if ki == hs:
                                host_info['interfaces'] = []
                                for iface in vi:
                                    interface = {}
                                    try:
                                        interface['ip'] = iface
                                        neutron_port_id = self.cloud.get_neutron_port(iface)
                                        ovs_port_id = self.cloud.get_port_id(interfaces[kh], neutron_port_id)[0]
                                        #interface['neutron_port'] = neutron_port_id
                                        #interface['ovs_port_id'] = ovs_port_id
                                        ovs_port_num = self.cloud.get_ovs_port_num(port[kh], ovs_port_id)
                                        interface['ovs_port_number'] = ovs_port_num
                                        qos_id = Host(kh).get_port_qos(vh.get('ip'), ovs_port_id)
                                        interface['qos'] = self.cloud.get_qos_queue(qos_id, queues[kh],
                                                                                         qoss[kh])
                                    except Exception, e:
                                        logging.info('Exception %s', e)
                                        interface['ip'] = None
                                        interface['neutron_port'] = None
                                        interface['ovs_port_id'] = None
                                        interface['qos'] = None
                                        continue
                                    host_info['interfaces'].append(interface)
                hypervisor_info['servers'].append(host_info)
            cloud_info['hypervisors'].append(hypervisor_info)

        logging.info('Cloud info: %s', cloud_info)
        return cloud_info

    def get_hypervisor_map(self):
        hypervisors = self.cloud.read_hypervisor_info()
        servers = self.cloud.read_server_info()
        response = {'hypervisors': []}

        for hn, hd in hypervisors.items():
            hypervisor_info = {}
            hypervisor_info['name'] = hn
            hypervisor_info['servers'] = []
            hypervisor_servers_id = self.cloud.get_server_hypervisor_info(servers,hn)

            for server_id in hypervisor_servers_id:
                for sid, sinfo in servers.items():
                    if server_id == sid:
                        hypervisor_info['servers'].append(sinfo.get('name'))
            response['hypervisors'].append(hypervisor_info)

        return response



    def set_qos(self, qos_args):
        qos_status = {'values':[]}
        hypervisors = self.cloud.read_hypervisor_info()

        _qos_args = json.loads(qos_args)
        for hyperv in _qos_args.get('values'):
            hypervisor = {}
            interfaces = Host(hyperv.get('hypervisor_id')).list_interfaces_hypervisor(hypervisors)
            hypervisor['server_id'] = hyperv.get('server_id')
            if type(hyperv) != unicode:
                logging.info('QoS rates for server %s: %s',hyperv.get('server_id'), hyperv.get('interfaces'))
                hypervisor['interfaces'] = []
                for iface in hyperv.get('interfaces'):
                    result = Host(hyperv.get('hypervisor_id')).set_qos_vm(iface,interfaces, hyperv.get('server_id'))
                    hypervisor['interfaces'].append(result)
            hypervisor['hypervisor_id'] = hyperv.get('hypervisor_id')
            qos_status['values'].append(hypervisor)

        logging.info('QoS status after POST: %s', qos_status)
        return qos_status

    def add_new_queue(self,qos_json):
        qos_args = json.loads(qos_json)

        for server in qos_args:
            host = Host(server.get('hypervisor_id'))
            for val in server.get('values'):
                for queue in val.get('queues'):
                    rates = queue.get('rates')
                    queue['queue_uuid'] = host.create_queue(rates.get('min_rate'),rates.get('max_rate'))
                    host.link_queue_to_qos(val.get('qos_uuid'),queue['queue_uuid'],queue.get('queue_id'))

        return qos_args


    def destroy_qos(self,hypervisor_hostname,qos_id):

        qos_status = {}

        logging.info('Deleting QoS on host : %s ', hypervisor_hostname)
        qos_status[hypervisor_hostname] = Host(hypervisor_hostname).dell_qos(qos_id)

        logging.info('After deleting all QoS: %s', qos_status)
        return qos_status

    def destroy_queue(self,hypervisor_name,queue_id,queue_number, qos_id):

        qos_status = {}

        qos_status = Host(hypervisor_name).del_queue(queue_number,queue_id,qos_id)

        return qos_status

    def set_flow(self, flow_args):

        flow_status = {'flows':[]}

        _flow_args = json.loads(flow_args)
        for add_flows in _flow_args.get('flows'):
            hypervisor_status = {}
            host = Host(add_flows.get('hypervisor_id'))
            hypervisor_status['hypervisor_id'] = host.hypervisor
            flow_config = add_flows.get('qos_flows')
            hypervisor_status['server_id'] = add_flows.get('server_id')
            hypervisor_status['qos_flows'] = host.set_flow_vm(flow_config)
            flow_status['flows'].append(hypervisor_status)

        return flow_status

    def _remove_flow(self,hypervisor_name,flow_protocol,flow_ip):
        host = Host(hypervisor_name)
        logging.debug("REMOVE FLOW AGENT hypervisor name %s flow protocol %s flow ip %s",hypervisor_name,flow_protocol,flow_ip)
        ret = host.remove_flow(flow_ip,flow_protocol)
        return ret

    def get_new_server_info(self,hypervisor_name,server_name):
        target_server_info = self.cloud.get_new_server(hypervisor_name,server_name)
        return target_server_info


class Cloud(object):
    def __init__(self):
        #self.keystoneclient = KeystoneClient()
        #self.endpoint = self.keystoneclient.get_endpoint(service_type='network', endpoint_type=None)
        self.novaclient = NovaClient()
        self.neutronclient = NeutronClient()

    def get_vm_host_infos(self, vm_id, cloud_info):

        for hk, hv in cloud_info.items():
            for uk in hv['servers']:
                if uk.get('id') == vm_id:
                    return uk
        return -1

    def read_hypervisor_info(self):
        host_info = {}
        hypervisors = self.novaclient.get_hypervisors()
        for hypervisor in hypervisors:
            host_info[hypervisor.hypervisor_hostname] = {}
            # host_info[hypervisor.id]['all'] = hypervisor._info
            host_info[hypervisor.hypervisor_hostname]['id'] = hypervisor.id
            host_info[hypervisor.hypervisor_hostname]['ip'] = hypervisor.host_ip
            host_info[hypervisor.hypervisor_hostname]['instances'] = hypervisor.running_vms
            host_info[hypervisor.hypervisor_hostname]['cpu_used'] = hypervisor.vcpus_used
            host_info[hypervisor.hypervisor_hostname]['cpu_total'] = hypervisor.vcpus
            host_info[hypervisor.hypervisor_hostname]['ram_used'] = hypervisor.memory_mb_used
            host_info[hypervisor.hypervisor_hostname]['ram_total'] = hypervisor.memory_mb
        logging.info('Reading info of all hypervisors %s', host_info)
        return host_info

    def get_hypervisor_ip(self, hyp_hostname):
        hypervisors = self.novaclient.get_hypervisors()
        for hypervisor in hypervisors:
            if hypervisor.hypervisor_hostname == hyp_hostname:
                return hypervisor.host_ip

    def read_server_info(self):
        server_info = {}
        servers = self.novaclient.get_servers()
        for server in servers:
            server_info[server.id] = {}
            server_info[server.id] = server._info
        logging.info('Reading info of all servers %s', server_info)
        return server_info

    def get_server_ips(self):
        servers = self.novaclient.get_servers()
        ips = {}
        for server in servers:
            ips[server.id] = self.get_server_ip(server)
        logging.info('All server IPs %s', ips)
        return ips

    def get_neutron_port(self, ip):
        port = self.neutronclient.get_ports(ip)
        logging.info('Getting Neutron port ID %s for IP %s', port, ip)
        return port


    """
    Format of hypervisor_qos
    [[[u'uuid', u'1ce97624-e065-4999-a6bc-a980b1fb3b28'], [u'map', [[0, [u'uuid', u'8462e645-6198-4964-984b-004136a5ed72']]]], u'linux-htb'], [[u'uuid', u'52a89cf1-e45a-4c02-b823-769d5be18d13'], [u'map', [[0, [u'uuid', u'69f2dedc-cee9-44d3-80bb-f36f67b5f2ea']]]], u'linux-htb'], [[u'uuid', u'82d072f1-5842-46c5-a879-4f27f265bd79'], [u'map', [[0, [u'uuid', u'c4584bf9-a616-4396-a1ef-b40a18527f61']]]], u'linux-htb'], [[u'uuid', u'cbe550cd-fbdc-4a09-a0e7-525bca5c5313'], [u'map', [[0, [u'uuid', u'75f7025e-a3fd-4220-8a9f-bc24fe0715a5']]]], u'linux-htb'], [[u'uuid', u'f807a246-4064-4577-806e-76dfe623dda0'], [u'map', [[1, [u'uuid', u'ed87baa7-1f20-43fa-96d3-8347592153f5']]]], u'linux-htb'], [[u'uuid', u'9cd461b3-f9b6-49b9-bac4-c71c19d1d2d0'], [u'map', [[1, [u'uuid', u'ecfcb9ce-7f6d-4e29-9361-4faec1ac45bf']]]], u'linux-htb']]
    Format of queues:
    [[[u'uuid', u'69f2dedc-cee9-44d3-80bb-f36f67b5f2ea'], [u'set', []], [u'map', []], [u'map', [[u'max-rate', u'50000000'], [u'min-rate', u'10000000']]]], [[u'uuid', u'c4584bf9-a616-4396-a1ef-b40a18527f61'], [u'set', []], [u'map', []], [u'map', [[u'max-rate', u'5000000'], [u'min-rate', u'1000000']]]], [[u'uuid', u'8462e645-6198-4964-984b-004136a5ed72'], [u'set', []], [u'map', []], [u'map', [[u'max-rate', u'10000000000'], [u'min-rate', u'100000000']]]], [[u'uuid', u'75f7025e-a3fd-4220-8a9f-bc24fe0715a5'], [u'set', []], [u'map', []], [u'map', [[u'max-rate', u'10000000000'], [u'min-rate', u'100000000']]]], [[u'uuid', u'ecfcb9ce-7f6d-4e29-9361-4faec1ac45bf'], [u'set', []], [u'map', []], [u'map', [[u'max-rate', u'60000000'], [u'min-rate', u'10000000']]]], [[u'uuid', u'ed87baa7-1f20-43fa-96d3-8347592153f5'], [u'set', []], [u'map', []], [u'map', [[u'max-rate', u'6000000'], [u'min-rate', u'1000000']]]]]
    """
    def get_qos_queue(self, qos_id, queues, hypervisor_qos):
        qos = {'queues': []}


        for qoi in hypervisor_qos:
            match = 0
            if type(qoi) == unicode:
                qos['type'] = qoi
            else:
                for li in qoi:
                    if li[1] == qos_id:
                        match = 1
                        if li[0] == 'uuid':
                            qos['qos_uuid'] = li[1]
                    elif match:
                        match = 0
                        for item_inner in li:
                            if type(item_inner) == list:
                                for queue in item_inner:
                                    queue_info = {}
                                    logging.info("queue1 %s", list(enumerate(queue[1])))
                                    for queue_inner in queue[1]:
                                        if queue_inner != 'uuid':
                                            logging.info("queue_inner %s", list(enumerate(queue_inner)))
                                            #queue_info['qos_uuid'] = queue_inner
                                            for qui in queues:
                                                if qui[0][0] == 'uuid':
                                                    if qui[0][1] == queue_inner:
                                                        logging.info('Get Queue Rates %s', qui)
                                                        queue_info = self.get_queue_rates(qui)
                                                        queue_info['id'] = queue[0]
                                                        qos['queues'].append(queue_info)

        logging.info('Getting OVS queue for QoS ID %s: %s', qos_id, qos)
        return qos

    @staticmethod
    def get_server_hypervisor_info(servers, hostname):
        server_match = []
        for server in servers.values():
            if server['OS-EXT-SRV-ATTR:hypervisor_hostname'] == hostname:
                server_match.append(server['id'])
        logging.info('Getting servers for matching hypervisor %s: %s', hostname, server_match)
        return server_match

    """
    Get queue rates of output:
    [u'uuid', u'ed87baa7-1f20-43fa-96d3-8347592153f5'], [u'set', []], [u'map', []], [u'map', [[u'max-rate', u'6000000'], [u'min-rate', u'1000000']]]]
    """

    @staticmethod
    def get_queue_rates(queue):
        queue_rates = {}

        for item in queue:
            for li in item:
                if item[0] == 'uuid':
                    queue_rates['queue_uuid'] = item[1]
                if li == 'map':
                    for item_inner in item:
                        if type(item_inner) == list and len(item_inner) > 0:
                            for rate_inner in item_inner:
                                if rate_inner[0] == 'max-rate':
                                    queue_rates['rates'] = {}
                                    queue_rates['rates']['max-rate'] = rate_inner[1]
                                if rate_inner[0] == 'min-rate':
                                    queue_rates['rates']['min-rate'] = rate_inner[1]
        logging.info('Queue port rates: %s', queue_rates)
        return queue_rates

    @staticmethod
    def get_server_ip(server):
        ips = []
        if hasattr(server, 'addresses'):
            for interface in server.addresses.values():
                ips.append(interface[0]['addr'])
        return ips

    @staticmethod
    def get_port_id(interfaces, server_port):
        end = re.search(server_port, interfaces).start()
        start = end - 75
        ovs_port = re.findall("(qvo.*?[^\'])\"", interfaces[start:end])
        logging.info('Getting OVS port: %s, for Neutron Port ID: %s', ovs_port, server_port)
        return ovs_port

    @staticmethod
    def get_ovs_port_num(port_desc, ovs_port_id):
        port_ar = []

        end = port_desc.find(ovs_port_id)
        count = end
        if end != -1:
            while port_desc[count] != " ":
                count -= 1
            else:
                for el in range(count+1, end-1):
                    port_ar.append(port_desc[el])
        else:
            return "-1"
        port_number = ''.join(port_ar)
        logging.info('Port Number is: %s, for OVS Port ID: %s', port_number, ovs_port_id)
        return port_number

    def get_ips(self,server_string):

        ips = server_string['addresses']
        result = []
        for addr in ips.values():
            for private in addr:
                if private['OS-EXT-IPS:type'] == "fixed":
                    result.append(private['addr'])

        return result

    def get_new_server(self,hypervisor_id,server_name):
        servers = self.read_server_info()
        target_server = {}

        for server in servers.values():

            if server['OS-EXT-SRV-ATTR:hypervisor_hostname'] == hypervisor_id and server['name'] == server_name:

                target_server['id'] = server.get('id')
                target_server['name'] = server.get('name')
                target_server['interfaces'] = []

                server_ips = self.get_ips(server)

                for ip in server_ips:
                    interface = {}
                    interface['ip'] = ip
                    neutron_port = self.get_neutron_port(ip)
                    hypervisors = self.read_hypervisor_info()
                    host = Host(hypervisor_id)
                    hypervisor_ip = self.get_hypervisor_ip(hypervisor_id)
                    hypervisor_interfaces = host.list_interfaces_hypervisor(hypervisors)
                    ovs_port_id = self.get_port_id(hypervisor_interfaces,neutron_port)[0]
                    port_desc = host.list_port_desc_hypervisor(hypervisor_ip)
                    interface['ovs_port_number'] = self.get_ovs_port_num(port_desc,ovs_port_id)
                    qos_id = host.get_port_qos(hypervisor_ip,ovs_port_id)
                    queues = host.list_queues_hypervisor(hypervisor_ip)
                    qoss = host.list_qos_hypervisor(hypervisor_ip)
                    interface['qos'] = self.get_qos_queue(qos_id,queues,qoss)
                    target_server['interfaces'].append(interface)

        return target_server


class Host(object):
    def __init__(self, hypervisor):
        self.hypervisor = hypervisor
        self.ovsclient = OVSClient()
        self.cloud = Cloud()

    def list_interfaces_hypervisor(self, hypervisors):
        interfaces = {}
        for k, v in hypervisors.items():
            if k == self.hypervisor:
                for k_inner, v_inner in v.items():
                    if k_inner == 'ip':
                        ip = v_inner
                        interfaces = self.ovsclient.list_interfaces(ip)
        logging.info('Getting OVS interfaces %s :', interfaces)
        return interfaces

    """
    Format:
    {"data":[["em1",["set",[]],["set",[]]],["vxlan-c0a8292c",["set",[]],["set",[]]],["tapab31b81d-9f",["set",[]],1],["br-int",["set",[]],["set",[]]],["br-ex",["set",[]],["set",[]]],["br-tun",["set",[]],["set",[]]],["patch-tun",["set",[]],["set",[]]],["patch-int",["set",[]],["set",[]]],["qg-f2e6bee1-e7",["set",[]],["set",[]]],["qr-23d740b1-74",["set",[]],1],["qvob3f1896b-c8",["uuid","f807a246-4064-4577-806e-76dfe623dda0"],1],["qvo365ba3c3-14",["uuid","9cd461b3-f9b6-49b9-bac4-c71c19d1d2d0"],1]],"headings":["name","qos","tag"]}
    """
    def list_ports_hypervisor(self, hypervisor_ip):
        ports = self.ovsclient.list_ports(hypervisor_ip)
        logging.info('Getting OVS ports: %s for Hypervisor IP: %s', ports, hypervisor_ip)
        return ports

    def list_qos_hypervisor(self, hypervisor_ip):
        qos_raw = json.loads(self.ovsclient.list_qoss(hypervisor_ip))
        hypervisor_qos = []

        for q in qos_raw.get('data'):
            hypervisor_qos.append(q)

        logging.info('Getting final OVS QoS %s for IP %s', hypervisor_qos, hypervisor_ip)
        return hypervisor_qos

    def list_port_desc_hypervisor(self, hypervisor_ip):
        port_desc_raw = self.ovsclient.list_port_desc(hypervisor_ip)
        logging.info('Getting final Port Desc %s for IP %s', port_desc_raw, hypervisor_ip)
        return port_desc_raw

    def list_queues_hypervisor(self, hypervisor_ip):
        queues = []
        queues_raw = json.loads(self.ovsclient.list_queues(hypervisor_ip))
        logging.info('Queues for comparison for %s : %s ... ', hypervisor_ip, queues_raw)

        for q in queues_raw.get('data'):
            queues.append(q)
        logging.info('Queues from queue list: %s', queues)
        return queues

    def get_port_qos(self, hypervisor_ip, ovs_port):
        ports_raw = json.loads(self.list_ports_hypervisor(hypervisor_ip))
        logging.info('Ports for %s: %s', hypervisor_ip, ports_raw)
        qos_id = []
        for port in ports_raw.get('data'):
            isvm = 0
            for port_key in port:
                if type(port_key) == unicode and port_key == ovs_port:
                    isvm = 1
                if type(port_key) == list and isvm:
                    isvm = 0
                    for pv in port_key:
                        if pv != 'uuid':
                            qos_id = pv
        logging.info('QoS ID for port: %s is: %s', ovs_port, qos_id)
        return qos_id

    def set_qos_vm(self, server_interface, interfaces, vm_id):
        qos_status = {}
        queues = {}
        queue_string = "queues="
        found_match = 0
        queue_cfgs = ""
        server_ips = self.cloud.get_server_ips()
        hypervisor_ip = self.cloud.get_hypervisor_ip(self.hypervisor)

        for ks, vs in server_ips.items():
            if ks == vm_id:
                for ip in vs:
                    if ip == server_interface.get('ip'):
                        found_match = 1
                        neutron_port = self.cloud.get_neutron_port(ip)
                        ovs_port_id = self.cloud.get_port_id(interfaces, neutron_port)[0]
                        logging.info('OVS port ID for Server %s: %s', ks, ovs_port_id)
                        qos_tmp = server_interface.get('qos')
                        for rate in qos_tmp.get('queues'):
                            internal_rate = rate.get('rates')
                            logging.info('Server %s gets Min-rate %s Max-rate %s', ks, rate.get('min-rate'), rate.get('max-rate'))
                            #queues[index] = self.ovsclient.create_queue(hypervisor_ip, int(qos_rate.get('min-rate')), int(qos_rate.get('max-rate')))
                            queue_cfgs += "-- --id=@q" + rate.get('id') + " create queue other-config:min-rate=" + internal_rate.get('min-rate') +\
                                          " other-config:max-rate=" + internal_rate.get('max-rate') + " "
                            queues[rate.get('id')] = "q"+ rate.get('id')
                            logging.info('Queue ID for Server %s: %s', ks, queue_cfgs)
                        for idx, qid in queues.items():
                            queue_string += "%s=@" %idx + "%s," % qid

                        logging.info('Queue String for server %s: %s%s', ks, queue_string, queue_cfgs)
                        return_ids = self.ovsclient.create_qos(hypervisor_ip, queue_string, queue_cfgs)
                        logging.info('QoS ID %s', return_ids.split('\n'))
                        qos_id = return_ids.split('\n')
                        qos_status = self.ovsclient.set_port(hypervisor_ip, ovs_port_id, 'qos', qos_id[0])

                        qos_tmp['qos_uuid'] = qos_id[0]

                        # logging.debug("Current qoses_ids %s",qos_id)

                        for num_id,ids in enumerate(qos_id):
                            for rate in qos_tmp.get('queues'):
                                if int(rate.get('id')) == num_id:
                                    rate['queue_uuid'] = ids

                        server_interface['qos'] = qos_tmp


                        if not qos_status:
                            qos_status = server_interface
                        logging.info('QoS status for Server %s: %s', ks, qos_status)
        if not found_match:
            return qos_status
        else:
            return qos_status

    def dell_qos(self,qos_id):
        hypervisor_ip = self.cloud.get_hypervisor_ip(self.hypervisor)
        resp = {}
        resp['queues'] = []
        queues = self.get_queues(qos_id)
        logging.debug("Queues found: %s",queues)

        logging.info('OVS destroy all queue on : %s and deleteting qos %s',hypervisor_ip,qos_id)

        if queues:
            for current_queue in queues:
                queue_del = {}
                queue_del['status'] = self.del_queue(current_queue.get('number'),current_queue.get('id'),qos_id)
                queue_del['number'] = current_queue.get('number')

                resp['queues'].append(queue_del)

        qos_del = self.ovsclient.del_qos(hypervisor_ip,qos_id)

        resp['qos_id'] = qos_id
        if qos_del == None:
            resp['status'] = "success"
        else:
            resp['status'] = qos_del

        return resp


    def get_queues(self,qos_id):
        hypervisor_ip = self.cloud.get_hypervisor_ip(self.hypervisor)
        queue_json = self.ovsclient.list_qosandqueue(hypervisor_ip,qos_id)
        queues = json.loads(queue_json)
        logging.debug("Queues %s", queues)
        val = []

        for item in queues.get('data'):
            logging.debug("Item %s", item)
            for inner in item:
                logging.debug("Inner %s", inner)
                if type(inner) == list:
                    for li in inner:
                        logging.debug("Li %s",li)
                        if type(li) == list:
                            if not li:
                                return val

                            if len(li) > 1:
                                for lu in li:
                                    queue = {}
                                    logging.debug("LU[0] %s",lu[0])
                                    queue['number'] = lu[0]
                                    logging.debug("LU[1] %s",lu[1][1])
                                    queue['id'] = lu[1][1]
                                    val.append(queue)
                            else:
                                single_queue = {}
                                logging.debug("Li[0] %s",li[0])
                                single_queue['number'] = li[0][0]
                                logging.debug("Li[0][1][1] %s",li[0][1][1])
                                single_queue['id'] = li[0][1][1]
                                val.append(single_queue)
        return val


    def del_queue(self,queue_number,queue_id,qos_id):
        logging.info('OVS destroy queue number %s with id %s',queue_number,queue_id)
        hypervisor_ip = self.cloud.get_hypervisor_ip(self.hypervisor)
        ret = {}
        val = self.ovsclient.del_queue(hypervisor_ip,qos_id,queue_id,queue_number)

        # queues = self.get_queues(qos_id)
        # ret['qos_uuid'] = qos_id
        # ret['queues'] = []
        #
        # for queue in queues:
        #     ret_queue = {}
        #     ret_queue['queue_uuid'] = queue.get('id')
        #     ret_queue['id'] = queue.get('number')
        #     ret_queue['rates'] = self.get_queue_rates(queue.get('id'))
        #     ret['queues'].append(ret_queue)

        ret['queue_uuid'] = queue_id
        ret['queue_id'] = queue_number
        ret['qos_uuid'] = qos_id

        if val is 0:
            ret['status'] = 'success'
        else:
            ret['status'] = val

        return ret

    def set_flow_vm(self, flow_config):
        flow_status = []


        logging.info('Flow config %s',flow_config)

        for qv in flow_config:

            current_flow = {}
            logging.info('Setting flow on Queue: ip %s', qv.get("src_ipv4"))
            hypervisor_ip = self.cloud.get_hypervisor_ip(qv.get("dest_hyp"))
            current_flow = self.ovsclient.add_flow_to_queue(hypervisor_ip, qv.get('src_ipv4'),qv.get("dest_ipv4"), qv.get("protocol"),
                                                           qv.get('priority'), qv.get('ovs_port_number'), qv.get("queue_number"))

            flow_status.append(current_flow)

        return flow_status

    def remove_flow(self,ip,protocol):

        result = {}
        hypervisor_ip = self.cloud.get_hypervisor_ip(self.hypervisor)
        logging.debug("REMOVE FLOW hypervisor ip %s",hypervisor_ip)
        self.ovsclient.remove_flow_dest(hypervisor_ip,ip,protocol)

        current_flows = self.ovsclient.dump_flows()
        logging.debug("REMOVE FLOW current flows %s", current_flows)
        if ("nw_dst=" + ip in current_flows) == True:
            result = "failed"
        else:
            self.ovsclient.remove_flow_src(hypervisor_ip,ip,protocol)
            current_flows = self.ovsclient.dump_flows()
            if ("nw_src=" + ip in current_flows) == True:
                result = "failed"
            else:
                result = "success"

        return result

    def create_queue(self,min_rate,max_rate):
        hypervisor_ip = self.cloud.get_hypervisor_ip(self.hypervisor)
        queue_id = self.ovsclient.create_queue(hypervisor_ip,min_rate,max_rate)
        return queue_id

    def link_queue_to_qos(self,qos_id,queue_id,queue_number):
        hypervisor_ip = self.cloud.get_hypervisor_ip(self.hypervisor)

        ret = self.ovsclient.set_qos_ovs(hypervisor_ip,qos_id,queue_id,queue_number)
        return ret

        # def get_queue_rates(self,queue_id):
    #     hypervisor_ip = self.cloud.get_hypervisor_ip(self.hypervisor)
    #     queues = self.ovsclient.list_queue(hypervisor_ip,queue_id)
    #     ret = json.loads(queues)
    #
    #     rates = {}
    #     for inner in ret.get('data'):
    #         if type(inner) == list:
    #             for li in inner:
    #                 if type(li) == list:
    #                     for lu in li[1]:
    #                         rates[lu[0]] = lu[1]
    #
    #     return rates
