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
    PracticeMicroCheckValidation,
    PracticeMicroCheckSupport,
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
    preferred_language: str = "auto",
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
    Primary concept to address:
    {diagnosis.primary_missing_concept_id}

    Concepts already demonstrated:
    {diagnosis.understood_concept_ids}

    Backend Mentor Decision:
    {decision_text}

    Preferred language:
    {preferred_language}
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
- Teach the smallest concept necessary to resolve the
  primary_missing_concept_id.

- Do not introduce related techniques unless they are required
  by the primary concept.

- For dictionary_key_access:
  teach only how to retrieve the value of an EXISTING dictionary key.

- Do not introduce dict.get(), key existence checks, KeyError handling,
  default values, or the "in" operator unless the diagnosis specifically
  identifies one of those as the primary problem.

- A micro-check for dictionary_key_access must use an existing key
  and ask only how to access its value.

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


LANGUAGE RULES:

- preferred_language = "tr":
  Respond in Turkish.

- preferred_language = "en":
  Respond in English.

- preferred_language = "nl":
  Respond in Dutch.

- preferred_language = "auto":
  Infer the most appropriate language from the challenge
  and learner context.

- Keep programming keywords, Python syntax, SQL syntax,
  variable names, and code in their original technical form.

- The language choice must not change concept IDs or
  backend terminology.

- Natural-language explanations should follow preferred_language.

- All code examples must use English ASCII variable names and identifiers,
  even when the explanation language is Turkish or Dutch.
"""

    response = client.responses.parse(
        model="gpt-5-mini",
        input=prompt,
        instructions=instructions,
        text_format=PracticeMentorSupport,
    )

    return response.output_parsed

# ==================================================
# PRACTICE MICRO-CHECK EVALUATION
# ==================================================


def evaluate_practice_micro_check(
    question: str,
    answer: str,
    primary_concept_id: str,
    preferred_language: str = "auto",
) -> PracticeMicroCheckValidation:
    """
    Mentorun sorduğu küçük micro-check sorusuna
    junior'ın verdiği cevabı değerlendirir.

    Bu fonksiyon original challenge'ı çözmez.
    Sadece micro-check cevabının hedef kavramı
    gösterip göstermediğine karar verir.
    """

    prompt = f"""
Micro-check question:
{question}

Learner answer:
{answer}

Primary concept being checked:
{primary_concept_id}

Preferred language:
{preferred_language}
"""

    instructions = """
You evaluate a junior Data Engineer's answer
to a small mentor micro-check.

Your job is ONLY to evaluate the micro-check answer.

Rules:

1. Judge only the micro-check question.
   Do not evaluate or solve the original challenge.

2. success = true only if the learner's answer
   demonstrates the primary concept correctly.

3. Accept semantically equivalent answers.
   Minor formatting differences, whitespace,
   or quote style should not make a correct answer fail.

4. If the answer is wrong:
   - give short feedback,
   - do NOT reveal the correct answer,
   - do NOT write corrected code,
   - do NOT provide the solution.

5. If the answer is correct:
   give brief confirmation only.

6. Keep feedback focused on the single
   primary concept.

LANGUAGE RULES:

- preferred_language = "tr":
  feedback must be Turkish.

- preferred_language = "en":
  feedback must be English.

- preferred_language = "nl":
  feedback must be Dutch.

- preferred_language = "auto":
  use the most appropriate language from the context.

Return only PracticeMicroCheckValidation.
"""

    response = client.responses.parse(
        model="gpt-5-mini",
        input=prompt,
        instructions=instructions,
        text_format=PracticeMicroCheckValidation,
    )

    return response.output_parsed

# ==================================================
# PRACTICE MICRO-CHECK EXTRA SUPPORT
# ==================================================


def generate_practice_micro_check_support(
    question: str,
    answer: str,
    primary_concept_id: str,
    micro_check_attempt_number: int,
    preferred_language: str = "auto",
) -> PracticeMicroCheckSupport:
    """
    Yanlış micro-check cevabından sonra
    hedef kavram için ek destek üretir.

    Original challenge bu fonksiyona verilmez.
    Böylece çözüm sızıntısı önlenir.
    """

    prompt = f"""
Micro-check question:
{question}

Learner's incorrect answer:
{answer}

Primary concept:
{primary_concept_id}

Micro-check attempt number:
{micro_check_attempt_number}

Preferred language:
{preferred_language}
"""

    instructions = """
You are supporting a junior Data Engineer
after an incorrect micro-check answer.

Your job is to help with ONLY the primary concept.

IMPORTANT RULES:

1. Do not solve the original challenge.
   You do not have access to it.

2. Do not give the correct answer to the
   micro-check question.

3. Do not write a corrected version of the
   learner's answer.

4. Do not create a new micro-check question.
   The learner will retry the same question.

5. Keep the support focused on one concept only.

6. If micro_check_attempt_number == 1:
   give a short conceptual hint.

7. If micro_check_attempt_number >= 2:
   explain the concept a little more explicitly,
   but still do not reveal the exact answer.

8. Use a different generic example only if needed.
   Never reuse the micro-check's exact variables,
   keys, or values in that example.

9. Teach ONLY the minimum concept required by
   primary_concept_id.

10. Do not introduce adjacent concepts unless
    they are themselves the primary concept.

11. For dictionary_key_access specifically:
    teach only how to retrieve the value of an
    existing dictionary key.

    Do NOT discuss:
    - KeyError
    - missing keys
    - .get()
    - default values
    - checking whether a key exists

12. Do not repeat the learner's exact incorrect
    expression in the support message.

LANGUAGE:

- tr → Turkish
- en → English
- nl → Dutch
- auto → infer appropriate language

Technical terms and Python syntax may remain English.

Return only PracticeMicroCheckSupport.
"""

    response = client.responses.parse(
        model="gpt-5-mini",
        input=prompt,
        instructions=instructions,
        text_format=PracticeMicroCheckSupport,
    )

    return response.output_parsed