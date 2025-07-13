"""Chemistry-focused DSPy extensions for structured reasoning and output formatting.

This module provides enhanced DSPy components specifically tailored for chemistry education
and chemical reasoning tasks in the Chemezy application.
"""

import json
import textwrap
import re
from typing import get_args, get_origin

import dspy
from dspy import ensure_signature, make_signature
from pydantic import TypeAdapter

# Pattern for extracting field headers from chemistry-related content
field_header_pattern = re.compile(r'\[\[ ## (\w+) ## \]\]')


class ChemistryLLMException(Exception):
    """Exception raised when chemistry LLM operations fail."""
    def __init__(self, message: str, details: str = None):
        super().__init__(message)
        self.details = details

    def __str__(self):
        return f"{self.args[0]}: {self.details}" if self.details else str(self.args[0])


def format_chemical_name(name: str, delimiter: str = '_') -> str:
    """Format chemical names for use in identifiers."""
    return re.sub(r'[\W_]+', delimiter, name.encode('ascii', errors='ignore').decode()).strip(delimiter).lower()


class ChemistryReasoningModule(dspy.Module):
    def __init__(self, signature, rationale_type=None, cot=True, activated=True, 
                 reflect=False, feedback_fn=None, feedback_retries=2, **config):
        super().__init__()

        self.activated = activated
        self.reflect = reflect
        self.cot = cot
        self.feedback_fn = feedback_fn
        self.feedback_retries = feedback_retries
        self.signature = signature = ensure_signature(signature)
        *_, last_key = signature.output_fields.keys()

        prefix = "Reasoning: Let's think step by step in order to"

        if isinstance(dspy.settings.lm, dspy.LM):
            desc = "${reasoning}"
        elif hasattr(dspy.settings, "experimental") and dspy.settings.experimental:
            desc = "${produce the output fields}. We ..."
        else:
            desc = f"${{produce the {last_key}}}. We ..."

        rationale_type = rationale_type or dspy.OutputField(
            prefix=prefix, desc=desc)

        if self.cot:
            extended_signature = signature.prepend(
                "reasoning", rationale_type, type_=str)
        else:
            extended_signature = signature

        extended_signature = make_signature(
            extended_signature.model_fields, extended_signature.instructions, signature_name=signature.__name__)
        self._predict = dspy.Predict(extended_signature, **config)
        self._predict.extended_signature = extended_signature

    def forward(self, **kwargs):
        assert self.activated in [True, False]

        signature = kwargs.pop(
            "new_signature", self._predict.extended_signature if self.activated else self.signature)
        prediction = self._predict(signature=signature, **kwargs)
        if self.feedback_fn and self.feedback_retries > 0:
            reflect, feedback_message = self.feedback_fn(prediction)
            self.feedback_retries -= 1
            if reflect:
                instructions = textwrap.dedent(f"""Given feedback below, please review your above response and fix the issues.\n<feedback>\n{
                                               feedback_message}\n</feedback>\n\nWrite your response in StructuredOutput.reasoning field. Always respond in single line without wrapping inside ```json or ```.""")
                kwargs['reflect'] = self._prepare_chemistry_reflection(
                    signature, prediction, instructions)
                self.pred_reasoning = prediction.reasoning
                return self.forward(new_signature=signature, **kwargs)

        if self.reflect:
            instructions = textwrap.dedent(
                f"""Please review your response and provide a detailed critique, and fix issues.
                    Always respond with complete content as per OUTPUT_SCHEMA in a valid json format.
                """)
            self.reflect = False
            kwargs['reflect'] = self._prepare_chemistry_reflection(
                signature, prediction, instructions)
            return self.forward(new_signature=signature, **kwargs)

        return prediction

    def _prepare_chemistry_reflection(self, signature, prediction, instructions: str = None):
        return {
            'assistant': json.dumps({
                k: TypeAdapter(signature.output_fields[k].annotation).dump_python(
                    getattr(prediction, k))
                for k in signature.output_fields.keys()
            }),
            'user': instructions or 'Please review your response and provide a detailed critique, and fix issues.'
        }

    @property
    def demos(self):
        return self._predict.demos

    @property
    def extended_signature(self):
        return self._predict.extended_signature

    def make_chemistry_turns(self, signature: dspy.Signature, prediction: dspy.Prediction, **kwargs):
        response = {k: getattr(prediction, k)
                    for k in signature.output_fields.keys()}
        # extract inputs from **kwargs based on signature.input_fields
        inputs = {k: kwargs[k] for k in signature.input_fields.keys()}
        return [{'user': inputs, 'assistant': response}]


# ChemistryOutputAdapter class removed - was not being used in the codebase


def format_chemistry_content(content: str) -> str:
    """Format chemistry content for display in structured format."""
    if '\n' not in content and "«" not in content and "»" not in content:
        return f"«{content}»"

    modified_content = content.replace('\n', '\n    ')
    return f"«««\n    {modified_content}\n»»»"


def format_chemistry_list(items: list) -> str:
    """Format a list of chemistry-related items for display."""
    if len(items) == 0:
        return "N/A"
    if len(items) == 1:
        return format_chemistry_content(items[0])

    return "\n".join([f"[{idx+1}] {format_chemistry_content(txt)}" for idx, txt in enumerate(items)])


def format_chemistry_fields(fields: dict) -> str:
    """Format chemistry fields into structured XML format."""
    xml_structure = ""
    for k, v in fields.items():
        v = v if not isinstance(v, list) else format_chemistry_list(v)
        xml_structure += f"\n<{k}>\n{v}\n</{k}>\n\n"

    return xml_structure.strip()


def parse_chemistry_value(value, annotation):
    """Parse and validate chemistry-related values according to their type annotation."""
    if annotation is str:
        return str(value)
    parsed_value = value
    if isinstance(annotation, dict):
        validated_dict = {}
        for key, value_type in annotation.items():
            if key in parsed_value:
                if isinstance(parsed_value[key], dict) and hasattr(value_type, '__annotations__'):
                    # Handle nested structured output
                    validated_dict[key] = TypeAdapter(
                        value_type).validate_python(parsed_value[key])
                else:
                    validated_dict[key] = TypeAdapter(
                        value_type).validate_python(parsed_value[key])
        return validated_dict
    return TypeAdapter(annotation).validate_python(parsed_value)


def format_chemistry_turn(signature, values, role, incomplete=False):
    """Format a conversation turn for chemistry reasoning tasks."""
    content = []

    if role == "user":
        field_names = signature.input_fields.keys()
        if incomplete:
            content.append(
                "This is an example of the task, though some input or output fields are not supplied.")
    else:
        field_names, values = list(signature.output_fields.keys(
        )) + ['completed'], {**values, 'completed': ''}

    if not incomplete:
        if not set(values).issuperset(set(field_names)):
            raise ValueError(f"Expected {field_names} but got {values.keys()}")

    content.append(format_chemistry_fields({k: values.get(
        k, "Not supplied for this particular example.") for k in field_names}))

    if role == "user":
        content.append(
            "Your response should be a valid JSON of type StructuredOutput")

    return {"role": role, "content": '\n\n'.join(content).strip()}


def add_chemistry_reflection(messages: list, reflect: dict) -> None:
    """Add reflection messages for chemistry reasoning improvement."""
    messages.append({"role": "assistant", "content": reflect['assistant']})
    messages.append({"role": "user", "content": reflect['user']})


def get_chemistry_annotation_name(annotation) -> str:
    """Get a readable name for a chemistry-related type annotation."""
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is None:
        if hasattr(annotation, '__name__'):
            return annotation.__name__
        else:
            return str(annotation)
    else:
        args_str = ', '.join(get_chemistry_annotation_name(arg) for arg in args)
        return f"{origin.__name__}[{args_str}]"


def enumerate_chemistry_fields(fields: dict) -> str:
    """Enumerate chemistry fields with their types and descriptions."""
    xml_structure = ""
    for idx, (k, v) in enumerate(fields.items()):
        xml_structure += f"\n<{k} id='{idx + 1}' type='{get_chemistry_annotation_name(v.annotation)}'>{v.json_schema_extra['desc']}</{k}>\n\n"
    return xml_structure.strip()


# enumerate_json_schema_fields function removed - was not being used in the codebase


def prepare_chemistry_instructions(signature, output_schema=None) -> str:
    """Prepare instructions for chemistry reasoning tasks."""
    parts = []
    input_fields = "You will be working with the following INPUTS:\n" + \
        "<INPUTS>\n" + \
        enumerate_chemistry_fields(signature.input_fields) + "\n</INPUTS>\n\n"

    instructions = textwrap.dedent(signature.instructions.strip())
    objective = "\n".join([""] + instructions.splitlines())

    if ':prompt_inputs' in objective:
        objective = objective.replace(":prompt_inputs", input_fields)
    else:
        objective += f"\n\n{input_fields}"

    parts.append(objective)

    if output_schema:
        parts.append("You will be working with the following OUTPUT_SCHEMA:\n" +
                     "<OUTPUT_SCHEMA>\n" + json.dumps(output_schema, indent=2) + "\n</OUTPUT_SCHEMA>\n\n")
        parts.append("Your response should be a valid JSON of type StructuredOutput in single line without wrapping inside ```json or ```.\nIt should be valid for json.loads")

    return '\n\n'.join(parts).strip()


# Direct export of ChemistryReasoningModule for chemistry-focused DSPy operations
TypedCOTPredict = ChemistryReasoningModule  # Legacy alias for any remaining compatibility needs
