""" """
from shakedown import *
from utils import *
from dcos.errors import DCOSException
import uuid
import random

def app(id=1, instances=1):
    app_json = {
      "id": "",
      "instances":  1,
      "cmd": "sleep 100000000",
      "cpus": 0.01,
      "mem": 1,
      "disk": 0
    }
    if not str(id).startswith("/"):
        id = "/" + str(id)
    app_json['id'] = id
    app_json['instances'] = instances

    return app_json


def app_mesos(app_id=None):
    if app_id is None:
        app_id = uuid.uuid4().hex

    return {
        'id': app_id,
        'cmd': 'sleep 1000',
        'cpus': 0.5,
        'mem': 32.0,
        'container': {
            'type': 'MESOS'
        }
    }


def constraints(name, operator, value=None):
    constraints = [name, operator]
    if value is not None:
        constraints.append(value)
    return [constraints]


def unique_host_constraint():
    return constraints('hostname', 'UNIQUE')


def group():

    return {
        "apps": [],
        "dependencies": [],
        "groups": [
            {
                "apps": [
                    {
                        "cmd": "sleep 1000",
                        "cpus": 1.0,
                        "dependencies": [],
                        "disk": 0.0,
                        "id": "/test-group/sleep/goodnight",
                        "instances": 1,
                        "mem": 128.0
                    },
                    {
                        "cmd": "sleep 1000",
                        "cpus": 1.0,
                        "dependencies": [],
                        "disk": 0.0,
                        "id": "/test-group/sleep/goodnight2",
                        "instances": 1,
                        "mem": 128.0
                    }
                ],
                "dependencies": [],
                "groups": [],
                "id": "/test-group/sleep",
            }
        ],
        "id": "/test-group"
    }


def python_http_app():
    return {
        'id': 'python-http',
        'cmd': '/opt/mesosphere/bin/python -m http.server $PORT0',
        'cpus': 1,
        'mem': 128,
        'disk': 0,
        'instances': 1
        }


def fake_framework_app():
    return {
        "id": "/python-http",
        "cmd": "/opt/mesosphere/bin/python -m http.server $PORT0",
        "cpus": 1,
        "mem": 128,
        "disk": 0,
        "instances": 1,
        "readinessChecks": [
        {
            "name": "readiness",
            "protocol": "HTTP",
            "path": "/",
 		    "portName": "api",
            "interval": 2,
            "timeout": 1,
            "httpStatusCodesForReady": [200]
        }],
        "healthChecks": [
        {
            "gracePeriodSeconds": 10,
            "intervalSeconds": 2,
            "maxConsecutiveFailures": 0,
            "path": "/",
            "portIndex": 0,
            "protocol": "HTTP",
            "timeoutSeconds": 2
        }],
        "labels": {
            "DCOS_PACKAGE_FRAMEWORK_NAME": "pyfw",
            "DCOS_MIGRATION_API_VERSION": "v1",
            "DCOS_MIGRATION_API_PATH": "/v1/plan",
            "MARATHON_SINGLE_INSTANCE_APP": "true",
            "DCOS_SERVICE_NAME": "pyfw",
            "DCOS_SERVICE_PORT_INDEX": "0",
            "DCOS_SERVICE_SCHEME": "http"
        },
        "upgradeStrategy": {
            "minimumHealthCapacity": 0,
            "maximumOverCapacity": 0
        },
        "portDefinitions": [
        {
            "protocol": "tcp",
            "port": 0,
	        "name": "api"
        }]
    }


def pending_deployment_due_to_resource_roles(app_id):
    resource_role = str(random.getrandbits(32))

    return {
      "id": app_id,
      "cpus": 0.001,
      "instances": 1,
      "mem": 32,
      "cmd": "sleep 12345",
      "acceptedResourceRoles": [
        resource_role
      ]
    }


def pending_deployment_due_to_cpu_requirement(app_id):
    return {
      "id": app_id,
      "instances": 1,
      "mem": 128,
      "cpus": 65536,
      "cmd": "sleep 12345"
    }


def pin_to_host(app_def, host):
    app_def['constraints'] = constraints('hostname', 'LIKE', host)


def health_check(path='/', port_index=0, failures=1, timeout=2):

    return {
          'protocol': 'HTTP',
          'path': path,
          'timeoutSeconds': timeout,
          'intervalSeconds': 2,
          'maxConsecutiveFailures': failures,
          'portIndex': port_index
        }


def cluster_info(mom_name='marathon-user'):
    agents = get_private_agents()
    print("agents: {}".format(len(agents)))
    client = marathon.create_client()
    about = client.get_about()
    print("marathon version: {}".format(about.get("version")))
    # see if there is a MoM
    with marathon_on_marathon(mom_name):
        try:
            client = marathon.create_client()
            about = client.get_about()
            print("marathon MoM version: {}".format(about.get("version")))

        except Exception as e:
            print("Marathon MoM not present")


def delete_all_apps():
    client = marathon.create_client()
    apps = client.get_apps()
    for app in apps:
        if app['id'] == '/marathon-user':
            print('WARNING: marathon-user installed')
        else:
            client.remove_app(app['id'], True)


def stop_all_deployments():
    client = marathon.create_client()
    deployments = client.get_deployments()
    for deployment in deployments:
        client.stop_deployment(deployment['id'])

def delete_all_apps_wait():
    delete_all_apps()
    deployment_wait()


def ip_other_than_mom():
    mom_ip = ip_of_mom()

    agents = get_private_agents()
    for agent in agents:
        if agent != mom_ip:
            return agent

    return None


def ip_of_mom():
    service_ips = get_service_ips('marathon', 'marathon-user')
    for mom_ip in service_ips:
        return mom_ip


def ensure_mom():
    if not is_mom_installed():

        try:
            install_package_and_wait('marathon')
            deployment_wait()
        except:
            pass

        if not wait_for_service_endpoint('marathon-user'):
            print('ERROR: Timeout waiting for endpoint')


def is_mom_installed():
    return package_installed('marathon')


def restart_master_node():
    """ Restarts the master node
    """

    run_command_on_master("sudo /sbin/shutdown -r now")


def systemctl_master(command='restart'):
        run_command_on_master('sudo systemctl {} dcos-mesos-master'.format(command))


def save_iptables(host):
    run_command_on_agent(host, 'if [ ! -e iptables.rules ] ; then sudo iptables -L > /dev/null && sudo iptables-save > iptables.rules ; fi')


def restore_iptables(host):
    run_command_on_agent(host, 'if [ -e iptables.rules ]; then sudo iptables-restore < iptables.rules && rm iptables.rules ; fi')


def block_port(host, port, direction='INPUT'):
    run_command_on_agent(host, 'sudo iptables -I {} -p tcp --dport {} -j DROP'.format(direction, port))


def wait_for_task(service, task, timeout_sec=120):
    """Waits for a task which was launched to be launched"""

    now = time.time()
    future = now + timeout_sec

    while now < future:
        response = None
        try:
            response = get_service_task(service, task)
        except Exception as e:
            pass

        if response is not None and response['state'] == 'TASK_RUNNING':
            return response
        else:
            time.sleep(5)
            now = time.time()

    return None


def get_pod_tasks(pod_id):
    pod_tasks = []
    tasks = get_marathon_tasks()
    for task in tasks:
        if task['labels'][0]['value'] == pod_id:
            pod_tasks.append(task)

    return pod_tasks
