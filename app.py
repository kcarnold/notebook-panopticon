from difflib import SequenceMatcher
from typing import Dict
import streamlit as st
import streamlit.components.v1 as components
import nbformat
from pathlib import Path
import random
import difflib
from rubric_analysis import do_rubric_check
from starter_notebooks import StarterMatch, find_closest_starter, get_all_starter_versions, unified_diff

st.set_page_config(
    layout="wide",
    page_title="Notebook Diff Viewer",
    page_icon=":notebook:"
)



DATA_DIR = Path("data")
SUBMISSIONS_DIR = DATA_DIR / "submissions"
STARTERS_DIR = DATA_DIR / "starters"

REPO_DIR = DATA_DIR / "cs-375-376-public"


@st.cache_resource
def all_starter_versions() -> Dict[str, Dict[str, str]]:
    """Map each starter notebook to its historical Quarto versions."""
    return get_all_starter_versions(REPO_DIR)


def compute_diff_score(submission, starter):
    """
    Compute a similarity score between submission and starter notebooks.
    Simple implementation that compares source code of all cells.
    """
    submission_code = '\n'.join(
        cell.get('source', '') for cell in submission.cells
    )
    starter_code = '\n'.join(
        cell.get('source', '') for cell in starter.cells
    )
    
    similarity = SequenceMatcher(None, submission_code, starter_code).ratio()
    return 1 - similarity


def get_submission_and_starter(student, assignment, versions) -> tuple[str, StarterMatch]:
    """Get or compute diff for student's assignment."""
    submission_path = SUBMISSIONS_DIR / assignment / f"{student}.ipynb"
    
    if not submission_path.exists():
        raise FileNotFoundError(f"Submission not found: {submission_path}")
    
    submission = nbformat.read(submission_path, as_version=4)
    submission_quarto = notebook_to_quarto(submission)
    return submission_quarto, find_closest_starter(submission_quarto, versions=versions)


def notebook_to_quarto(nb):
    """Convert notebook to Quarto markdown format."""
    chunks = []
    for cell in nb.cells:
        if cell.cell_type == 'markdown':
            chunks.append(cell.source)
        elif cell.cell_type == 'code':
            chunks.append(f"```{{python}}\n{cell.source}\n```")
    return '\n\n'.join(chunks)


def generate_unified_diff_html(a, b):
    """Generate HTML for a unified diff between two texts with collapsible common sections."""
    #diff = unified_diff(a.splitlines(), b.splitlines(), lineterm='', n=9999)
    a_lines = a.splitlines()
    b_lines = b.splitlines()
    ops = SequenceMatcher(None, a_lines, b_lines).get_opcodes()

    def format_chunk(lines, start, end):
        if not lines[start:end]:
            return ""
        chunk = "\n".join(lines[start:end])
        # Escape HTML characters
        chunk = chunk.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return chunk

    html_out = ''
    for tag, i1, i2, j1, j2 in ops:
        if tag == 'equal':
            html_out += f'<div class="equal">{format_chunk(a_lines, i1, i2)}</div>'
            continue
        if tag in {'replace', 'delete'}:
            html_out += f'<div class="delete">{format_chunk(a_lines, i1, i2)}</div>'
        if tag in {'replace', 'insert'}:
            html_out += f'<div class="insert">{format_chunk(b_lines, j1, j2)}</div>'

    custom_css = """
        .equal { background-color: white; font-size: 6px; }
        .delete { background-color: #ffe6e6; }
        .insert { background-color: #e6ffe6; }
        .diff-container { font-size: 10px; font-family: monospace; white-space: pre-wrap; overflow-x: auto; }
    """
    return f"""
    <style>{custom_css}</style>
    <div class="diff-container">
    <div class="diff-pane">
{html_out}
</div>
    </div>
    """


@st.cache_data
def get_assignments():
    """Get list of assignments from submissions directory."""
    return sorted([d.name for d in SUBMISSIONS_DIR.iterdir() if d.is_dir()])


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
        inc = -1 if direction == "prev" else 1
        new_idx = (current_idx + inc) % len(assignments)
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
        inc = -1 if direction == "prev" else 1
        new_idx = (current_idx + inc) % len(students)
        new_student = students[new_idx]
    
    st.session_state["selected_student"] = new_student


def main():
    # Load data
    st.session_state["available_assignments"] = assignments = get_assignments()
    st.session_state['available_students'] = students = get_students()
    
    # Navigation controls
    col1, col2 = st.columns(2)
    
    with col1:
        cols = st.columns([1, 1, 1, 4])
        with cols[0]:
            st.button("⬅️ Prev", on_click=lambda: navigate_assignment("prev"), key="prev_assignment")
        with cols[1]:
            st.button("Next ➡️", on_click=lambda: navigate_assignment("next"), key="next_assignment")
        with cols[2]:
            st.button("🔀 Random", on_click=lambda: navigate_assignment("random"), key="random_assignment")
        with cols[3]:
            selected_assignment = st.selectbox("Select Assignment", assignments, key="selected_assignment")
    
    with col2:
        cols = st.columns([4, 1, 1, 1])
        with cols[0]:
            selected_student = st.selectbox("Select Student", students, key="selected_student")
        with cols[1]:
            st.button("⬅️ Prev", on_click=lambda: navigate_student("prev"), key="prev_student")
        with cols[2]:
            st.button("Next ➡️", on_click=lambda: navigate_student("next"), key="next_student")
        with cols[3]:
            st.button("🔀 Random", on_click=lambda: navigate_student("random"), key="random_student")
    
    # Get and display diff
    try:
        versions = all_starter_versions()
        submission_quarto, match = get_submission_and_starter(selected_student, selected_assignment, versions=versions)
        starter_quarto = versions[match.starter][match.revision]
        unified_diff_text = unified_diff(submission_quarto, starter_quarto, n_context_lines=9999)
    except FileNotFoundError as e:
        st.error(f"Error: {e}")
        return

    rubric = st.text_area("Rubric", height=200)
    if st.button("Check against rubric"):
        do_rubric_check(rubric=rubric, document=unified_diff_text, document_title="Notebook Diff")
        

    # Display options
    diff_html = generate_unified_diff_html(starter_quarto, submission_quarto)

    height = 800
    components.html(diff_html, height=height, scrolling=True)


main()
