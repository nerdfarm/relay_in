# pylint: disable=import-error,invalid-name,bare-except,unused-argument,no-self-use
""" Python ZNC module for passing mosquitto mq messages to ZNC """

import re
import multiprocessing

import znc
import paho.mqtt.client as mqtt


def _contains_required_args(args, required_args):
    """ Validates the arg string from ZNC contains required arg keys """
    return len([x for x in required_args if x in args]) == len(required_args)


def _parse_args(args, required_args):
    """ Parse args according to required args """
    module_args = {}
    split_args = []
    for index, token in enumerate([x for x in re.split("=|--", args.strip()) if x.strip()]):
        if token:
            if index % 2 == 0:
                split_args.append("--" + token.strip())
            else:
                split_args.append(token.strip())
    for arg in required_args:
        index = split_args.index(arg)
        if index > -1:
            value = split_args[index + 1]
            if value and value not in required_args:
                module_args[arg] = value.strip()
    return module_args


def _is_valid_module_args(parsed_args, required_args):
    """ Validate that parsed args have required args, and no values are None or empty strings """
    return len([x for x in required_args if x not in parsed_args.keys()]) == 0 and \
           len([x for x in parsed_args.values() if not x]) == 0


class relay_in(znc.Module):
    """ ZNC module with a mosquitto MQ running in a background process """

    description = "Relay messages into IRC from obs"
    module_types = [znc.CModInfo.UserModule]

    _PARAM_KEYS = {
        "_TOPIC_KEY": "--topic",
        "_HOST_KEY": "--host",
        "_PORT_KEY": "--port",
        "_QOS_KEY": "--qos",
        "_CLIENT_ID_KEY": "--client-id",
        "_NETWORK_NAME_KEY": "--network-name",
        "_CHANNEL_KEY": "--channel"
    }

    def __init__(self):
        self._client = None
        self._client_process = None
        self._module_args = {}

    def OnLoad(self, args, message):
        """
        Initialize client with this callback to avoid module loading issues with incomplete initialization
        """
        try:
            message.s = str(message.s) + "\n"
            if not _contains_required_args(args, list(relay_in._PARAM_KEYS.values())):
                message.s = "Missing required args, found: {}, required: {}".format(
                    args, str(list(relay_in._PARAM_KEYS.values())))
                return False
            message.s = str(message.s) + "Passed required arg check\n"
            parsed_args = _parse_args(args, list(relay_in._PARAM_KEYS.values()))
            message.s = str(message.s) + "Parsed module args\n"
            if not _is_valid_module_args(parsed_args, list(relay_in._PARAM_KEYS.values())):
                message.s = "Invalid module args, found: {}, required: {}".format(
                    str(parsed_args), str(list(relay_in._PARAM_KEYS.values())))
                return False
            message.s = str(message.s) + "Passed module arg check\n"
            self._module_args = parsed_args
            message.s = str(message.s) + "Module args: " + str(self._module_args) + "\n"
            self._client = self._init_mqtt_client()
            message.s = str(message.s) + "Initialized mq client\n"
            self._client_process = multiprocessing.Process(target=self._client.loop_forever)
            self._client_process.start()
            message.s = str(message.s) + "Started mq client\n"
            return True
        except Exception as exception:
            # Catch all to ensure any exception will prevent the module from loading
            message.s = str(message.s) + "Failed to load module: \n" + str(exception)
            return False

    def OnModCommand(self, command):
        """ No commands yet """
        return znc.CONTINUE

    def _init_mqtt_client(self):
        """ Initialize, connect, and subscribe mosquitto client """
        client = mqtt.Client(client_id=self._get_param("_CLIENT_ID_KEY"), clean_session=False)
        client.on_message = self._on_message
        client.connect(self._get_param("_HOST_KEY"), port=int(self._get_param("_PORT_KEY")))
        client.subscribe(topic=self._get_param("_TOPIC_KEY"), qos=int(self._get_param("_QOS_KEY")))
        return client

    def _on_message(self, client, user_data, msg):
        """ mosquitto client callback for incoming mq messages """
        network = self.GetUser().FindNetwork(self._get_param("_NETWORK_NAME_KEY"))
        if network:
            message = str(msg.payload.decode(encoding='utf-8', errors='ignore'))
            network.GetIRCSock().Write("PRIVMSG {} :{}\r\n".format(self._get_param("_CHANNEL_KEY"), message))

    def GetWebMenuTitle(self):
        """ Title for web UI """
        return "relay_in mosquitto mq to IRC"

    def OnShutdown(self):
        """ Tear down the module """
        try:
            if self._client:
                self._client.unsubscribe(self._get_param("_TOPIC_KEY"))
                self._client.disconnect()
            if self._client_process:
                self._client_process.terminate()
        except:
            # Catch all to ensure this module gets unloaded, regardless of exception states
            return znc.CONTINUE

    def _get_param(self, key):
        """ Helper to get a module parameter """
        return self._module_args[relay_in._PARAM_KEYS[key]]
