import shutil
from pathlib import Path
import click

COURSES_DIR = Path.home() / "Courses/cs375-376/static/notebooks"
STARTERS_DIR = Path("data/starters")

def find_starter(assignment_name: str) -> Path | None:
    """Find a starter notebook matching the assignment name."""
    # Look for exact match with .ipynb extension
    target = COURSES_DIR / f"{assignment_name}.ipynb"
    if target.exists():
        return target
    return None

@click.command()
@click.argument('assignments_dir', type=click.Path(exists=True), default="data/submissions")
def copy_starters(assignments_dir):
    """Find and copy starter notebooks for all assignments in submissions directory."""
    assignments_path = Path(assignments_dir)
    STARTERS_DIR.mkdir(parents=True, exist_ok=True)

    # Get list of assignment names from submissions directory
    assignments = [d.name for d in assignments_path.iterdir() if d.is_dir()]

    for assignment in assignments:
        print(f"Looking for starter for {assignment}...")
        starter = find_starter(assignment)

        if starter:
            dest = STARTERS_DIR / f"{assignment}.ipynb"
            if not dest.exists():
                print(f"Copying {starter} to {dest}")
                shutil.copy2(starter, dest)
            else:
                print(f"Starter already exists at {dest}")
        else:
            print(f"No starter found for {assignment}")

if __name__ == '__main__':
    copy_starters()
