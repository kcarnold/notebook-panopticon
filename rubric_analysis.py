from dataclasses import dataclass
import difflib
import json
from typing import Literal
import streamlit as st
from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel


GENAI_MODEL = 'gemini-2.0-flash'


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


class RubricResponse(BaseModel):
    """A response to a rubric check."""
    item: str
    status: Literal["pass", "not yet", "not applicable"]
    comment: str


def do_rubric_check(rubric, document, document_title):
    prompt = f"""
<document title="{document_title}">
{document}
</document>

<document title="Rubric">
{rubric}
</document>

Check the notebook against the rubric."""

    client = genai_client()
    response = client.models.generate_content(
        model=GENAI_MODEL,
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=list[RubricResponse]
        )
    )

    # try to parse
    try:
        list_of_rubric_responses = json.loads(response.text)
        if not isinstance(list_of_rubric_responses, list):
            raise ValueError("Response is not a list")
        rubric_responses = [RubricResponse.model_validate(item) for item in list_of_rubric_responses]
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
    for rubric_item in rubric_responses:
        emoji = status_to_emoji.get(rubric_item.status, "❓")
        md += f"- {emoji} **{rubric_item.item}**\n"
        if rubric_item.comment:
            md += f"  - {rubric_item.comment}\n"
    st.markdown(md)
        