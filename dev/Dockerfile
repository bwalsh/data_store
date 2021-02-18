FROM python:3.7.6-buster

# install vi
RUN apt-get --quiet update
RUN apt-get install -y vim

# install python client libraries for all the databases
RUN pip install pypfb gripql redisgraph neo4j pymongo psycopg2 elasticsearch-dsl

#  install misc dev tools
RUN pip install tabulate pandas plotly 
