from dataclasses import dataclass
import difflib
import json
from typing import Literal
import streamlit as st
from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel


#GENAI_MODEL = 'gemini-2.0-flash'
GENAI_MODEL = 'gemini-2.5-flash-preview-04-17'


@dataclass
class Diff:
    src_name: str
    dst_name: str
    diff: str
    n_changed_lines: int


@st.cache_resource
def genai_client():
    """Initialize OpenAI client."""
    return genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"],
    )


class RubricItemResponse(BaseModel):
    """A response to a rubric check."""
    item: str
    status: Literal["pass", "not yet", "not applicable"]
    comment: str

class RubricResponse(BaseModel):
    item_responses: list[RubricItemResponse]
    possible_issues: list[str]
    other_comments: str


def do_rubric_check(rubric, document, document_title):
    prompt = f"""
<document title="{document_title}">
{document}
</document>

<document title="Rubric">
{rubric}
</document>

Check the notebook against the rubric. Also identify any other possible issues or misconceptions.

Only include a comment if the item is not clearly pass, otherwise leave it blank.

Use the other_comments field to point out any other possible issues or things that would benefit from manual review.
"""

    client = genai_client()
    response = client.models.generate_content(
        model=GENAI_MODEL,
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RubricResponse,
            thinking_config=genai_types.ThinkingConfig(
                thinking_budget=1000
            )
        )
    )

    # try to parse
    try:
        if response.text is None:
            raise ValueError("Response is None")
        rubric_check = RubricResponse.model_validate_json(response.text)
    except json.JSONDecodeError as e:
        st.error(f"Error parsing rubric response: {e}")
    except Exception as e:
        st.error(f"Error parsing rubric response: {e}")
        st.write("Raw response:")
        st.code(response.text)
        return

    status_to_emoji = {
        "pass": "✅",
        "not yet": "❌",
        "not applicable": "⏳"
    }
    md = ''
    for rubric_item in rubric_check.item_responses:
        emoji = status_to_emoji.get(rubric_item.status, "❓")
        md += f"- {emoji} **{rubric_item.item}**\n"
        if rubric_item.comment:
            md += f"  - {rubric_item.comment}\n"

    if rubric_check.possible_issues:
        md += "\n### Possible Issues\n"
        for issue in rubric_check.possible_issues:
            md += f"- {issue}\n"
    if rubric_check.other_comments:
        md += f"\n### Other Comments\n{rubric_check.other_comments}\n"
    st.markdown(md)
        