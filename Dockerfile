# ./docker/Dockerfile
FROM python:3.11
MAINTAINER Haktan Ozdemir haktanozdem@gmail.com

# specifying the working directory inside the container
WORKDIR /usr/src/app

# installing the Python dependencies
COPY ./requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# copying the contents of our app' inside the container
COPY . .

# defining env vars
ENV FLASK_APP=app.py
# watch app' files
ENV FLASK_DEBUG=true
ENV FLASK_ENV=development

EXPOSE 8000

# running Flask as a module, we sleep a little here to make sure that the DB is fully instnciated before running our app'
CMD ["/bin/bash","flask.sh"]

