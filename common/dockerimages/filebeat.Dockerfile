FROM ubuntu:focal
RUN apt-get update && apt-get -y install sudo && apt-get -y install curl
RUN curl -sLO https://s3.timeweb.com/2475852b-3afdd654-9f26-4019-a9d4-ad20d884ad29/filebeat-8.17.0-amd64.deb
RUN sudo dpkg -i ./filebeat-8.17.0-amd64.deb

WORKDIR /code
COPY . /code/

CMD filebeat -e -c /code/filebeat.yml
