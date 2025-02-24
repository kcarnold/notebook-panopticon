# Notebook Diff Viewer Application Specification

## Project Overview

This application allows an instructor to quickly review student Jupyter notebook submissions by comparing them to starter notebooks. The system finds the most likely starter notebook for each submission (based on minimal diff size) and displays the differences, focusing on code and markdown changes while optionally showing cell outputs.

### Key Features
- Compare student notebook submissions with original starter notebooks
- Navigate between students and assignments quickly
- View diffs that highlight changes in code and markdown
- Option to view/hide cell outputs
- Local deployment with no authentication required

## Requirements

### Functional Requirements
- Process ZIP files containing student notebook submissions
- Match each submission to the most appropriate starter notebook
- Generate and display diffs between starter and submission notebooks
- Navigate between students and assignments efficiently
- Cache processed diffs for quick retrieval
- Focus primarily on code and markdown changes
- Optionally display cell outputs

### Non-Functional Requirements
- Performance: System should handle ~30 students and ~24 assignments efficiently
- Local deployment only
- No authentication required
- All data fits in memory (even large notebooks with images up to a few MB)

## Architecture

### High-Level Components
1. **Data Preprocessor**: Extracts and organizes notebooks from ZIP files
2. **Notebook Matcher**: Identifies the most appropriate starter notebook for each submission
3. **Diff Generator**: Computes differences between starter and submission notebooks
4. **Web Interface**: Streamlit application with navigation and diff display capabilities

### Directory Structure
```
app_root/
├── data/
│   ├── submissions/
│   │   ├── assignment1/
│   │   │   ├── student1.ipynb
│   │   │   ├── student2.ipynb
│   │   │   └── ...
│   │   └── ...
│   └── starters/
│       ├── assignment1.ipynb
│       ├── assignment1_v2.ipynb
│       └── ...
├── cache/
│   └── diffs/
├── app.py
└── utils/
    ├── diff_engine.py
    ├── notebook_parser.py
    ├── indexer.py
    └── ui_components.py
```

## Data Flow

1. Preprocessing:
   - ZIP files are extracted and organized by assignment/student
   - Starter notebooks are identified and cataloged
   - Index is built to map submissions to potential starters

2. Runtime:
   - User selects assignment and student via dropdowns
   - System retrieves or computes diff between submission and best-matching starter
   - Diff is displayed in the UI
   - User can navigate to next/previous/random student or assignment

## UI/UX Design

### Main Interface
- **Header**: Application title and controls
- **Navigation Section**:
  - Dropdown for selecting assignment
  - Dropdown for selecting student
  - Navigation buttons: Previous/Next/Random for both assignment and student
- **Diff Viewer Section**:
  - Toggle for showing/hiding outputs
  - Diff display with syntax highlighting
  - Cell-by-cell comparison with added/removed/modified highlighting

### Navigation Controls
```
+-----------------------------------------------------------------------------------+
| Notebook Diff Viewer                                                              |
+-----------------------------------------------------------------------------------+
| Assignment: [Dropdown▼]  << Prev | Next >> | Random |                             |
| Student:    [Dropdown▼]  << Prev | Next >> | Random |                             |
+-----------------------------------------------------------------------------------+
| Show Outputs: [ ] | Show Only Changes: [x]                                        |
+-----------------------------------------------------------------------------------+
|                                                                                   |
| [Diff Viewer Content]                                                             |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

## Implementation Phases

### Phase 1: Core Infrastructure & Simple Viewer
- Set up project structure
- Implement notebook parsing and basic matching algorithm
- Create simple UI with dropdowns for navigation
- Basic diff display using existing libraries
- Validate approach with a small set of notebooks

### Phase 2: Enhanced Matching & Diff Display
- Implement advanced matching algorithm to find best starter notebook
- Improve diff visualization with syntax highlighting
- Add caching mechanism for better performance
- Implement navigation buttons (prev/next/random)

### Phase 3: Refinements & Optimizations
- Add configuration options (e.g., toggle cell outputs)
- Optimize loading and processing time
- Enhance UI/UX with improved styling
- Add search/filter capabilities if needed
- Add optional statistics about submissions

## Technical Details

### Notebook Matching Algorithm
```python
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
```

### Diff Generation
```python
@st.cache_data
def compute_notebook_diff(submission_notebook, starter_notebook):
    """Compute cell-by-cell differences between notebooks."""
    diff_result = []
    
    # For each cell in submission, find matching cell in starter
    # and compute diff
    
    return diff_result
```

### Streamlit Application Structure
```python
def main():
    st.title("Notebook Diff Viewer")
    
    # Load data
    assignments = get_assignments()
    
    # Navigation controls
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("Assignment")
        selected_assignment = st.selectbox("Select Assignment", assignments)
        cols = st.columns(3)
        with cols[0]:
            st.button("⬅️ Prev", on_click=lambda: navigate_assignment("prev"))
        with cols[1]:
            st.button("Next ➡️", on_click=lambda: navigate_assignment("next"))
        with cols[2]:
            st.button("🔀 Random", on_click=lambda: navigate_assignment("random"))
    
    with col2:
        st.write("Student")
        students = get_students(selected_assignment)
        selected_student = st.selectbox("Select Student", students)
        cols = st.columns(3)
        with cols[0]:
            st.button("⬅️ Prev", on_click=lambda: navigate_student("prev"))
        with cols[1]:
            st.button("Next ➡️", on_click=lambda: navigate_student("next"))
        with cols[2]:
            st.button("🔀 Random", on_click=lambda: navigate_student("random"))
    
    # Display options
    show_outputs = st.checkbox("Show Cell Outputs", value=False)
    
    # Get and display diff
    diff_data = get_cached_diff(selected_student, selected_assignment)
    display_diff(diff_data, show_outputs=show_outputs)
```

## Libraries and Dependencies

- **Streamlit**: Web application framework
- **nbformat**: For parsing and working with Jupyter notebooks
- **difflib**: For text comparison (or custom diff implementation)
- **Custom HTML/JS**: For enhanced diff visualization
- **Python 3.7+**: Required for typing and other modern features

## Open Questions & Considerations

1. **Starter Notebook Identification**:
   - How will starter notebooks be named/organized?
   - Will there be multiple versions of starter notebooks for each assignment?
   - Should we implement version detection for starter notebooks?

2. **Diff Visualization**:
   - What's the preferred format for displaying diffs? Side-by-side or inline?
   - How should we handle large diffs or notebooks with many cells?
   - Should we offer collapsible sections for unchanged parts?

3. **Performance Considerations**:
   - Will caching be sufficient or do we need more sophisticated optimizations?
   - Should preprocessing be done upfront or on-demand?

4. **UI Enhancements**:
   - Would filtering capabilities (e.g., show only modified cells) be useful?
   - Is there a need for search functionality across notebooks?
   - Would showing statistics about student modifications be valuable?

## Future Enhancements

1. Export functionality for annotations or feedback
2. Integration with grading systems
3. Batch processing capabilities
4. Search across all notebooks for specific patterns
5. Analytics on common modifications or errors
