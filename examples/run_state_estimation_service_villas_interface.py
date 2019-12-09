import time
import logging
import paho.mqtt.client as mqtt
import traceback
from json import loads

import cimpy
from acs.state_estimation.network import System
from acs.state_estimation.nv_state_estimator import DsseCall
from acs.state_estimation.measurement import MeasurementSet

import sys
import os
from os import chdir, getcwd
from os.path import abspath, dirname, join

chdir(dirname(__file__))

sys.path.append("..")
from interfaces import villas_node_interface

logging.basicConfig(filename='recv_client.log', level=logging.INFO, filemode='w')

def connect(client_name, username, password, broker_adress, port=1883):
    mqttc = mqtt.Client(client_name, True)
    mqttc.username_pw_set(username, password)
    mqttc.on_connect = on_connect  # attach function to callback
    mqttc.on_message = on_message  # attach function to callback
    mqttc.connect(broker_adress, port)  # connect to broker
    mqttc.loop_forever()  # start loop to process callback
    time.sleep(4)  # wait for connection setup to complete

    return mqttc


def on_connect(client, userdata, flags, rc):
    """
    The callback for when the client receives a CONNACK response from the server.
    """
    if rc == 0:
        client.subscribe(topic_subscribe)
        print("connected OK with returned code=", rc)
    else:
        print("Bad connection with returned code=", rc)


def on_message(client, userdata, msg):
    """
    The callback for when a PUBLISH message is received from the server
    """
    global sequence

    sequence += 1

    message = loads(msg.payload)[0]    

    if sequence > 0:
        try:
            # store the received data in powerflow_results
            powerflow_results = villas_node_interface.receiveVillasNodeInput(system, message, input_mapping_vector)

            # read measurements from file
            measurements_set = MeasurementSet()

            if sequence < 90:
                measurements_set.read_measurements_from_file(powerflow_results, meas_configfile1)
                scenario_flag = 1
            else:
                measurements_set.read_measurements_from_file(powerflow_results, meas_configfile2)
                scenario_flag = 2

            # calculate the measured values (affected by uncertainty)
            measurements_set.meas_creation(dist="uniform", seed=sequence)
            # Performs state estimation
            state_estimation_results = DsseCall(system, measurements_set)

            # send results to message broker
            villasOutput = villas_node_interface.sendVillasNodeOutput(message, output_mapping_vector, powerflow_results,
                                                                      state_estimation_results, scenario_flag)
            client.publish(topic_publish, villasOutput, 0)

            # Finished message
            print("Finished state estimation for sequence " + str(sequence))

        except Exception as e:
            print(e)
            traceback.print_tb(e.__traceback__)
            sys.exit()


cwd = getcwd()

# grid files
xml_files = [
    abspath(join(cwd, r"../state-estimation/examples/quickstart/sample_data/Rootnet_FULL_NE_06J16h_EQ.xml")),
    abspath(join(cwd, r"../state-estimation/examples/quickstart/sample_data/Rootnet_FULL_NE_06J16h_SV.xml")),
    abspath(join(cwd, r"../state-estimation/examples/quickstart/sample_data/Rootnet_FULL_NE_06J16h_TP.xml"))]

# measurements files
meas_configfile1 = abspath(join(cwd, r"./configs/Measurement_config2.json"))
meas_configfile2 = abspath(join(cwd, r"./configs/Measurement_config3.json"))

# read mapping file and create mapping vectors
input_mapping_file = abspath(join(cwd, r"./configs/villas_node_input_data.conf"))
output_mapping_file = abspath(join(cwd, r"./configs/villas_node_output_data.conf"))
input_mapping_vector = villas_node_interface.read_mapping_file(input_mapping_file)
output_mapping_vector = villas_node_interface.read_mapping_file(output_mapping_file)

# load grid
Sb = 25
res = cimpy.cimread(xml_files)
system = System()
system.load_cim_data(res, Sb)

client_name = "StateEstimationService"

"""
# Public Message Broker
broker_address = "m16.cloudmqtt.com"
mqtt_username = "ilgtdaqk"
mqtt_password = "UbNQQjmcUdqq"
port = 14543

# ACS Message Broker
broker_address = "137.226.248.91"
mqtt_username = "villas"
mqtt_password = "s3c0sim4!"
port = 1883

# Local SOGNO platform broker
broker_address = "127.0.0.1"
mqtt_username = "sogno_user"
mqtt_password = "sogno_pass"
port = 1883
"""

# Message Broker according to environment variables
broker_address = os.environ['HOSTNAME_BROKER']
mqtt_username = os.environ['MQTT_USER']
mqtt_password = os.environ['MQTT_PASS']
port = int(os.environ['MQTT_PORT'])
topic_subscribe = os.environ['SUBSCRIBE_TOPIC']
topic_publish = os.environ['PUBLISH_TOPIC']

sequence = -1

mqttc = connect(client_name, mqtt_username, mqtt_password, broker_address, port)

#input("Press enter to stop client...\n")
#mqttc.loop_stop()  # Stop loop
#mqttc.disconnect()  # disconnect

#mqttc.loop_forever(retry_first_connection=False)

#mqttc.loop_start()

