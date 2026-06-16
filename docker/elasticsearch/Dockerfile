ARG ELASTICSEARCH_BASE_IMAGE=docker.elastic.co/elasticsearch/elasticsearch:8.15.0
FROM ${ELASTICSEARCH_BASE_IMAGE}

ARG IK_PLUGIN_URL=https://get.infini.cloud/elasticsearch/analysis-ik/8.15.0
RUN elasticsearch-plugin install --batch "${IK_PLUGIN_URL}"
