FROM docker.io/panzhongxian/wecom-bot-svr

RUN python3 -m pip install -i https://test.pypi.org/simple/ wecom-bot-svr==0.1.11

COPY *.py /data/code/

CMD ["python3", "/data/code/demo.py" ]
