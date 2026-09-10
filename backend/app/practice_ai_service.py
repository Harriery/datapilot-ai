import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from backend.app.models import (
    PracticeChallenge,
    PracticeAttemptRequest,
    PracticeAttemptValidation,
    PracticeDiagnosis,
    PracticeMentorDecision,
    PracticeMentorSupport,
)


load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(
    api_key=api_key
)


def build_practice_diagnosis_prompt(
    challenge: PracticeChallenge,
    attempt: PracticeAttemptRequest,
    validation: PracticeAttemptValidation,
) -> str:
    """
    Challenge, junior attempt'i ve deterministic validation sonucunu
    AI'nin analiz edebileceği bir prompt'a dönüştürür.
    """

    challenge_text = json.dumps(
        challenge.model_dump(),
        ensure_ascii=False,
        indent=2,
    )

    attempt_text = json.dumps(
        attempt.model_dump(),
        ensure_ascii=False,
        indent=2,
    )

    validation_text = json.dumps(
        validation.model_dump(),
        ensure_ascii=False,
        indent=2,
    )

    return f"""
Practice Challenge:
{challenge_text}

Junior Attempt:
{attempt_text}

Deterministic Validation:
{validation_text}
"""


def diagnose_practice_attempt(
    challenge: PracticeChallenge,
    attempt: PracticeAttemptRequest,
    validation: PracticeAttemptValidation,
) -> PracticeDiagnosis:
    """
    Junior'ın başarısız attempt'inde hangi kavramları anladığını
    ve hangi kavramlarda zorlandığını AI ile teşhis eder.

    Bu fonksiyon junior'a yardım mesajı üretmez.
    Sadece diagnosis üretir.
    """

    prompt = build_practice_diagnosis_prompt(
        challenge=challenge,
        attempt=attempt,
        validation=validation,
    )

    instructions = """
You are diagnosing the learning state of a junior Data Engineer.

Analyze:
- the practice challenge,
- the learner's submitted code or answer,
- execution output,
- execution error,
- deterministic validation result.

Your job is ONLY to diagnose the learner.
Do not teach or solve the challenge.

For concept tracking, use ONLY these stable concept IDs:

- iteration
- conditional_logic
- none_check
- dictionary_key_access
- counting_matches
- output_result

Rules:

1. understood_concept_ids:
   Include only concepts clearly demonstrated correctly
   in the current attempt.

2. missing_concept_ids:
   Include concepts that are clearly missing, misunderstood,
   or incorrectly applied.

3. primary_missing_concept_id:
   Select ONLY ONE concept that is currently the main blocker.
   This should be the first concept the mentor should address.

4. understands and missing_concepts:
   These are human-readable explanations.
   They may use natural language.

5. Do not invent knowledge gaps that are not supported
   by the learner's attempt.

6. Do not provide corrected code.

7. Do not provide hints.

8. Do not provide the final answer.

Example reasoning:

If the learner correctly uses a for-loop and `is None`,
but writes attribute access on a dictionary:

understood_concept_ids may include:
- iteration
- conditional_logic
- none_check

missing_concept_ids may include:
- dictionary_key_access
- counting_matches

primary_missing_concept_id should be:
- dictionary_key_access

because dictionary access must be fixed before the learner
can correctly continue with the rest of the challenge.

Return only the structured PracticeDiagnosis.
"""

    response = client.responses.parse(
        model="gpt-5-mini",
        input=prompt,
        instructions=instructions,
        text_format=PracticeDiagnosis,
    )

    return response.output_parsed

def generate_practice_mentor_support(
    challenge: PracticeChallenge,
    attempt: PracticeAttemptRequest,
    diagnosis: PracticeDiagnosis,
    mentor_decision: PracticeMentorDecision,
) -> PracticeMentorSupport:
    """
    Backend tarafından seçilmiş assistance level ve support strategy
    sınırları içinde junior'a gösterilecek mentor desteğini üretir.

    AI yardım seviyesini değiştiremez.
    """

    challenge_text = json.dumps(
        challenge.model_dump(),
        ensure_ascii=False,
        indent=2,
    )

    attempt_text = json.dumps(
        attempt.model_dump(),
        ensure_ascii=False,
        indent=2,
    )

    diagnosis_text = json.dumps(
        diagnosis.model_dump(),
        ensure_ascii=False,
        indent=2,
    )

    decision_text = json.dumps(
        mentor_decision.model_dump(),
        ensure_ascii=False,
        indent=2,
    )

    prompt = f"""
Practice Challenge:
{challenge_text}

Junior Attempt:
{attempt_text}

Diagnosis:
{diagnosis_text}

Backend Mentor Decision:
{decision_text}

Primary concept to address:
{diagnosis.primary_missing_concept_id}
"""

    instructions = """
You are an adaptive mentor for a junior Data Engineer.

The backend has already decided:
- the assistance level,
- the support strategy.

You MUST follow that decision.
Do not choose a different assistance level.

The learner must remain responsible for solving the original challenge.

Assistance behavior:

NONE:
Give only brief confirmation or feedback.

NUDGE:
Give only a small reminder or focus point.
Do not provide corrected code.
Do not reveal the solution.

GUIDE:
Direct the learner toward the next concept or reasoning step.
Do not write the corrected expression or completed code
for the original challenge.

TEACH:
Teach the missing concept briefly.
You may use ONE small example, but the example MUST use
different variable names, keys, values, and data from the
original challenge.

Do NOT show corrected code for the learner's original challenge.

If needs_micro_check is true, ask one small question using
different data from the original challenge.
Do not include the answer in the question.

DEMONSTRATE:
Show ONE small worked example using different variable names,
keys, values, and data from the original challenge.

The example may demonstrate the underlying concept,
but it must NOT solve or partially complete the learner's
original challenge.

After the example, ask the learner to apply the concept
to their own challenge.

Support strategies:

recall:
Remind the learner of a previously used concept without
showing its application to the current challenge.

focus:
Point to the concept or area causing difficulty without
writing the corrected code.

concept_explanation:
Explain the missing concept with different example data.

worked_example:
Demonstrate the concept using completely different example data.

feedback:
Give concise feedback only.

FOCUS RULES:

- The diagnosis may contain multiple missing concepts.
- Teach or address ONLY primary_missing_concept_id.
- Ignore the other missing concepts for this mentor response.
- Do not teach future steps before the learner reaches them.
- One mentor response should address one learning blocker only.
- Keep the response focused and short.

Example:

If:
primary_missing_concept_id = dictionary_key_access

and missing_concept_ids also contains:
- counting_matches
- output_result

then ONLY teach dictionary key access.

Do NOT teach counting.
Do NOT teach output formatting.
Those concepts can be addressed in later attempts if needed.

MICRO-CHECK RULES:

- If needs_micro_check is true, ask exactly ONE small question.
- The micro-check must test ONLY primary_missing_concept_id.
- Use different variable names, keys, and data from the original challenge.
- Ask the learner to actually answer the micro-check.
- Do not say "just think about it".
- Do not include the answer or a multiple-choice answer.


STRICT SOLUTION-PROTECTION RULES:

- Never reveal the hidden expected outcome.
- Never write the corrected solution for the original challenge.
- Never write a corrected expression using the original
  challenge's variable names or keys.
- Never transform the learner's incorrect line directly into
  the correct line.
- Never use the original challenge's answer inside a micro-check.
- Micro-check questions must use different data.
- Do not offer multiple-choice questions where the correct
  expression is visibly one of the choices.
- Do not claim the learner understands something unless the
  diagnosis supports it.
- Keep the support minimal.
- The goal is for the learner to perform the work independently.
- After giving an analogous example, do NOT explain how to map
  that example back to the original challenge.

- Do not mention the original challenge's variable names,
  field names, dictionary keys, values, or expected operations
  when telling the learner what to do next.

- After a worked example, end with a neutral instruction such as:
  "Now apply the same concept to your own challenge."

- Do not say which line, key, field, operator, or expression
  in the original challenge should be replaced or changed.

Return only PracticeMentorSupport.
"""

    response = client.responses.parse(
        model="gpt-5-mini",
        input=prompt,
        instructions=instructions,
        text_format=PracticeMentorSupport,
    )

    return response.output_parsed