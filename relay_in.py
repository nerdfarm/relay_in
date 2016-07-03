# pylint: disable=import-error,invalid-name,bare-except,unused-argument,no-self-use
""" Python ZNC module for passing mosquitto mq messages to ZNC """

import multiprocessing

import znc
import paho.mqtt.client as mqtt


class relay_in(znc.Module):
    """ ZNC module with a mosquitto MQ running in a background process """

    description = "Relay messages into IRC from obs"
    module_types = [znc.CModInfo.UserModule]

    TOPIC = "a_topic"
    HOST = "localhost"
    PORT = 1883
    QOS = 2
    CLIENT_ID = "client_id"
    NETWORK_NAME = "network_name"
    CHANNEL = "channel"

    def __init__(self):
        self._client = None
        self._client_process = None
        self._irc_process = None

    def OnLoad(self, args, message):
        """
        Initialize client with this callback to avoid module loading issues with incomplete initialization
        """
        try:
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
        client = mqtt.Client(client_id=relay_in.CLIENT_ID, clean_session=False)
        client.on_message = self._on_message
        client.connect(relay_in.HOST, port=relay_in.PORT)
        client.subscribe(topic=relay_in.TOPIC, qos=relay_in.QOS)
        return client

    def _on_message(self, client, user_data, msg):
        """ mosquitto client callback for incoming mq messages """
        network = self.GetUser().FindNetwork(relay_in.NETWORK_NAME)
        if network:
            message = str(msg.payload.decode(encoding='utf-8', errors='ignore'))
            network.GetIRCSock().Write("PRIVMSG {} :{}\r\n".format(relay_in.CHANNEL, message))

    def GetWebMenuTitle(self):
        """ Title for web UI """
        return "mosquitto mq to IRC"

    def OnShutdown(self):
        """ Tear down the module """
        try:
            if self._client:
                self._client.unsubscribe(relay_in.TOPIC)
                self._client.disconnect()
            if self._client_process:
                self._client_process.terminate()
        except:
            # Catch all to ensure this module gets unloaded, regardless of exception states
            return znc.CONTINUE

