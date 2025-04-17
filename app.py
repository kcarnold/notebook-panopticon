from difflib import SequenceMatcher
import io
import streamlit as st
import streamlit.components.v1 as components
import nbformat
from pathlib import Path
import random

st.set_page_config(layout="wide")


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

#@st.cache_data
def get_submission_and_starter(student, assignment):
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
    
    return submission, starter

def notebook_to_quarto(nb):
    """Convert notebook to Quarto markdown format."""
    chunks = []
    for cell in nb.cells:
        if cell.cell_type == 'markdown':
            chunks.append(cell.source)
        elif cell.cell_type == 'code':
            chunks.append(f"```{{python}}\n{cell.source}\n```")
    return '\n\n'.join(chunks)

def generate_diff_html(a, b):
    """Generate HTML for a side-by-side diff between two texts."""
    s = SequenceMatcher(None, a.splitlines(), b.splitlines())
    a_lines = a.splitlines()
    b_lines = b.splitlines()
    context_lines = 3
    
    def format_chunk(lines, start, end):
        if not lines[start:end]:
            return ""
        chunk = "\n".join(lines[start:end])
        # Escape HTML characters
        chunk = chunk.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return chunk
    
    def format_lines(lines, cls=''):
        if not lines:
            return ""
        lines_html = [f'<div class="line">{line}</div>' for line in lines.split('\n')]
        return f'<div class="{cls}">' + ''.join(lines_html) + '</div>'
    
    rows = []
    last_i2 = last_j2 = 0
    
    for tag, i1, i2, j1, j2 in s.get_opcodes():
        # Determine context boundaries
        i_start = max(i1 - context_lines, last_i2)
        j_start = max(j1 - context_lines, last_j2)
        
        # Add ellipsis if there's a gap
        if i_start > last_i2 or j_start > last_j2:
            rows.append((
                '<div class="ellipsis">...</div>',
                '<div class="ellipsis">...</div>'
            ))
        
        # Add context before
        context_left = format_chunk(a_lines, i_start, i1)
        context_right = format_chunk(b_lines, j_start, j1)
        if context_left or context_right:
            rows.append((format_lines(context_left), format_lines(context_right)))
        
        # Add changed content with padding
        if tag == 'replace':
            left_chunk = format_chunk(a_lines, i1, i2)
            right_chunk = format_chunk(b_lines, j1, j2)
            left_lines = left_chunk.split('\n')
            right_lines = right_chunk.split('\n')
            # Pad the shorter side with blank lines
            max_lines = max(len(left_lines), len(right_lines))
            left_lines += [''] * (max_lines - len(left_lines))
            right_lines += [''] * (max_lines - len(right_lines))
            rows.append((
                format_lines('\n'.join(left_lines), 'diff-delete'),
                format_lines('\n'.join(right_lines), 'diff-insert')
            ))
        elif tag == 'delete':
            left_chunk = format_chunk(a_lines, i1, i2)
            blank_lines = [''] * len(left_chunk.split('\n'))
            rows.append((
                format_lines(left_chunk, 'diff-delete'),
                format_lines('\n'.join(blank_lines))
            ))
        elif tag == 'insert':
            right_chunk = format_chunk(b_lines, j1, j2)
            blank_lines = [''] * len(right_chunk.split('\n'))
            rows.append((
                format_lines('\n'.join(blank_lines)),
                format_lines(right_chunk, 'diff-insert')
            ))
        elif tag == 'equal':
            rows.append((
                format_lines(format_chunk(a_lines, i1, i2)),
                format_lines(format_chunk(b_lines, j1, j2))
            ))
        
        last_i2 = i2
        last_j2 = j2
    
    custom_css = """
        .diff-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
            font-size: 14px;
            font-family: monospace;
        }
        .diff-pane {
            border: 1px solid #ddd;
            padding: 1rem;
            white-space: pre;
            overflow-x: auto;
        }
        .line {
            min-height: 1.2em;
            white-space: pre;
            overflow-x: visible;
        }
        .diff-delete { background-color: #ffe6e6; }
        .diff-insert { background-color: #e6ffe6; }
        .ellipsis {
            text-align: center;
            color: #666;
            padding: 0.2em;
            background: #f0f0f0;
        }
    """
    
    return f"""
    <style>{custom_css}</style>
    <div class="diff-container">
        <div class="diff-pane">
            <h3>Starter</h3>
            {''.join(left for left, _ in rows)}
        </div>
        <div class="diff-pane">
            <h3>Submission</h3>
            {''.join(right for _, right in rows)}
        </div>
    </div>
    """

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
        .diff-container { font-size: 10px; font-family: monospace; white-space: pre-line; overflow-x: auto; }
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
    unified_view = st.checkbox("Unified Diff View", value=False)
    
    # Get and display diff
    submission, starter = get_submission_and_starter(selected_student, selected_assignment)
    submission_quarto = notebook_to_quarto(submission)
    starter_quarto = notebook_to_quarto(starter)
    if unified_view:
        diff_html = generate_unified_diff_html(starter_quarto, submission_quarto)
    else:
        diff_html = generate_diff_html(starter_quarto, submission_quarto)

    height = 800
    components.html(diff_html, height=height, scrolling=True)


main()
