import json
import textwrap
import re
from typing import get_args, get_origin

import dspy
from dspy import ensure_signature, make_signature
from pydantic import BaseModel, TypeAdapter
from openai.lib._pydantic import to_strict_json_schema

field_header_pattern = re.compile(r'\[\[ ## (\w+) ## \]\]')


class LLMResponseDecoderException(Exception):
    def __init__(self):
        super().__init__()  # Add this line to properly initialize the parent class

    def __str__(self):
        return f"{self.args[0]}: {self.details}"


def slugify(string, delimiter='_'):
    return re.sub(r'[\W_]+', delimiter, string.encode('ascii', errors='ignore').decode()).strip(delimiter).lower()


class TypedCOTPredict(dspy.Module):
    def __init__(self, signature, rationale_type=None, cot=True, activated=True, reflect=False, feedback_fn=None, feedback_retries=2, **config):
        super().__init__()

        self.activated = activated
        self.reflect = reflect
        self.cot = cot
        self.feedback_fn = feedback_fn
        self.feedback_retries = feedback_retries
        self.signature = signature = ensure_signature(signature)
        *_keys, last_key = signature.output_fields.keys()

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
                kwargs['reflect'] = self._prepare_reflection(
                    signature, prediction, instructions)
                self.pred_reasoning = prediction.reasoning
                return self.forward(new_signature=signature, **kwargs)

        if self.reflect:
            instructions = textwrap.dedent(
                f"""Please review your response and provide a detailed critique, and fix issues.
                    Always respond with complete content as per OUTPUT_SCHEMA in a valid json format.
                """)
            self.reflect = False
            kwargs['reflect'] = self._prepare_reflection(
                signature, prediction, instructions)
            return self.forward(new_signature=signature, **kwargs)

        return prediction

    def _prepare_reflection(self, signature, prediction, instructions: str = None):
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

    def make_turns(self, signature: dspy.Signature, prediction: dspy.Prediction, **kwargs):
        response = {k: getattr(prediction, k)
                    for k in signature.output_fields.keys()}
        # extract inputs from **kwargs based on signature.input_fields
        inputs = {k: kwargs[k] for k in signature.input_fields.keys()}
        return [{'user': inputs, 'assistant': response}]


class StructuredOutputAdapter(dspy.ChatAdapter):
    def __call__(self, lm, lm_kwargs, signature, demos, inputs, _parse_values=True):
        reflect = None
        if 'reflect' in inputs:
            reflect = inputs['reflect']

        StructuredOutput = self.signature_to_structured_output_model(signature)
        schema = to_strict_json_schema(StructuredOutput)
        model_name = StructuredOutput.__name__
        if 'openai' in lm.model and 'o1' not in lm.model:
            lm_kwargs['response_format'] = {
                "type": "json_schema",
                "json_schema": {
                    "schema": schema,
                    "name": model_name,
                    "strict": True,
                }
            }
            inputs = self.format(signature, demos, inputs)
        else:
            inputs = self.format(signature, demos, inputs,
                                 output_schema=schema)

        if reflect:
            add_reflect_messages(inputs, reflect)
        inputs = dict(prompt=inputs) if isinstance(
            inputs, str) else dict(messages=inputs)
        outputs = lm(**inputs, **lm_kwargs)
        try:
            results = []
            for output in outputs:
                results.append(self.parse(signature, output))
            return results
        except Exception as e:
            raise e

    def signature_to_structured_output_model(self, signature):
        annotations = {}
        for k, v in signature.output_fields.items():
            if isinstance(v.annotation, type):
                annotations[k] = v.annotation
            else:
                annotations[k] = str
        return type('StructuredOutput', (BaseModel,), {'__annotations__': annotations})

    def format(self, signature, demos, inputs, output_schema=None):
        messages = []
        is_anthropic = 'anthropic' in dspy.settings.lm.model

        # Add system message with instructions
        system_content = prepare_instructions(signature, output_schema)
        system_content = (
            [{'type': 'text', 'text': system_content, 'cache_control': {
                'type': 'ephemeral'}}] if is_anthropic else system_content
        )
        messages.append({"role": "system", "content": system_content})

        # Format chat history
        for item in inputs.get('history', []):
            role = "user" if "user" in item else "assistant"
            message_text = item.get('user') or item.get('assistant')
            if item.get('cache', False) and is_anthropic:
                content = [{
                    'type': 'text',
                    'text': message_text,
                    'cache_control': {'type': 'ephemeral'}
                }]
            else:
                content = message_text

            messages.append({"role": role, "content": content})

        # Process and format demos
        incomplete_demos = [
            demo for demo in demos
            if not all(k in demo for k in signature.fields)
            and any(k in demo for k in signature.input_fields)
            and any(k in demo for k in signature.output_fields)
        ]
        complete_demos = [
            demo for demo in demos if demo not in incomplete_demos]

        # Add demo messages in order (incomplete then complete)
        for demo in incomplete_demos + complete_demos:
            is_incomplete = demo in incomplete_demos
            messages.append(format_turn(signature, demo,
                            role="user", incomplete=is_incomplete))
            messages.append(format_turn(signature, demo,
                            role="assistant", incomplete=is_incomplete))

        # Add final user input
        messages.append(format_turn(signature, inputs, role="user"))

        return messages

    def parse(self, signature, completion):
        completion = json.loads(completion)
        StructuredOutput = self.signature_to_structured_output_model(signature)
        return parse_value(completion, StructuredOutput.__annotations__)


def format_blob(blob):
    if '\n' not in blob and "«" not in blob and "»" not in blob:
        return f"«{blob}»"

    modified_blob = blob.replace('\n', '\n    ')
    return f"«««\n    {modified_blob}\n»»»"


def format_list(items):
    if len(items) == 0:
        return "N/A"
    if len(items) == 1:
        return format_blob(items[0])

    return "\n".join([f"[{idx+1}] {format_blob(txt)}" for idx, txt in enumerate(items)])


def format_fields(fields):
    xml_structure = ""
    for k, v in fields.items():
        v = v if not isinstance(v, list) else format_list(v)
        xml_structure += f"\n<{k}>\n{v}\n</{k}>\n\n"

    return xml_structure.strip()


def parse_value(value, annotation):
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


def format_turn(signature, values, role, incomplete=False):
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

    content.append(format_fields({k: values.get(
        k, "Not supplied for this particular example.") for k in field_names}))

    if role == "user":
        content.append(
            "Your response should be a valid JSON of type StructuredOutput")

    return {"role": role, "content": '\n\n'.join(content).strip()}


def add_reflect_messages(messages, reflect):
    messages.append({"role": "assistant", "content": reflect['assistant']})
    messages.append({"role": "user", "content": reflect['user']})


def get_annotation_name(annotation):
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is None:
        if hasattr(annotation, '__name__'):
            return annotation.__name__
        else:
            return str(annotation)
    else:
        args_str = ', '.join(get_annotation_name(arg) for arg in args)
        return f"{origin.__name__}[{args_str}]"


def enumerate_fields(fields):
    xml_structure = ""
    for idx, (k, v) in enumerate(fields.items()):
        xml_structure += f"\n<{k} id='{idx + 1}' type='{get_annotation_name(v.annotation)}'>{v.json_schema_extra['desc']}</{k}>\n\n"
    return xml_structure.strip()


def enumerate_json_schema_fields(fields):
    xml_structure = ""
    for idx, (k, v) in enumerate(fields.items()):
        xml_structure += f"\n<{k} id='{idx + 1}'>\n{v.annotation.dump_json_schema()}\n</{k}>\n\n"
    return xml_structure.strip()


def prepare_instructions(signature, output_schema=None):
    parts = []
    input_fields = "You will be working with the following INPUTS:\n" + \
        "<INPUTS>\n" + \
        enumerate_fields(signature.input_fields) + "\n</INPUTS>\n\n"

    instructions = textwrap.dedent(signature.instructions.strip())
    objective = "\n".join([""] + instructions.splitlines())

    if ':prompt_inputs' in objective:
        objective = objective.replace(":prompt_inputs", input_fields)
    else:
        objective += f"\n\n{input_fields}"

    parts.append(objective)

    # parts.append("Breakdown your objective reasoning with citations from INPUTS into following sections: **Key Points**, **Critical Thinking & Observations**")

    if output_schema:
        parts.append("You will be working with the following OUTPUT_SCHEMA:\n" +
                     "<OUTPUT_SCHEMA>\n" + json.dumps(output_schema, indent=2) + "\n</OUTPUT_SCHEMA>\n\n")
        parts.append("Your response should be a valid JSON of type StructuredOutput in single line without wrapping inside ```json or ```.\nIt should be valid for json.loads")

    return '\n\n'.join(parts).strip()


dspy.TypedCOTPredict = TypedCOTPredict
