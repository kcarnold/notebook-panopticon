import zipfile
import os
import re
from pathlib import Path
import click

def extract_student_name(path):
    """Extract student name from submission path."""
    # Example: "Fname Lname_1234_assignsubmission_file/notebook.ipynb"
    parts = Path(path).parts[0].split('_')
    return parts[0]

def find_assignment_name(filenames):
    """Try to find assignment name from notebook filenames using uDDnD pattern."""
    
    # Strip .ipynb extension once at the start and normalize filenames
    filenames = [Path(f).stem.strip() for f in filenames]
    filenames = [re.sub(r'\(\d+\)$', '', f) for f in filenames]
    filenames = [re.sub(r'-ipynb$', '', f) for f in filenames]

    pattern = r'u\d{2}n\d-[^/]+$'
    matches = sorted(set([f for f in filenames if re.search(pattern, f.lower())]))
    
    if len(matches) == 1:
        return matches[0]
    elif len(matches) == 0:
        print("No filenames match the uDDnD pattern. Examples found:")
        for f in matches[:3]:  # Show first 3 examples
            print(f"  {f}")
    else:
        print("Multiple filenames match the uDDnD pattern:")
        for f in matches:
            print(f"  {f}")
    
    result = click.prompt("Please enter the assignment name to use")
    # make sure the result itself matches the pattern!
    if not re.match(pattern, result):
        raise ValueError("Invalid assignment name")
    return result

@click.command()
@click.argument('zipfile_paths', type=click.Path(exists=True), nargs=-1)
def process_submissions(zipfile_paths):
    """Process a ZIP file of student submissions."""
    for zipfile_path in zipfile_paths:
        if not zipfile_path.lower().endswith('.zip'):
            print(f"Skipping {zipfile_path} - not a ZIP file")
            continue
        process_submission_zip(zipfile_path)

def process_submission_zip(zipfile_path):
    """Process a single ZIP file of student submissions."""
    print(f"Processing {zipfile_path}")
    with zipfile.ZipFile(zipfile_path) as zf:
        # Get all .ipynb files
        notebooks = [f for f in zf.namelist() if f.endswith('.ipynb')]
        if not notebooks:
            print("No notebook files found in ZIP!")
            return

        # Find assignment name
        assignment_name = find_assignment_name([Path(n).name for n in notebooks])
        
        # Create output directory
        output_dir = Path('data/submissions') / assignment_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Process each notebook
        for notebook_path in notebooks:
            student_name = extract_student_name(notebook_path)
            output_path = output_dir / f"{student_name}.ipynb"
            
            print(f"Extracting {student_name}'s notebook to {output_path}")
            with zf.open(notebook_path) as src, open(output_path, 'wb') as dst:
                dst.write(src.read())

if __name__ == '__main__':
    process_submissions()