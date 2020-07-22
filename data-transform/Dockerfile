FROM python:3.6.4-slim-jessie
COPY requirements.txt /
RUN pip install -r /requirements.txt
COPY *.py /
CMD ["python"  , "transform.py"]