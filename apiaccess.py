import requests
infermedica_url = 'https://api.infermedica.com/v3/{}'

def get_observation_names(age, auth_string, caseid, language_model=None):
    """Call /symptoms and /risk_factors to obtain full lists of all symptoms
    and risk factors along with their metadata. Those metadata include names
    and this is what we're after. Observations may contain both symptoms and
    risk factors. Their ids indicate concept type (symptoms are prefixed s_,
    risk factors -- p_)."""
    obs_structs = []
    obs_structs.extend(
        call_endpoint('risk_factors', auth_string, {'age.value': age['value'], 'age.unit': age['unit']}, None, caseid=caseid, language_model=language_model))
    obs_structs.extend(
        call_endpoint('symptoms', auth_string, {'age.value': age['value'], 'age.unit': age['unit']}, None, caseid=caseid, language_model=language_model))
    return {struct['id']: struct['name'] for struct in obs_structs}

def _remote_headers(auth_string, caseid, language_model=None):
    app_id, app_key = auth_string.split(':')
    headers = {
        'Content-Type': 'application/json',
        'Dev-Mode': 'true',  # please turn this off when your app goes live
        'Interview-Id': caseid,
        'App-Id': app_id,
        'App-Key': app_key}
    if language_model:
        headers['Model'] = language_model
    return headers

def call_endpoint(endpoint, auth_string, params, request_spec, caseid, language_model=None):
    if auth_string and ':' in auth_string:
        url = infermedica_url.format(endpoint)
        headers = _remote_headers(auth_string, caseid, language_model)
    else:
        raise IOError('need App-Id:App-Key auth string')
    if language_model:
        # name of a model that designates a language and possibly a
        # non-standard knowledge base e.g. infermedica-es
        # (the default model is infermedica-en)
        # extract the language code if model name provided
        if '-' in language_model:
            lang_code = language_model.split('-')[-1]
        else:
            lang_code = language_model
        headers['Language'] = lang_code
    if request_spec:
        resp = requests.post(
            url,
            params=params,
            json=request_spec,
            headers=headers)
    else:
        resp = requests.get(
            url,
            params=params,
            headers=headers)
    resp.raise_for_status()
    #print("\n\n\n")
    #print(resp.json())
    return resp.json()

def call_parse(age, gender, text, auth_string, caseid, context=(),
               conc_types=('symptom', 'risk_factor',), language_model=None):
    """Process the user message (text) via Infermedica NLP API (/parse) to 
    capture observations mentioned there. Return a list of dicts, each of them
    representing one mention. A mention refers to one concept (e.g. abdominal
    pain), its status/modality (present/absent/unknown) + some additional
    details. Providing context of previously understood observations may help
    make sense of partial information in some cases. Context should be a list
    of strings, each string being an id of a present observation reported so
    far, in the order of reporting. 
    See https://developer.infermedica.com/docs/nlp ("contextual clues").
    """
    request_spec = {
       'age': age,
       'sex': gender,
       'text': text,
       'context': list(context),
       'include_tokens': True,
       'concept_types': conc_types,
       }
    return call_endpoint('parse', auth_string, None, request_spec, caseid,
                         language_model=language_model)

def mentions_to_evidence(mentions):
    """Convert mentions (from /parse endpoint) to evidence structure as
    expected by the /diagnosis endpoint.
    """
    return [{'id': m['id'], 'choice_id': m['choice_id'], 'source': 'initial'} for m in mentions]

def call_diagnosis(evidence, age, gender, caseid, auth_string, no_groups=True,
                   language_model=None):
    """Call the /diagnosis endpoint.
    Input: evidence and patient basic data (age and gender).
    Output:
    1. next question to be answered by the patient (differential diagnosis);
    2. current outlook (list of diagnoses with probability estimates);
    3. "stop now" flag -- if the diagnostic engine recommends to stop asking
       questions now and present
    the current outlook as final results.
    Use no_groups to turn off group questions (they may be both single-choice
    questions and multiple questions gathered together under one subtitle; it's
    hard to handle such questions in voice-only chatbot).
    """
    request_spec = {
        'age': age,
        'sex': gender,
        'evidence': evidence,
        'extras': {
            # voice/chat apps usually can't handle group questions well
            'disable_groups': no_groups
        }
    }
    return call_endpoint('diagnosis', auth_string, None, request_spec, caseid, language_model)

def call_triage(evidence, age, gender, caseid, auth_string, language_model=None):
    """Call the /triage endpoint.
    Input: evidence and patient basic data (age and gender).
    Output:
    1. next question to be answered by the patient (differential diagnosis);
    2. current outlook (list of diagnoses with probability estimates);
    3. "stop now" flag -- if the diagnostic engine recommends to stop asking
       questions now and present
    the current outlook as final results.
    Use no_groups to turn off group questions (they may be both single-choice
    questions and multiple questions gathered together under one subtitle; it's
    hard to handle such questions in voice-only chatbot).
    """
    request_spec = {
        'age': age,
        'sex': gender,
        'evidence': evidence
    }
    return call_endpoint('triage', auth_string, None, request_spec, caseid, language_model)

def question_answer_to_evidence(question_struct_item, observation_value):
    """Return new evidence obtained via abswering the one item contained in a
    question with the given observation value (status)."""
    return [{'id': question_struct_item['id'], 'choice_id': observation_value}]

def name_evidence(evidence, naming):
    """Add "name" field to each piece of evidence."""
    for piece in evidence:
        piece['name'] = naming[piece['id']]