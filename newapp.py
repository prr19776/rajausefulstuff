import streamlit as st
import os
import yaml
import tempfile
import zipfile
from jinja2 import Environment, FileSystemLoader
from io import BytesIO

#Global Var
templates_folder = "templates"

def load_template_config(template_folder):
    template_config_path = os.path.join(template_folder, "template_config.yaml")
    with open(template_config_path, "r") as template_config_file:
        return yaml.safe_load(template_config_file)

def get_template_filenames(template_folder):
    template_compose_path = os.path.join(template_folder, "template_compose.yml")
    with open(template_compose_path, 'r') as yaml_file:
        template_data = yaml.safe_load(yaml_file)

    # Create a list of template names from the YAML data, excluding "Choose a Template"
    template_names = list(template_data.keys())  # Exclude "Choose a Template"

    # Create a sidebar with a multiselect for template selection
    selected_template_names = st.sidebar.multiselect("Select Templates", template_names)

    # Initialize a list to store selected filenames while maintaining order
    selected_filenames_list = []

    # Initialize a set to track unique filenames
    selected_filenames_set = set()

    # Get the selected templates and their filenames
    for selected_template_name in selected_template_names:
        # Get the selected template based on the name
        selected_template = template_data.get(selected_template_name, {})
        
        # Get the filenames from the selected template
        selected_filenames = selected_template.get("filenames", [])
        
        # Add unique filenames to the list and set
        for filename in selected_filenames:
            if filename not in selected_filenames_set:
                selected_filenames_list.append(filename)
                selected_filenames_set.add(filename)

    return selected_filenames_list

# Function to generate output templates and save them to a temporary directory
def generate_output_templates(template_filenames, user_inputs, templates_folder):
    output_dir = tempfile.mkdtemp()  # Create a temporary directory to store output templates
    output_templates = {}  # Dictionary to store template names and their content

    for selected_template in template_filenames:
        # Load the selected YAML template
        with open(os.path.join(templates_folder, selected_template), "r") as template_file:
            template_yaml = template_file.read()

        # Create a Jinja2 environment
        env = Environment(loader=FileSystemLoader(templates_folder))
        template = env.from_string(template_yaml)

        # Render the template with user inputs
        rendered_template = template.render(**user_inputs)

        # Save the rendered template to the temporary directory
        output_template_filename = os.path.join(output_dir, selected_template)
        with open(output_template_filename, "w") as output_file:
            output_file.write(rendered_template)

        # Store the output template in the dictionary
        output_templates[selected_template] = output_template_filename

    return output_templates, output_dir

def validate_text_field(field_label, user_input, field_validations):
    if "required" in field_validations and field_validations["required"] and not user_input:
        st.warning(f"{field_label} is required.")
        return False

    if "max_length" in field_validations and len(user_input) > field_validations["max_length"]:
        st.warning(f"{field_label} should not exceed {field_validations['max_length']} characters.")
        return False

    # Add more specific validation rules as needed.

    return True

def layout_handler():
  
  # Hide the "Made with Streamlit" text using custom CSS
    hide_streamlit_style = """
        <style>
        footer {visibility: hidden;}
        .stDeployButton {display: none;}
        .baseButton-headerNoPadding {display: none;}
        #MainMenu {display: none !important;}
        </style>
        """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

def generate_zip_bundle(selected_templates, user_inputs):
    left_column, right_column = st.columns(2)

    # Generate button
    if left_column.button("Generate"):
        # Generate the output templates and get the temporary directory
        output_templates, output_dir = generate_output_templates(selected_templates, user_inputs, templates_folder)

        # Create a zip file containing the output templates in memory
        output_zip = BytesIO()
        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
            for template_name, template_path in output_templates.items():
                zipf.write(template_path, arcname=template_name)

        zip_filename = f"{user_inputs['app_name']}_output.zip"
        right_column.download_button(
            label=f"Download {zip_filename}",
            data=output_zip.getvalue(),
            file_name=zip_filename,  # Set the filename
            mime="application/zip",  # Set the MIME type to ensure the correct extension
        )

def field_handler(user_inputs, field):
    field_name = field["name"]
    field_label = field["label"]
    field_type = field["type"]
    field_validations = field.get("validation", {})  # Get field-specific validations

    if field_type == "text":
        user_input = st.text_input(field_label)
        if validate_text_field(field_label, user_input, field_validations):
            user_inputs[field_name] = user_input
    if field_type == "number":
        user_input = int(st.number_input(field_label,min_value=1))
        user_inputs[field_name] = user_input
    elif field_type == "radio":
        field_options = field["options"]
        user_inputs[field_name] = st.radio(field_label, field_options)


## main function ##
def main():

    layout_handler()

    selected_templates = get_template_filenames(templates_folder)

    # Ensure at least one template is chosen before enabling the generate button
    if not selected_templates:
        st.sidebar.warning("Please select at least one template.")
        return

    formatted_list = ", ".join(selected_templates)
    st.sidebar.markdown(f"Expected file(s) in zip : {len(selected_templates)} <br>List : {formatted_list}",  unsafe_allow_html=True)
    
    # Form input fields
    user_inputs = {}

    # Load the template configuration from the configured folder
    template_config = load_template_config(templates_folder)

    # Render and display common fields based on the configuration
    common_fields = template_config.get("common_fields", [])
    for field in common_fields:
        field_handler(user_inputs, field)

    # Render and display fields based on the selected templates and configuration
    for selected_template in selected_templates:
        if selected_template in template_config:
            for field in template_config[selected_template]:
                field_handler(user_inputs, field)

    generate_zip_bundle(selected_templates, user_inputs)


if __name__ == "__main__":
    main()