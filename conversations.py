import apiaccess
import uuid
import random

gender = ""
age = ""
caseid = uuid.uuid4().hex
idkey = "" #your infermedica id and key goes here like:- if id is xyz and key is abc then idkey="xyz:abc"
model = "infermedica-en"

GREETING_INPUTS = ("hello", "hi", "hiii", "hii", "hiiii", "hiiii", "greetings", "sup", "what's up", "hey", 'yooooooooo', 'yoooooooo', 'yoooo')
GREETING_RESPONSES = ["hi", "hey", "hii there", "hi there", "hello", "I am glad! You are talking to me"]
MYSELF_RESPONSES = ["My name is HealthCare Bot.", "I am HealthCare Bot :) ", "My name is HealthCare Bot and I am ready to help you. :)"]

def interview(evidence, age, gender, caseid, auth, language_model=None):
    """Keep asking questions until API tells us to stop or the user gives an
    empty answer."""
    global triage_resp
    triage_resp = {}
    resp = apiaccess.call_diagnosis(evidence, age, gender, caseid, auth, language_model=language_model)
    #print("\n\n\nresp : ",resp)
    question_struct = resp['question']
    diagnoses = resp['conditions']
    should_stop_now = resp['should_stop']
    question = ""
    if should_stop_now:
        # Triage recommendation must be obtained from a separate endpoint,
        # call it now and return all the information together.
        triage_resp = apiaccess.call_triage(evidence, age, gender, caseid, auth, language_model=language_model)
        return evidence, diagnoses, triage_resp, question, question_items
    new_evidence = []
    if question_struct['type'] == 'single':
        # If you're calling /diagnosis in "disable_groups" mode, you'll
        # only get "single" questions. These are simple questions that
        # require a simple answer -- whether the observation being asked
        # for is present, absent or unknown.
        question_items = question_struct['items']
        assert len(question_items) == 1  # this is a single question
        question_item = question_items[0]
        question = "Q. : " + question_struct['text']
        return evidence, diagnoses, triage_resp, question, question_item
    else:
        # You'd need a rich UI to handle group questions gracefully.
        # There are two types of group questions: "group_single" (radio
        # buttons) and "group_multiple" (a bunch of single questions
        # gathered under one caption). Actually you can try asking
        # sequentially for each question item from "group_multiple"
        # question and then adding the evidence coming from all these
        # answers. For "group_single" there should be only one present
        # answer. It's recommended to include only this chosen answer as
        # present symptom in the new evidence. For more details, please
        # consult:
        # https://developer.infermedica.com/docs/diagnosis#group_single
        raise NotImplementedError("Group questions not handled in this example")
    evidence.extend(new_evidence)

def interview_q(evidence, age, gender, caseid, auth, que, question_items, user_response, language_model=None):
    """Keep asking questions until API tells us to stop or the user gives an
    empty answer."""
    global triage_resp
    triage_resp = {}
    new_evidence = []

    if(user_response.find("yes") != -1 or user_response.find("Yes") != -1):
        observation_value = "present"
    elif(user_response.find("no") != -1 or user_response.find("No") != -1):
        observation_value = "absent"
    else:
        observation_value = "unknown"
    
    new_evidence.extend(apiaccess.question_answer_to_evidence(question_items, observation_value))
    evidence.extend(new_evidence)

    resp = apiaccess.call_diagnosis(evidence, age, gender, caseid, auth, language_model=language_model)
    #print("\n\n\nresp : ",resp)
    question_struct = resp['question']
    diagnoses = resp['conditions']
    should_stop_now = resp['should_stop']
    question = ""
    if should_stop_now:
        question_item = ''
        # Triage recommendation must be obtained from a separate endpoint,
        # call it now and return all the information together.
        triage_resp = apiaccess.call_triage(evidence, age, gender, caseid, auth, language_model=language_model)
        return evidence, diagnoses, triage_resp, question, question_item
    if question_struct['type'] == 'single':
        # If you're calling /diagnosis in "disable_groups" mode, you'll
        # only get "single" questions. These are simple questions that
        # require a simple answer -- whether the observation being asked
        # for is present, absent or unknown.
        question_items = question_struct['items']
        assert len(question_items) == 1  # this is a single question
        question_item = question_items[0]
        question = "Q. : " + question_struct['text']
    else:
        # You'd need a rich UI to handle group questions gracefully.
        # There are two types of group questions: "group_single" (radio
        # buttons) and "group_multiple" (a bunch of single questions
        # gathered under one caption). Actually you can try asking
        # sequentially for each question item from "group_multiple"
        # question and then adding the evidence coming from all these
        # answers. For "group_single" there should be only one present
        # answer. It's recommended to include only this chosen answer as
        # present symptom in the new evidence. For more details, please
        # consult:
        # https://developer.infermedica.com/docs/diagnosis#group_single
        raise NotImplementedError("Group questions not handled in this example")
    
    return evidence, diagnoses, triage_resp, question, question_item

def summarise_some_evidence(evidence, header):
    op = header + ' :\n'
    for idx, piece in enumerate(evidence):
        op += '{:2}. {}\n'.format(idx + 1, mention_as_text(piece))
    return op

def summarise_all_evidence(evidence):
    reported = []
    answered = []
    for piece in evidence:
        (reported if piece.get('source')=='initial' else answered).append(piece)
    op1 = summarise_some_evidence(reported, 'Patient complaints')
    op2 = summarise_some_evidence(answered, 'Patient answers')
    return op1, op2

def summarise_diagnoses(diagnoses):
    op = 'Diagnoses :\n'
    for idx, diag in enumerate(diagnoses):
        op += '{:2}. {:.2f} {}\n'.format(idx + 1, diag['probability'], diag['name'])
    return op

def summarise_triage(triage_resp):
    op = 'Triage level: {}\n'.format(triage_resp['triage_level'])
    teleconsultation_applicable = triage_resp.get('teleconsultation_applicable')
    if teleconsultation_applicable is not None:
        op += 'Teleconsultation applicable: {}\n'.format(teleconsultation_applicable)
    return op

def output():
    op = ''
    op1, op2 = summarise_all_evidence(evidence)
    op3 = summarise_diagnoses(diagnoses)
    op4 = summarise_triage(triage)
    op = '\n' + op1 + '\n' + op2 + '\n' + op3 + '\n' + op4
    return op

def diagnostic_question():
    global evidence, diagnoses, triage, question_items
    evidence = apiaccess.mentions_to_evidence(mentions)
    evidence, diagnoses, triage, question, question_items = interview(evidence, age, gender, caseid, idkey, model)
    #print("Evidence : ",evidence)
    #print("\n\n\nDiagnoses : ",diagnoses)
    #print("\n\n\nTriage : ",triage)
    #print("\n\n\nQuestion : ",question_items)
    if(question == ''):
        apiaccess.name_evidence(evidence, naming)
        return output()
    else:
        return question

def diagnostic_questions(que, user_response):
    global evidence, diagnoses, triage, question_items
    #evidence = apiaccess.mentions_to_evidence(mentions)
    evidence, diagnoses, triage, question, question_items = interview_q(evidence, age, gender, caseid, idkey, que, question_items, user_response.lower(), model)
    #print("Evidence : ",evidence)
    #print("\n\n\nDiagnoses : ",diagnoses)
    #print("\n\n\nTriage : ",triage)
    #print("\n\n\nQuestion : ",question_items)
    if(question == ''):
        apiaccess.name_evidence(evidence, naming)
        return output()
    else:
        return question

def mention_as_text(mention):
    """Represents the given mention structure as simple textual summary.
    Args:
        mention (dict): Response containing information about medical concept.
    Returns:
        str: Formatted name of the reported medical concept, e.g. +Dizziness,
            -Headache.
    """
    _modality_symbol = {"present": "+", "absent": "-", "unknown": "?"}
    name = mention["name"]
    symbol = _modality_symbol[mention["choice_id"]]
    return "{}{}, ".format(symbol, name)

def context_from_mentions(mentions):
    """Returns IDs of medical concepts that are present."""
    return [m['id'] for m in mentions if m['choice_id'] == 'present']

def read_complaints(user_response):
    """Keeps reading complaint-describing messages from user until empty
    message is read (or just read the story if given). Will call the /parse
    endpoint and return mentions captured there.
    Args:
        age (dict): Patients age in {'value': int, 'unit': str} format.
        gender (str): Patients gender.
        auth_string (str): Authentication string.
        caseid (str): Case ID.
        lanugage_model (str): Chosen language model.
    Returns:
        list: Mentions extracted from user answers.
    """
    global mentions
    mentions = []
    context = []  # List of ids of present symptoms in the order of reporting.
    answer = "Noting : "
    b = apiaccess.call_parse(age, gender, user_response, idkey, caseid, context, language_model=model)
    portion = b.get('mentions', [])
    for p in portion:
        ans = mention_as_text(p)
        answer += ans
    mentions.extend(portion)
    # Remember the mentions understood as context for next /parse calls
    context.extend(context_from_mentions(portion))
    return answer

def IntroduceMe(sentence):
    a = random.choice(MYSELF_RESPONSES)
    return ''.join(str(b) for b in a)

def greeting(sentence):
    for word in sentence.split():
        if word.lower() in GREETING_INPUTS:
            return random.choice(GREETING_RESPONSES)

def read_gender(a):
    global gender
    if(a.lower() == 'male'):
        gender = 'male'
        return "Please enter symptoms : "
    elif(a.lower() == 'female'):
        gender = 'female'
        return "Please enter symptoms : "
    else:
        return "Couldn't understand. Please enter your gender(male/female) : "
def read_age(a):
    global naming
    global age
    if(int(a) < 12):
        return "Ages below 12 are not yet supported. Please enter your age : "
    elif(int(a) > 100):
        return "Maximum supported age is 100. Please enter your age : "
    else:
        age = int(a)
        age = {'value': age, 'unit': 'year'}
        naming = apiaccess.get_observation_names(age, idkey, caseid, model)
        #print("Naming : ",naming)
        return "Please enter your gender(male/female) : "


def chat(user_response):
    user_response = user_response.lower()
    keyword = "not well"
    keyword1 = "not feeling well"
    keyword2 = "ill"
    keyword3 = "symptoms"
    keyword4 = "Symptom"

    if (user_response == 'bye' or user_response == 'byy' or user_response == 'by'):
        return "Bye! take care.."
    elif (user_response == 'thanks' or user_response == 'thank you'):
        return "You are welcome.."
    else:
        if (user_response.find(keyword) != -1 or user_response.find(keyword1) != -1 or user_response.find(keyword2) != -1  or user_response.find(keyword3) != -1  or user_response.find(keyword4) != -1):
            return "Sorry to hear that...Please enter your age : "
        elif (greeting(user_response) != None):
            return greeting(user_response)
        elif(user_response.lower().find("who are you?") != -1 or user_response.lower().find("your name?") != -1 or user_response.lower().find("can you describe your self?") != -1):
            return IntroduceMe(user_response)
        else:
            return "Sorry. I didn't get it...."
        