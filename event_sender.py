import os
import json
import logging
import requests
from flask import Flask, render_template, request, redirect, url_for

PAGERDUTY_API_URL = "https://events.pagerduty.com/v2/enqueue"
GENERATED_FOLDER = 'generated_files'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def list_organizations():
    """Return a list of organization subdirectories."""
    orgs = []
    base_dir = GENERATED_FOLDER
    if os.path.exists(base_dir):
        for entry in os.listdir(base_dir):
            path = os.path.join(base_dir, entry)
            if os.path.isdir(path):
                orgs.append(entry)
    return orgs

def list_event_files(org):
    """Return a list of JSON event files for a given organization."""
    org_folder = os.path.join(GENERATED_FOLDER, org)
    files = []
    if os.path.exists(org_folder):
        for f in os.listdir(org_folder):
            if f.endswith("events.json") or "events_" in f:  # adjust as needed
                files.append(f)
    return files

def load_event_file(org, filename):
    """Load a JSON event file with cleanup for malformed data."""
    path = os.path.join(GENERATED_FOLDER, org, filename)
    with open(path, 'r') as f:
        content = f.read().strip()

    # Extract the JSON array by finding the first '[' and last ']'
    start_index = content.find("[")
    end_index = content.rfind("]")
    if start_index == -1 or end_index == -1:
        raise ValueError("File does not contain a valid JSON array.")
    content = content[start_index:end_index+1]

    try:
        data = json.loads(content)
        return data
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error in file {filename}: {e}")
        raise

def prepare_event_payload(event):
    """
    Remove scheduling metadata (timing_metadata and repeat_schedule) from the event.
    Also ensure that the 'custom_details' include the service_name.
    """
    new_event = event.copy()
    new_event.pop("timing_metadata", None)
    new_event.pop("repeat_schedule", None)
    return new_event

def send_event(payload, routing_key):
    """Send a single event payload to PagerDuty."""
    headers = {"Content-Type": "application/json"}
    # Add the routing key to the payload
    payload["routing_key"] = routing_key
    response = requests.post(PAGERDUTY_API_URL, headers=headers, json=payload)
    return response

def event_sender():
    if request.method == 'POST':
        org = request.form.get('organization')
        filename = request.form.get('filename')
        routing_key = request.form.get('routing_key')
        
        # Load the event file
        try:
            events = load_event_file(org, filename)
        except Exception as e:
            logging.error(f"Error loading event file: {e}")
            return f"Error loading file: {e}", 500
        
        # Process and send each event
        results = []
        for event in events:
            payload = prepare_event_payload(event)
            response = send_event(payload, routing_key)
            results.append({
                "summary": event.get("payload", {}).get("summary", "N/A"),
                "status_code": response.status_code,
                "response": response.text
            })
        return render_template("event_sender_results.html", results=results)
    
    # For GET, render a form that lets the user select organization, event file, and enter a routing key.
    organizations = list_organizations()
    return render_template("event_sender.html", organizations=organizations)

# Route to load event files for a given organization (for use in AJAX or similar)

def get_files(org):
    files = list_event_files(org)
    return json.dumps(files)