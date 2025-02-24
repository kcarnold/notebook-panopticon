from difflib import SequenceMatcher
import io
import streamlit as st
import streamlit.components.v1 as components
import nbformat
from pathlib import Path
import random
from nbdime import diff_notebooks
import nbdime.prettyprint as nbdiff_print
#from nbdime.webapp.nbdimeserver import diff_to_html

DATA_DIR = Path("data")
SUBMISSIONS_DIR = DATA_DIR / "submissions"
STARTERS_DIR = DATA_DIR / "starters"


def find_matching_starter(submission_path, starter_paths):
    """Find the starter notebook that best matches the submission."""
    submission = nbformat.read(submission_path, as_version=4)
    
    best_match = None
    best_score = float('inf')
    
    for starter_path in starter_paths:
        starter = nbformat.read(starter_path, as_version=4)
        score = compute_diff_score(submission, starter)
        
        if score < best_score:
            best_score = score
            best_match = starter_path
            
    return best_match, best_score

def compute_diff_score(submission, starter):
    """Compute a similarity score between submission and starter notebooks."""
    # Simple implementation: compare source code of all cells
    submission_code = '\n'.join(cell.get('source', '') for cell in submission.cells)
    starter_code = '\n'.join(cell.get('source', '') for cell in starter.cells)
    
    # Use SequenceMatcher to get a similarity ratio
    similarity = SequenceMatcher(None, submission_code, starter_code).ratio()
    # Convert similarity to a distance score (0 = identical, higher = more different)
    return 1 - similarity

#@st.cache_data
def get_cached_diff(student, assignment):
    """Get or compute diff for student's assignment."""
    submission_path = SUBMISSIONS_DIR / assignment / f"{student}.ipynb"
    starter_paths = list(STARTERS_DIR.glob(f"{assignment}*.ipynb"))
    
    if not submission_path.exists():
        return {"error": "Submission not found"}

    if not starter_paths:
        return {"error": "No starter notebook found"}
    
    best_starter, score = find_matching_starter(submission_path, starter_paths)
    
    submission = nbformat.read(submission_path, as_version=4)
    starter = nbformat.read(best_starter, as_version=4)
    
    return compute_notebook_diff(submission, starter)

#@st.cache_data
def compute_notebook_diff(submission_notebook, starter_notebook):
    """Compute notebook diff and return HTML representation."""
    # Get the raw diff
    diff = diff_notebooks(starter_notebook, submission_notebook)

    # The webapp diff code uses JS that we can't run easily here.
    # So we'll use the command-line diff generator and convert to HTML.
    from nbdime.prettyprint import pretty_print_notebook_diff, PrettyPrintConfig
    output = io.StringIO()
    pretty_config = PrettyPrintConfig(
        out=output,
    )
    pretty_config.metadata = False
    pretty_config.outputs = False
    pretty_config.details = False
    assert pretty_config.should_ignore_path('/cells/3/metadata/execution')
    assert pretty_config.should_ignore_path('/cells/3/execution_count')
    pretty_print_notebook_diff("starter", "submission", starter_notebook, diff, pretty_config)
    terminal_output = output.getvalue()
    output.close()

    # Convert the terminal output to HTML
    import ansi2html
    converter = ansi2html.Ansi2HTMLConverter(dark_bg=False)
    html = converter.convert(terminal_output)

    
    # Add some custom CSS to make it work better in Streamlit
    html = f"""
    <style>
    .jp-Notebook {{ max-width: 100%; margin: 0; }}
    .jp-Cell {{ margin: 10px 0; }}
    .jp-OutputArea-output {{ overflow-x: auto; }}
    .jp-Diff-addedChunk {{ background-color: #e6ffe6; }}
    .jp-Diff-removedChunk {{ background-color: #ffe6e6; }}
    </style>
    {html}
    """
    return html

@st.cache_data
def get_assignments():
    """Get list of assignments from submissions directory."""
    return [d.name for d in SUBMISSIONS_DIR.iterdir() if d.is_dir()]


@st.cache_data
def get_students():
    """Get list of all students who have submitted any assignments."""
    students = set()
    for assignment_dir in SUBMISSIONS_DIR.iterdir():
        if not assignment_dir.is_dir():
            continue
        students.update(f.stem for f in assignment_dir.iterdir())
    return sorted(students)


def navigate_assignment(direction):
    """Navigate between assignments."""
    assignments = get_assignments()
    current = st.session_state.get("selected_assignment")
    assert current in assignments, f"Invalid current assignment: {current}"
    
    if direction == "random":
        new_assignment = random.choice(assignments)
    else:
        current_idx = assignments.index(current)
        if direction == "prev":
            new_idx = (current_idx - 1) % len(assignments)
        else:  # next
            new_idx = (current_idx + 1) % len(assignments)
        new_assignment = assignments[new_idx]
    
    st.session_state["selected_assignment"] = new_assignment

def navigate_student(direction):
    """Navigate between students."""
    students = get_students()
    current = st.session_state.get("selected_student")
    assert current in students, f"Invalid current student: {current}"
    if len(students) < 2:
        return
    
    if direction == "random":
        while (new_student := random.choice(students)) == current:
            pass
    else:
        current_idx = students.index(current)
        if direction == "prev":
            new_idx = (current_idx - 1) % len(students)
        else:  # next
            new_idx = (current_idx + 1) % len(students)
        new_student = students[new_idx]
    
    st.session_state["selected_student"] = new_student

def display_diff(diff_html, show_outputs=False):
    """Display the diff using Streamlit's HTML component."""
    if isinstance(diff_html, dict) and "error" in diff_html:
        st.error(diff_html["error"])
        return
    
    height = 500
    
    components.html(diff_html, height=height, scrolling=True)

def main():
    st.title("Notebook Diff Viewer")
    
    # Load data
    st.session_state["available_assignments"] = assignments = get_assignments()
    st.session_state['available_students'] = students = get_students()
    
    # Navigation controls
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("Assignment")
        selected_assignment = st.selectbox("Select Assignment", assignments, key="selected_assignment")
        cols = st.columns(3)
        with cols[0]:
            st.button("⬅️ Prev", on_click=lambda: navigate_assignment("prev"), key="prev_assignment")
        with cols[1]:
            st.button("Next ➡️", on_click=lambda: navigate_assignment("next"), key="next_assignment")
        with cols[2]:
            st.button("🔀 Random", on_click=lambda: navigate_assignment("random"), key="random_assignment")
    
    with col2:
        st.write("Student")
        selected_student = st.selectbox("Select Student", students, key="selected_student")
        cols = st.columns(3)
        with cols[0]:
            st.button("⬅️ Prev", on_click=lambda: navigate_student("prev"), key="prev_student")
        with cols[1]:
            st.button("Next ➡️", on_click=lambda: navigate_student("next"), key="next_student")
        with cols[2]:
            st.button("🔀 Random", on_click=lambda: navigate_student("random"), key="random_student")
    
    # Display options
    show_outputs = st.checkbox("Show Cell Outputs", value=False)
    
    # Get and display diff
    diff_data = get_cached_diff(selected_student, selected_assignment)
    display_diff(diff_data, show_outputs=show_outputs)


main()
