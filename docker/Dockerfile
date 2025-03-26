FROM ubuntu:22.04
ENV BASE=/data/code/
RUN mkdir -p $BASE

RUN apt-get update && apt-get install --yes python3 python3-pip 
RUN pip3 install wecom-bot-svr==0.3.3

