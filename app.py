import streamlit as st
import nbformat
from pathlib import Path
import random
from difflib import SequenceMatcher

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

@st.cache_data
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

@st.cache_data
def compute_notebook_diff(submission_notebook, starter_notebook):
    """Compute cell-by-cell differences between notebooks."""
    diff_result = []
    
    for i, sub_cell in enumerate(submission_notebook.cells):
        cell_diff = {
            "cell_type": sub_cell.cell_type,
            "index": i,
            "status": "added",
            "source": sub_cell.get('source', ''),
            "outputs": sub_cell.get('outputs', []) if sub_cell.cell_type == 'code' else None
        }
        
        # Try to find matching cell in starter
        best_match = None
        best_score = float('inf')
        for j, start_cell in enumerate(starter_notebook.cells):
            if start_cell.cell_type == sub_cell.cell_type:
                score = 1 - SequenceMatcher(None, 
                    sub_cell.get('source', ''),
                    start_cell.get('source', '')
                ).ratio()
                if score < best_score:
                    best_score = score
                    best_match = (j, start_cell)
        
        if best_match and best_score < 0.3:  # threshold for considering cells similar
            j, start_cell = best_match
            cell_diff["status"] = "unchanged" if best_score < 0.01 else "modified"
            cell_diff["original_source"] = start_cell.get('source', '')
            cell_diff["original_index"] = j
            
        diff_result.append(cell_diff)
    
    return diff_result

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

def display_diff(diff_data, show_outputs=False):
    """Display the diff in a readable format."""
    if "error" in diff_data:
        st.error(diff_data["error"])
        return
    
    for cell in diff_data:
        with st.expander(
            f"Cell {cell['index']} ({cell['cell_type']}) - {cell['status'].upper()}",
            expanded=cell['status'] != 'unchanged'
        ):
            if cell['status'] == 'added':
                st.code(cell['source'], language='python' if cell['cell_type'] == 'code' else None)
            elif cell['status'] == 'modified':
                col1, col2 = st.columns(2)
                with col1:
                    st.write("Original:")
                    st.code(cell['original_source'], language='python' if cell['cell_type'] == 'code' else None)
                with col2:
                    st.write("Modified:")
                    st.code(cell['source'], language='python' if cell['cell_type'] == 'code' else None)
            else:  # unchanged
                st.code(cell['source'], language='python' if cell['cell_type'] == 'code' else None)
            
            if show_outputs and cell['outputs'] and cell['cell_type'] == 'code':
                st.write("Outputs:")
                for output in cell['outputs']:
                    if 'text' in output:
                        st.text(output['text'])
                    elif 'data' in output:
                        if 'image/png' in output['data']:
                            st.image(output['data']['image/png'])
                        elif 'text/plain' in output['data']:
                            st.text(output['data']['text/plain'])

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
