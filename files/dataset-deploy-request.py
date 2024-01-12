from flask import Flask,request
import pyodbc
import json
import os
import time
import requests

# Retrieve connection details from environment variables
# server = os.environ.get('AZURE_SQL_SERVER')
# database = os.environ.get('AZURE_SQL_DATABASE')
# username = os.environ.get('AZURE_SQL_USER')
# password = os.environ.get('AZURE_SQL_PASSWORD')
# jiraUrl = os.environ.get('JIRA_URL')

server = 'datamgmt-felixchung-demo-sql01.database.windows.net'
database = 'datamgmt-felixchung-demo-db01'
username = 'dbadmin01'
password = 'Passw0rd'
jiraUrl = 'http://localhost:5001/submit-jira'

app = Flask(__name__)

@app.route('/request-dataset-deploy', methods=['POST'])
def requestDatasetDeploy():
    # Get the JSON from the POST request body
    try:
        json_array = request.get_json()
    except ValueError:
        return "Invalid JSON", 400
    
    connection_string = """
        Driver={{ODBC Driver 18 for SQL Server}};
        Server={server};
        Database={database};
        Uid={username};
        Pwd={password};
        Encrypt=yes;
        TrustServerCertificate=no;
        Connection Timeout=30;
    """.format(server=server, database=database, username=username, password=password)

    datasetPath = json_array[0].get('dataset_path')


    # SQL query to insert JSON string into the table
    sql_query = """
            INSERT INTO dbo.DATA_CATALOG_DRAFT 
            (
                batch_key
                ,name
                ,description
                ,is_sensitive
                ,data_type
                ,dataset_path
                ,status
                ,create_datetime
                ,create_user
                ,last_modified_datetime
                ,last_modified_user
            )
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """

    # Establish a connection to the database
    with pyodbc.connect(connection_string) as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute(f"select count(1) as cnt from dbo.DATA_CATALOG_DRAFT where status='pending' and dataset_path = '{datasetPath}'")
                # Fetch all the rows
                rows = cursor.fetchall()
                for row in rows:
                    if row[0] > 0:
                        responseText = "There has already been pending request for this dataset for approval"
                        return responseText
                    
                # Iterate over the JSON array and insert each item
                batch_key = int(round(time.time() * 1000))
                for item in json_array:
                    item['batch_key'] = batch_key

                    data_tuple = (
                    batch_key,
                    item['name'],
                    item['description'],
                    item['is_sensitive'],
                    item['data_type'],
                    item['dataset_path'],
                    item['status'],
                    item['create_datetime'],
                    item['create_user'],
                    item['last_modified_datetime'],
                    item['last_modified_user']
                    )
                
                    # Execute the SQL query
                    cursor.execute(sql_query, data_tuple)


                # Define the headers, including the content type and any necessary authentication tokens
                headers = {
                    'Content-Type': 'application/json',
                        # 'Authorization': 'Bearer your_auth_token'  # Uncomment and replace if authentication is required
                }

                # Send the POST request
                response = requests.post(jiraUrl, headers=headers,data=json.dumps(json_array))
                
                if response.status_code == 200 and response.text == 'Jira submitted successfully.':
                     # Commit the transaction
                    conn.commit()
                    return "Data catalog draft can be imported successfully"
                else:
                    conn.rollback()
                    return 'Get some issue when submitting Jira ticket',9000
    

            except pyodbc.DatabaseError as e:
                conn.rollback()  # Rollback the transaction on error
            finally:
                conn.rollback()  # Rollback the transaction on error

@app.route('/submit-jira', methods=['POST'])
def submitJira():
     # Get the JSON from the POST request body
    try:
        data = request.get_json()
    except ValueError:
        return "Invalid JSON", 400

    # Define which keys to include
    include_keys = ['name', 'description', 'is_sensitive',
                    'data_type']
    
    datasetPath = data[0].get("dataset_path")
    batchKey = data[0].get("batch_key")

    # Use the include_keys list to construct the header row
    header_row = "||" + "||".join(include_keys) + "||"

    # Collect rows using only the included keys
    rows = []
    for item in data:
        row = "|".join(' ' if item.get(key) == '' else str(item.get(key)) for key in include_keys)
        rows.append("|{}|".format(row))

    # Combine header and rows
    table_string = "\n".join([header_row] + rows)

    # Define the API endpoint
    api_endpoint = 'https://felixchung.atlassian.net/rest/servicedeskapi/request'

    # Define the JSON payload
    payload = {
        "requestFieldValues": {
            "description": table_string,
            "summary": f"Request to promote {datasetPath}",
            "customfield_10063": datasetPath,
            "customfield_10003": [{"accountId": "712020:eb83f9a3-84bc-41d7-b911-344efd79bc45"}],
            "customfield_10064":  str(batchKey)
        },
        "requestTypeId": "37",
        "serviceDeskId": "4"
    }


    # Define the headers, including the content type and any necessary authentication tokens
    headers = {
        'Content-Type': 'application/json',
        # 'Authorization': 'Bearer your_auth_token'  # Uncomment and replace if authentication is required
    }

    # Replace with your actual username and password for Basic Auth
    username = 'felix.chung@felixchung.org'
    password = 'ATATT3xFfGF0uWtupCocbNyFCYZQehCWt5uij2lE7_DC9ISyWWUrK06yXpXMlxFHRh9YPMruj85vnBiygr7uJCyWv1q6QCJjk0LCaKXhosI4XG-k54wlJS8Swbkgz7t8bQLremvEkHWdhypLgIiqW02fenEvV5PYUBUyAu9nAfPULBB0WLM7mpE=0580D2EA'

    # Send the POST request
    response = requests.post(api_endpoint, headers=headers,
                         data=json.dumps(payload), auth=(username, password))

    # Check the response
    if response.status_code == 201:
        return "Jira submitted successfully."
    else:
        return response.text, response.status_code
    return

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)

    