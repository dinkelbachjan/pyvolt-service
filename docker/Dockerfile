FROM python:3.7

LABEL name=state-estimation-service
LABEL version=1.0
LABEL description='state-estimation-service'
LABEL maintainer='Jan Dinkelbach'
LABEL maintainer_email='jdinkelbach@eonerc.rwth-aachen.de'

ADD . /state-estimation-service
WORKDIR /state-estimation-service

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

WORKDIR /state-estimation-service/state-estimation
RUN pip install -r requirements.txt
RUN python setup.py develop

WORKDIR /state-estimation-service/state-estimation/dependencies/cimpy
RUN python setup.py develop


WORKDIR /state-estimation-service/examples/

CMD ["sh", "-c", "sleep 30 &&  python ./run_state_estimation_service_villas_interface.py"]