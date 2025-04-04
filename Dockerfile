FROM registry.global.ccc.srvb.bo.paas.cloudcenter.corp/produban/python-311-ubi8:1.5.0.RELEASE

COPY . .

USER root

RUN pip config --user set global.index https://nexus.alm.europe.cloudcenter.corp/repository/pypi-public/simple && \
	pip config --user set global.index-url https://nexus.alm.europe.cloudcenter.corp/repository/pypi-public/simple && \
	pip config --user set global.trusted-host nexus.alm.europe.cloudcenter.corp && \
	pip install pipenv==2023.12.1 --no-cache-dir && \
	pipenv requirements > requirements.txt && \
	pip install -r requirements.txt && \
	rm requirements.txt

ENV SSL_CERT_FILE /etc/pki/tls/certs/ca-bundle.crt
ENV REQUESTS_CA_BUNDLE /etc/pki/tls/certs/ca-bundle.crt

RUN chmod -R 775 /opt

ENV UID 29000

ENV APP_HOME /opt

RUN chmod +x entrypoint.sh
ENTRYPOINT ["/bin/bash", "entrypoint.sh"]

USER $UID
