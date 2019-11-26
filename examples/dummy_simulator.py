import paho.mqtt.client as mqtt
import time
import os
import argparse


def connect(client_name, username, password, broker_adress, port=1883):
    mqttc = mqtt.Client(client_name, True)
    mqttc.username_pw_set(username, password)
    mqttc.on_connect = on_connect  # attach function to callback
    # mqttc.on_message = on_message					#attach function to callback
    mqttc.connect(broker_adress, port)  # connect to broker
    mqttc.loop_start()  # start loop to process callback
    time.sleep(4)  # wait for connection setup to complete

    return mqttc


def on_connect(client, userdata, flags, rc):
    """
    The callback for when the client receives a CONNACK response from the server.
    """
    if rc == 0:
        print("connected OK with returned code=", rc)
    else:
        print("Bad connection with returned code=", rc)


# argument parsing
parser = argparse.ArgumentParser()
parser.add_argument("-q", "--quiet", action="store_true", help="switch off output")
args = parser.parse_args()

# parameters
sequence = 1
len_data = 300
client_name = "DpsimDummy"

# # Public Message Broker
# broker_address = "m16.cloudmqtt.com"
# mqtt_username = "ilgtdaqk"
# mqtt_password = "UbNQQjmcUdqq"
# port = 14543
# topic_publish = "dpsim-powerflow"


# # ACS Message Broker
# broker_address = "platform-broker"
# mqtt_username = "sogno_user"
# mqtt_password = "sogno_pass"
# port = 1883
# topic_publish = "dpsim-powerflow"

# Message Broker according to environment variables
broker_address = os.environ['HOSTNAME_BROKER']
mqtt_username = os.environ['MQTT_USER']
mqtt_password = os.environ['MQTT_PASS']
port = int(os.environ['MQTT_PORT'])
topic_publish = os.environ['PUBLISH_TOPIC']

os.chdir(os.path.dirname(__file__))
print(os.getcwd())

mqttc = connect(client_name, mqtt_username, mqtt_password, broker_address, port)

data_file = r"./sample_data/dpsim_powerflow_record_cigre.txt"
data = []
with open(data_file) as json_file:
    for line in json_file:
        data.append(line)

while sequence < len_data + 1:
    mqttc.publish(topic_publish, data[sequence])
    if not args.quiet:
        print("Sent data for sequence " + str(sequence) + ": " + data[sequence])
    sequence += 1
    time.sleep(1)

mqttc.loop_stop()  # Stop loop
mqttc.disconnect()  # disconnect
