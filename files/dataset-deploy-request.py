from flask import Flask,request
import json
import os
import requests
import csv
import io
import base64

# Retrieve connection details from environment variables
ticketSysUrl = os.environ.get('TICKET_SYS_URL')
user = os.environ.get('TICKET_SYS_USER')
pw = os.environ.get('TICKET_SYS_PW')

app = Flask(__name__)


@app.after_request
def after_request(response):
    # Only add CORS headers if the Origin header exists and is from localhost
    origin = request.headers.get('Origin')
    if origin and 'localhost' in origin:
        # Add CORS headers to the response
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/submit-ticket', methods=['POST'])
def submitTicket():
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
    datasetName = data[0].get("dataset_name")
    folderPath = data[0].get("folder_path")

    # Create an in-memory string buffer
    output = io.StringIO()

    # Create a CSV writer object using the in-memory buffer
    csvwriter = csv.writer(output)

    # Write the header row using the include_keys list
    csvwriter.writerow(include_keys)

    # Write the data rows, filtering out only the included keys
    for item in data:
        row = [item[key] for key in include_keys]  # Extract the desired keys
        csvwriter.writerow(row)

    # Retrieve the CSV content
    csv_content = output.getvalue()

    # Don't forget to close the StringIO object when done
    output.close()

    # Encode the CSV content using base64
    encoded_csv_content = base64.b64encode(csv_content.encode('utf-8'))

    # If you need the base64 output as a string
    encoded_csv_string = encoded_csv_content.decode('utf-8')            

    # Define the JSON payload
    payload = {
        "title": f"Deploy {datasetPath}",
        "group": "Users",
        "customer": "felix.chung@felixchung.org",
        "approved": False,
        "datasetname": datasetPath,
        "article": {
           "subject": "Request dataset deployment",
           "body": f"Request dataset {datasetPath} production deployment. Please review the attached data mapping",
           "type": "note",
           "internal": False,
           "attachments": [
                {
                   "filename": f"{datasetPath}.csv",
                   "data": encoded_csv_string,
                   "mime-type": "text/plain"
                }
           ]
         }
    }


    # Define the headers, including the content type and any necessary authentication tokens
    headers = {
        'Content-Type': 'application/json',
        # 'Authorization': 'Bearer your_auth_token'  # Uncomment and replace if authentication is required
    }

    postData = json.dumps(payload)
    # Send the POST request
    response = requests.post(ticketSysUrl, headers=headers,
                         data=postData, auth=(user, pw))

    # Check the response
    if response.status_code == 201:
        return "Ticket submitted successfully."
    else:
        return response.text, response.status_code
    return

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)

    
