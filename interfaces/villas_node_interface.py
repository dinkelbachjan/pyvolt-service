from json import dumps, loads
from datetime import datetime

import numpy as np
from acs.state_estimation.results import Results


def read_mapping_file(mapping_file):
    """
    Create a list which contains the order in which the data must be received/sent from/to VillasNode.
    This mapping is readed from the files villas_node_input_data/villas_node_output_data

    @param mapping_file: received message  from the server (json.loads(msg.payload)[0])
    @return mapping:
        - if input is villas_node_input_data  --> each element of mapping is a list of length 3: [id, "V", "mag" or "phase"]
        - if input is villas_node_output_data --> each element of mapping is a list of length 4: [id, "V", "mag" or "phase", "pf" or "est"]
        * if id = "max_err" or "mean_err" or "scenario_flag" --> this element has the length 1: ["max_err" or "mean_err" or "scenario_flag"]
    """
    lines = []
    with open(mapping_file) as mfile:
        for line in mfile:
            lines.append(line.strip('\n'))
    mapping = [None] * len(lines)
    for pos, elem in enumerate(lines):
        mapping[pos] = elem.split(".")

    return mapping


def receiveVillasNodeInput(system, message, input_mapping_vector):
    """
    to store the received data in an object of type acs.state_estimation.results.Results

    @system: model of the system (type acs.state_estimation.network.System)
    @param message: received message from the server (json.loads(msg.payload)[0])
    @param input_mapping_vector: according to villas_node_input.json (see function read_mapping_file)
    @return powerflow_results: object type acs.state_estimation.results.Results
    """

    data = message['data']

    # create a results object to store the received data
    powerflow_results = Results(system)

    # store the received data in powerflow_results
    for node in powerflow_results.nodes:
        magnitude = 0.0
        phase = 0.0
        uuid = node.topology_node.uuid
        for idx, elem in enumerate(input_mapping_vector):
            # print("elem[0]: {}, uuid: {}".format(elem[0], uuid))
            if elem[0] == uuid:
                if elem[2] == "mag":  # elem[1] = "mag" or "phase"
                    magnitude = data[idx]
                elif elem[2] == "phase":
                    phase = data[idx]
        node.voltage = magnitude * (np.cos(phase) + 1j * np.sin(phase)) / 1000
        node.voltage_pu = node.voltage / node.topology_node.baseVoltage

    # calculate quantities I, Iinj, S and Sinj
    powerflow_results.calculate_all()

    return powerflow_results


def sendVillasNodeOutput(message, output_mapping_vector, powerflow_results, state_estimation_results, scenario_flag):
    """
    to create the payload according to "villas_node_output.json"

    @param message: received message from the server (json.loads(msg.payload)[0])
    @param output_mapping_vector: according to villas_node_output.json (see function read_mapping_file)
    @param powerflow_results: results of powerflow (type acs.state_estimation.results.Results)
    @param state_estimation_results: results of state_estimation (type acs.state_estimation.results.Results)
    @param scenario_flag:
    @return: string formatted according to "villas_node_output.json"
    """
    VillasNodeOutput = {}
    VillasNodeOutput["ts"] = {}
    VillasNodeOutput["ts"]["origin"] = message["ts"]["origin"]

    # calculate Vmag_err
    Vmag_err = np.zeros(len(powerflow_results.nodes))
    for idx, elem in enumerate(powerflow_results.nodes):
        uuid_pf = elem.topology_node.uuid
        Vmag_true = np.absolute(elem.voltage)
        Vmag_est = np.absolute(state_estimation_results.get_node(uuid=uuid_pf).voltage)
        Vmag_err[idx] = np.absolute(Vmag_est - Vmag_true)
        Vmag_err[idx] = 100 * np.divide(Vmag_err[idx], Vmag_true)

    max_err = np.amax(Vmag_err)
    mean_err = np.mean(Vmag_err)

    data = [None] * len(output_mapping_vector)
    for idx, elem in enumerate(output_mapping_vector):
        if elem[0] == "max_err":
            data[idx] = max_err
            continue
        elif elem[0] == "mean_err":
            data[idx] = mean_err
            continue
        elif elem[0] == "scenario_flag":
            data[idx] = float(scenario_flag)
            continue
        else:  # elem = ["N4", "V", "phase", "est"] or elem = ["N4", "V", "phase", "pf"]
            node = None
            if elem[3] == "est":
                node = state_estimation_results.get_node(uuid=elem[0])
            elif elem[3] == "pf":
                node = powerflow_results.get_node(uuid=elem[0])

            value = None
            if elem[2] == "mag":  # elem_data[2] = "mag" or "phase"
                value = np.absolute(node.voltage)
            elif elem[2] == "phase":
                value = np.angle(node.voltage)
            data[idx] = value

    VillasNodeOutput["data"] = data
    return "[" + dumps(VillasNodeOutput) + "]"


def serviceCalculations():
    pass


def convertVillasNodeInputToSognoInput(VillasNodeInput, input_mapping_vector, version="1.0", type="se_result"):
    """
    @param VillasNode: received message formatted according to "villas_node_input.json"
    @param input_mapping_vector: according to villas_node_input.json (result of read_mapping_file)
    @param version:
    @param type:
    @return: json object formatted according to "sogno_input.json"
    """
    timestamp = VillasNodeInput["ts"]["origin"]
    # sequence = VillasNodeInput["sequence"]
    data = VillasNodeInput["data"]

    SongoInput = {}
    SongoInput["version"] = version
    SongoInput["identifier"] = "123456"
    SongoInput["type"] = type
    SongoInput["readings"] = []

    for idx, elem in enumerate(input_mapping_vector):
        uuid = elem[0]
        type = elem[2]  # mag or phase

        value = {}
        value["id"] = uuid
        value["timestamp"] = timestamp
        value["phase"] = "a"
        value["measurand"] = ""
        if type == "mag":
            value["measurand"] = "voltage_magnitude"
        elif type == "phase":
            value["measurand"] = "voltage_angle"
        value["data"] = data[idx]

        SongoInput["readings"].append(value)

    return SongoInput


def convertSognoOutputToVillasNodeOutput(SognoOutput, output_mapping_vector):
    """
    @param SognoOutput: string formatted according to the file "sogno_output.json"
    @param output_mapping_vector: according to villas_node_input.json (see function read_mapping_file)
    @return: string formatted according to "villas_node_output.json"
    """
    SognoOutput = loads(SognoOutput)

    timestamp_sogno = SognoOutput["nodes"][0]["values"][0]["timestamp"]
    # Convert UTC datetime to seconds since January 1, 1970
    utc_dt = datetime.strptime(timestamp_sogno, '%Y-%m-%dT%H:%M:%S')
    timestamp_villas = (utc_dt - datetime(1970, 1, 1)).total_seconds()

    nodes = SognoOutput["nodes"]
    data_sogno = {}
    for node in nodes:
        node_id = node["node_id"]
        values = node["values"]
        for value in values:
            if value["measurand"] == "voltage_magnitude":
                data_sogno[node_id + ".mag.est"] = value["data"]
            elif value["measurand"] == "voltage_angle":
                data_sogno[node_id + ".phase.est"] = value["data"]

    data_villas = [0.0] * len(output_mapping_vector)
    for idx, elem in enumerate(output_mapping_vector):
        if elem[0] == "max_err":
            continue
        elif elem[0] == "mean_err":
            continue
        elif elem[0] == "scenario_flag":
            continue
        elif elem[3] == "pf":
            continue
        elif elem[3] == "est":
            node_id = elem[0]
            value_type = elem[2]  # phase or magnitude
            data_villas[idx] = data_sogno[node_id + "." + value_type + ".est"]

    VillasOutput = {}
    VillasOutput["ts"] = {}
    VillasOutput["ts"]["origin"] = []
    VillasOutput["ts"]["origin"].append(timestamp_villas)
    VillasOutput["sequence"] = 0
    VillasOutput["data"] = data_villas

    return dumps([VillasOutput])
