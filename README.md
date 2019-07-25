# Redfish URI Validator

Copyright 2018-2019 DMTF. All rights reserved.

## About

The Redfish URI Validator is a Python3 tool which scans all resources on a given service and verifies the URIs on the service match the patterns described in a provided OpenAPI specification.


## Requirements

Ensure that the machine running the tool has Python3 installed.

External modules:
* redfish: https://pypi.python.org/pypi/redfish
* pyyaml: https://pypi.org/project/PyYAML

You may install the external modules by running:

`pip3 install -r requirements.txt`


## Usage

Example: `python3 redfish-uri-validator.py --user root --password password --rhost https://192.168.1.100 --openapi C:\Redfish\openapi.yaml`

The tool will log into the service specified by the *rhost* argument using the credentials provided by the *user* and *password* arguments.  It then reads all resources on the specified service, and, using the `@odata.id` and `@odata.type` properties within the resource payloads, attempts to find matches for the resource in the OpenAPI specification provided by the *openapi* argument.  Each resource can have one of the following results:
* Pass: The given resource has a match in the OpenAPI specification
* Warning: The type specified by the `@odata.type` property could not be found in the OpenAPI specification.  This may happen if the resource is an OEM resource.
* Fail: This can happen for one of the following reasons
    * The type specified by the `@odata.type` is found in the OpenAPI specification, but the `@odata.id` property does not match any of the patterns specified by the OpenAPI specification
    * The resource is missing the `@odata.id` property and/or the `@odata.type` property

An HTML report is constructed and saved in the same directory as the tool.


## Options

```
usage: redfish-uri-validator.py [-h] --user USER --password PASSWORD --rhost
                                RHOST --openapi OPENAPI

A tool to walk a Redfish service and verify URIs against an OpenAPI
specification

required arguments:
  --user USER, -u USER  The user name for authentication
  --password PASSWORD, -p PASSWORD
                        The password for authentication
  --rhost RHOST, -r RHOST
                        The address of the Redfish service (with address
                        prefix)
  --openapi OPENAPI, -o OPENAPI
                        The OpenAPI spec to use for validation

optional arguments:
  -h, --help            show this help message and exit
```
