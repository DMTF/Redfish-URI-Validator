#! /usr/bin/python3
# Copyright Notice:
# Copyright 2018-2019 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfish-URI-Validator/blob/master/LICENSE.md

"""
Redfish URI Validator

File : redfish-uri-validator.py

Brief : This file contains the implementation of the URI validation test by
        consuming an OpenAPI specification and scanning all resources on a
        service.
"""

import argparse
from datetime import datetime
import json
import os
import re
import sys
import yaml

from redfish.ris import RmcApp
import RedfishLogo

tool_version = "0.9.0"

def run_test( user, password, rhost, openapi ):
    """
    Runs the URI test

    Args:
        user: The user name to use for the service
        password: The password to use for the service
        rhost: The host to use for the service
        openapi: The file name of the OpenAPI specification to use

    Returns:
        A results structure
    """

    print( "Opening {}...".format( openapi ) )
    try:
        with open( openapi ) as openapi_file:
            openapi_data = yaml.load(openapi_file, Loader=yaml.FullLoader)
    except:
        print( "ERROR: Could not open {}".format( openapi ) )
        return None

    # Creating RMC object
    RMCOBJ = RmcApp([])

    # Create cache directory
    config_dir = "data"
    RMCOBJ.config.set_cachedir( os.path.join( config_dir, "cache" ) )
    cachedir = RMCOBJ.config.get_cachedir()

    # If current cache exist try to log it out
    if os.path.isdir( cachedir ):
        RMCOBJ.logout

    # Login into the server, create a session, and download all resources
    print("Service URI: {}".format(rhost))
    print("Logging in and downloading resources; this may take a while...")
    try:
        RMCOBJ.login( base_url = rhost, username = user, password = password )
    except:
        print( "ERROR: Could not log into {} with credentials '{}':'{}'".format( rhost, user, password ) )
        return None

    # Get all resources
    RMCOBJ.select(['"*"'])
    response = RMCOBJ.get()

    # Go through each response and check the @odata.type and @odata.id properties against the OpenAPI file
    print( "Generating results..." );
    results = {}
    results["URIs"] = {}
    results["Orphans"] = []
    results["TotalPass"] = 0
    results["TotalFail"] = 0
    results["TotalWarn"] = 0
    for item in response:
        try:
            serv_file = item["@odata.type"].rsplit( "." )[0][1:]
            serv_type = item["@odata.type"].rsplit( "." )[-1]
            serv_uri = item["@odata.id"]
        except:
            results["Orphans"].append( item )
            results["TotalFail"] = results["TotalFail"] + 1
            continue

        # Go through each path object in the OpenAPI specification to find a match
        type_found = False
        path_match = False
        for uri in openapi_data["paths"]:
            # Pull the type from the reference
            try:
                ref = openapi_data["paths"][uri]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
                file = re.search( "([\\w\\d]+)(\\.v\\d+_\\d+_\\d+)?\\.yaml", ref ).group( 1 )
                type = ref.rsplit( "/" )[-1]
            except:
                # If we get here, then the path should be describing an action; ignore and move on
                continue

            # Check if the type found via the reference matches the @odata.type property
            if serv_file == file and serv_type == type:
                type_found = True

                # Check if the pattern in the path object matches the @odata.id property
                uri_pattern = "^" + re.sub( "{[A-Za-z0-9]+}", "[^/]+", uri ) + "$"
                if re.match( uri_pattern, serv_uri ) != None:
                    path_match = True

            if path_match:
                # Break out early since we got a match
                break

        # Log if a match was not found
        results["URIs"][serv_uri] = {}
        if type_found:
            if path_match:
                results["URIs"][serv_uri]["Result"] = "Pass"
                results["URIs"][serv_uri]["Details"] = "Pass"
                results["TotalPass"] = results["TotalPass"] + 1
            else:
                results["URIs"][serv_uri]["Result"] = "Fail"
                results["URIs"][serv_uri]["Details"] = "'{}' for type '{}' from file '{}' was not found in the OpenAPI specification".format( serv_uri, serv_type, serv_file )
                results["TotalFail"] = results["TotalFail"] + 1
        else:
            results["URIs"][serv_uri]["Result"] = "Warning"
            results["URIs"][serv_uri]["Details"] = "Type '{}' from file '{}' was not found in the OpenAPI specification".format( serv_type, serv_file )
            results["TotalWarn"] = results["TotalWarn"] + 1

    # Logout of the current session
    RMCOBJ.logout()

    return results

def generate_report( results, user, password, rhost, openapi ):
    """
    Creates an HTML report

    Args:
        results: The results structure from the test
        user: The user name to use for the service
        password: The password to use for the service
        rhost: The host to use for the service
        openapi: The file name of the OpenAPI specification to use
    """

    # The string template for the report
    html_string = """<html>
  <head>
    <title>Redfish URI Test Summary</title>
    <style>
      .pass {{background-color:#99EE99}}
      .fail {{background-color:#EE9999}}
      .warn {{background-color:#EEEE99}}
      .bluebg {{background-color:#BDD6EE}}
      .button {{padding: 12px; display: inline-block}}
      .center {{text-align:center;}}
      .log {{text-align:left; white-space:pre-wrap; word-wrap:break-word; font-size:smaller}}
      .title {{background-color:#DDDDDD; border: 1pt solid; font-height: 30px; padding: 8px}}
      .titlesub {{padding: 8px}}
      .titlerow {{border: 2pt solid}}
      .results {{transition: visibility 0s, opacity 0.5s linear; display: none; opacity: 0}}
      .resultsShow {{display: block; opacity: 1}}
      body {{background-color:lightgrey; border: 1pt solid; text-align:center; margin-left:auto; margin-right:auto}}
      th {{text-align:center; background-color:beige; border: 1pt solid}}
      td {{text-align:left; background-color:white; border: 1pt solid; word-wrap:break-word;}}
      table {{width:90%; margin: 0px auto; table-layout:fixed;}}
      .titletable {{width:100%}}
    </style>
  </head>
  <table>
    <tr>
      <th>
        <h2>##### Redfish URI Test Report #####</h2>
        <h4><img align=\"center\" alt=\"DMTF Redfish Logo\" height=\"203\" width=\"288\" src=\"data:image/gif;base64,{}\"></h4>
        <h4><a href=\"https://github.com/DMTF/Redfish-URI-Validator\">https://github.com/DMTF/Redfish-URI-Validator</a></h4>
        Tool Version: {}<br/>
        {}<br/><br/>
        This tool is provided and maintained by the DMTF.  For feedback, please open issues<br/>
        in the tool's Github repository: <a href=\"https://github.com/DMTF/Redfish-URI-Validator/issues\">https://github.com/DMTF/Redfish-URI-Validator/issues</a><br/>
      </th>
    </tr>
    <tr>
      <th>
        System: {}/redfish/v1/, User: {}, Password: {}<br/>
        OpenAPI Specification: {}<br/>
      </th>
    </tr>
    <tr>
      <td>
        <center><b>Results Summary</b></center>
        <center>Pass: {}, Fail: {}, Warning: {}</center>
      </td>
    </tr>
    <tr>
      <th class=\"titlerow bluebg\">
        <b>Results</b>
      </th>
    </tr>
    {}
  </table>
</html>
"""

    # Build the results section of the report
    html_results = ""
    results_populated = False

    # Go through the results and add them to the report
    if len( results["URIs"] ) != 0:
        results_populated = True
        for uri in sorted( results["URIs"].keys() ):
            html_results = html_results + "<tr>"
            html_results = html_results + "<td>" + uri + "</td>"
            result_class = "class=\"pass center\""
            if results["URIs"][uri]["Result"] == "Fail":
                result_class = "class=\"fail center\""
            elif results["URIs"][uri]["Result"] == "Warning":
                result_class = "class=\"warn center\""
            html_results = html_results + "<td " + result_class + " width=\"30%\">" + results["URIs"][uri]["Result"]
            if results["URIs"][uri]["Result"] != "Pass":
                html_results = html_results + ": " + results["URIs"][uri]["Details"] + "</td>"
            else:
                html_results = html_results + "</td>"
            html_results = html_results + "</tr>"

    # Go through the orphans and add them to the report
    if len( results["Orphans"] ) != 0:
        results_populated = True
        for orphan in results["Orphans"]:
            html_results = html_results + "<tr>"
            html_results = html_results + "<td><pre>" + json.dumps( orphan, sort_keys = True, indent = 4, separators = ( ",", ": " ) ) + "</pre></td>"
            html_results = html_results + "<td class=\"fail center\" width=\"30%\">Fail: Missing \"@odata.id\" and/or \"@odata.type\" from the payload</td>"
            html_results = html_results + "</tr>"

    # Close the results table if needed
    if results_populated:
        html_results = "<tr><td><table>" + html_results + "</table></td></tr>"

    current_time = datetime.now()
    log_file = datetime.strftime( current_time, "RedfishURITestReport_%m_%d_%Y_%H%M%S.html" )
    print( "Generating {}...". format( log_file ) )
    with open( log_file, "w", encoding = "utf-8") as out_file:
        out_file.write( html_string.format( RedfishLogo.logo, tool_version, current_time.strftime( "%c" ),
            rhost, user, password, openapi, results["TotalPass"], results["TotalFail"], results["TotalWarn"], html_results ) )

if __name__ == '__main__':

    # Get the input arguments
    argget = argparse.ArgumentParser( description = "A tool to walk a Redfish service and verify URIs against an OpenAPI specification" )
    argget.add_argument( "--user", "-u", type = str, required = True, help = "The user name for authentication" )
    argget.add_argument( "--password", "-p",  type = str, required = True, help = "The password for authentication" )
    argget.add_argument( "--rhost", "-r", type = str, required = True, help = "The address of the Redfish service (with address prefix)" )
    argget.add_argument( "--openapi", "-o", type = str, required = True, help = "The OpenAPI spec to use for validation" )
    args = argget.parse_args()

    # Run the test
    results = run_test( args.user, args.password, args.rhost, args.openapi )
    if results == None:
        sys.exit( 1 )
    else:
        # Generate the report
        generate_report( results, args.user, args.password, args.rhost, args.openapi )
        sys.exit( 0 )
