""" Module in charge of global variables
that don't change by environment
"""
import os
os.environ['DARWIN_APPKEY'] = os.getenv('DARWIN_APPKEY', 'apm2123')
from version import __version__

gluon = 'GLUON'
# Observability configuration
os.environ['DARWIN_LOGGING_FORMAT'] = gluon
os.environ['DARWIN_LOGGING_COMPANY'] = os.getenv('DARWIN_LOGGING_COMPANY', 'sgt')
os.environ['DARWIN_LOGGING_COMPANY_COMPONENT_NAME'] = os.getenv('DARWIN_LOGGING_COMPANY_COMPONENT_NAME', 'sgt')
os.environ['DARWIN_LOGGING_COMPANY_COMPONENT_ID'] = os.getenv('DARWIN_LOGGING_COMPANY_COMPONENT_ID', 'CHANGEIT_CMPT_ID')
os.environ['DARWIN_LOGGING_COMPANY_COMPONENT_TYPE'] = os.getenv('DARWIN_LOGGING_COMPANY_COMPONENT_TYPE', 'microservice')
os.environ['DARWIN_LOGGING_COMPANY_APP_NAME'] = os.getenv('DARWIN_LOGGING_COMPANY_APP_NAME', 'apm2123')
os.environ['DARWIN_LOGGING_COMPANY_APP_ID'] = os.getenv('DARWIN_LOGGING_COMPANY_APP_ID', 'CHANGEIT_APP_ID')
os.environ['COMPONENT_VERSION'] = __version__
# Error handling configuration
os.environ['DARWIN_CORE_EXCEPTIONS_ERROR_FORMAT'] = gluon

