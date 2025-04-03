from flask import Flask, render_template, request, send_from_directory, redirect, url_for
import os
import datetime
import utils

app = Flask(__name__)
app.config['GENERATED_FOLDER'] = 'generated_files'

# Ensure the main generated_files folder exists
if not os.path.exists(app.config['GENERATED_FOLDER']):
    os.makedirs(app.config['GENERATED_FOLDER'])

def sanitize_org(org_name):
    # Basic sanitization: remove spaces and non-alphanumeric characters
    return "".join(c for c in org_name if c.isalnum())

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Retrieve form data
        scenario = request.form.get('scenario')
        org_name = request.form.get('org_name')
        itsm_tools = request.form.get('itsm_tools')
        observability_tools = request.form.get('observability_tools')
        api_key = request.form.get('api_key')
        service_names = request.form.get('service_names')
        
        # Set default service names if none provided
        if not service_names:
            if scenario == 'major':
                service_names = "User Authentication, API Nodes, Payment Processing"
            elif scenario == 'partial':
                service_names = "API Nodes, Database"
            elif scenario == 'well':
                service_names = "Storage"
        
        # Generate narrative content and events based on the selected scenario
        if scenario == 'major':
            narrative = utils.generate_major(org_name, api_key, itsm_tools, observability_tools)
            outage_summary = utils.extract_outage_summary(narrative)
            incident_details = utils.extract_incident_details(narrative)
            events = utils.generate_major_events(org_name, api_key, itsm_tools, observability_tools, outage_summary, service_names, incident_details)
        elif scenario == 'partial':
            narrative = utils.generate_partial(org_name, api_key, itsm_tools, observability_tools)
            outage_summary = utils.extract_outage_summary(narrative)
            incident_details = utils.extract_incident_details(narrative)
            events = utils.generate_partial_events(org_name, api_key, itsm_tools, observability_tools, outage_summary, service_names, incident_details)
        elif scenario == 'well':
            narrative = utils.generate_well(org_name, api_key, itsm_tools, observability_tools)
            outage_summary = utils.extract_outage_summary(narrative)
            incident_details = utils.extract_incident_details(narrative)
            events = utils.generate_well_events(org_name, api_key, itsm_tools, observability_tools, outage_summary, service_names, incident_details)
        else:
            narrative = "Invalid scenario selected."
            events = ""
        
        # Create a subdirectory for the organization (sanitize org name)
        org_folder = os.path.join(app.config['GENERATED_FOLDER'], sanitize_org(org_name))
        if not os.path.exists(org_folder):
            os.makedirs(org_folder)
        
        # Save narrative content to a file with a timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        narrative_filename = f"{scenario}_{timestamp}.txt"
        narrative_path = os.path.join(org_folder, narrative_filename)
        with open(narrative_path, 'w') as f:
            f.write(narrative)
        
        # Save events content to a separate file (JSON)
        events_filename = f"{scenario}_events_{timestamp}.json"
        events_path = os.path.join(org_folder, events_filename)
        with open(events_path, 'w') as f:
            f.write(events)
        
        # Redirect to the preview page for this organization (listing all files)
        return redirect(url_for('preview_org', org=sanitize_org(org_name)))
        
    return render_template('index.html')

@app.route('/preview/<org>/', methods=['GET'])
def preview_org(org):
    # List all files for the organization subdirectory
    org_folder = os.path.join(app.config['GENERATED_FOLDER'], org)
    if not os.path.exists(org_folder):
        files = []
    else:
        files = os.listdir(org_folder)
    return render_template('preview.html', selected_org=org, files=files)

@app.route('/preview/', methods=['GET'])
def preview_orgs():
    # List all organization folders in the generated_files directory
    orgs = []
    base_dir = app.config['GENERATED_FOLDER']
    if os.path.exists(base_dir):
        for entry in os.listdir(base_dir):
            path = os.path.join(base_dir, entry)
            if os.path.isdir(path):
                orgs.append(entry)
    return render_template('preview.html', organizations=orgs)

@app.route('/preview/<org>/<filename>', methods=['GET', 'POST'])
def preview_file(org, filename):
    file_path = os.path.join(app.config['GENERATED_FOLDER'], org, filename)
    if request.method == 'POST':
        # Save edited content back to the file
        edited_content = request.form.get('edited_content')
        with open(file_path, 'w') as f:
            f.write(edited_content)
        return redirect(url_for('preview_file', org=org, filename=filename))
    
    # Load file content for preview
    with open(file_path, 'r') as f:
        content = f.read()
    return render_template('preview.html', selected_org=org, selected_file=filename, content=content)

@app.route('/download/<org>/<filename>')
def download(org, filename):
    directory = os.path.join(app.config['GENERATED_FOLDER'], org)
    return send_from_directory(directory, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)