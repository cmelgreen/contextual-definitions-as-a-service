import urllib.request
import json
import os
import re


def get_sense_by_sn(sense_number, entry):
    def loop_entry(entry):
        x = entry
        for sn in sense_number:
            x = x[sn]

        return x['def']

    try: return loop_entry(entry)  
    except: pass

    # check for implicit references to transitive / intransitive verb if explicit path fails
    try: return loop_entry(entry['t'])
    except: pass

    try: return loop_entry(entry['i'])
    except: pass

    return ''

curr_num = ''
curr_let = ''

def reset():
    global curr_let
    global curr_num

    curr_num = ''
    curr_let = ''

def parse_resp(resp, all_defs=False):
    reset()
    entries = [parse_entry(entry) for entry in resp]
    
    if all_defs == True:
        return [non_empty for non_empty in entries if non_empty]
    
    for entry in entries:
        entry['def'] = get_sense_by_sn(entry['sn'], entry['def'])
    
    entries = [e for e in entries if e['date'] and e['def']]

    return entries



def parse_entry(defs):
    (date, sn) = parse_date(defs)
    entry = unpack_defs(parse_defs(defs))

    if entry is None:
        return

    return {
        'date': date,
        'sn': sn,
        'def': entry
    }


def unpack_defs(defs):
    global curr_num
    global curr_let

    if isinstance(defs, dict):
        (key, value) = next(iter(defs.items()))
        key = str(key)

        if is_verb(key):
            return {key: unpack_defs(value)}
        else:
            return fmt_def(key, value)

    if isinstance(defs, list):
        def_dict = dict()

        # def reset_curr():
        #     nonlocal curr_num
        #     nonlocal curr_let

        #     curr_num = ''
        #     curr_let = ''


        for d in defs:
            if isinstance(d, list):
                def_dict.update(unpack_defs(d))
            if isinstance(d, dict):
                (key, value) = next(iter(d.items()))
                
                if is_number(key):
                    curr_num = key
                    def_dict.update(fmt_def(key, value))
                elif is_paren(key):
                    
                    def_dict[curr_num][curr_let].update(fmt_def(key, value))
                else:
                    keys = key.split()
                    
                    def nest_keys(keys):
                        global curr_num
                        global curr_let

                        key = keys[0]

                        if len(keys) > 1:

                            if is_number(key):
                                curr_num = key

                            if is_letter(key):
                                curr_let = key

                            return {key: nest_keys(keys[1:])}
                        else:
                            return (fmt_def(key, value))

                    if not curr_num or (is_number(keys[0]) and curr_num != keys[0]):
                        def_dict.update(nest_keys(keys))
                        
                    elif curr_num:
                        if curr_num in def_dict.keys():
                            def_dict[curr_num].update(fmt_def(key, value))
                        else:
                            return {str(key): unpack_defs(value)}

        return def_dict

def fmt_def(key, value):
    key = str(key)

    return {key: {'def': value}}

def is_number(string):
    try:
        int(string)
        return True
    except:
        return False

def is_paren(string):
    return '(' in string[0]

def is_letter(string):
    return string.isalpha()

def is_verb(string):
    return string == 't' or string == 'i'
        

# First Known Use: date
# Hierarchical Context
#   Top-level member of dictionary entry
# Data Model
#   "date" : string
def parse_date(entry):
    if isinstance(entry, dict):
        if 'date' in entry.keys():
            return clean_date(entry['date'])


    return ('', '')

def clean_date(date_string):
    date = int(re.search(r'[0-9]+', date_string).group())
    sn = re.findall(r'(?<=\|)[\w()]*', date_string) or ['1']
    sn = [non_empty for non_empty in sn if non_empty]

    # quick and dirty conversion of centuries 
    if date < 100:
        date = (date-1) * 100

    return (date, sn)



# Definition: def
# Hierarchical Context
#   Occurs as top-level member of dictionary entry and in dros.
# Data Model
#   array of one or more objects
def parse_defs(defs):
    if isinstance(defs, dict):
        defs = defs['def']

    for entry in defs:
        if is_vd(entry):
            return parse_vd(entry)

        elif is_sseq(entry):
            return parse_sseq(entry)


# Verb Divider: vd
# Hierarchical Context
#   Occurs in def, preceding an sls (optional) and sseq (required)
# Data Model
#   "vd" : string
def is_vd(vd):
    if isinstance(vd, dict):
        return 'vd' in vd.keys()
    
    return False

# Verbs can be transititive or intransitive and referenced as 'i' or 'v' in date
def parse_vd(vd):
    verb_type = 't'
    if 'intransitive' in vd['vd']:
        verb_type = 'i'

    return {verb_type: parse_sseq(vd['sseq'])}


#
# Shared logic for sseq and pseg
#
def parse_array(array):
    sense_list = []

    for sense in array:
        if is_sense(sense):
            sense_list.append(parse_sense(sense))
        elif is_bs(sense):
            sense_list.append(parse_bs(sense))
        elif is_pseq(sense):
            sense_list.append(parse_pseq(sense))
        elif isinstance(sense, list):
            sense_list.append(parse_array(sense))

    if len(sense_list) == 1:
        return sense_list[0]

    return sense_list


# Sense Sequence: sseq
# Hierarchical Context:
#   Occurs in def
# Data Model:
#   "sseq" : array
def is_sseq(sseq):
    if isinstance(sseq, dict):
        return 'sseq' in sseq.keys()

    return False

def parse_sseq(sseq):
    if isinstance(sseq, dict):
        sseq = sseq['sseq']

    sense_list=[]

    for array in sseq:
        sense_list.append(parse_array(array))

    if len(sense_list) == 1:
        return sense_list[0]

    return sense_list


# Parenthesised Sense Sequence:
# Hierarchical Context:
#   Occurs as an element in an sseq array.
# Data Model:
#   array consisting of one or more sense elements and an optional bs element.
def is_pseq(pseq):
    if isinstance(pseq, list):
        return pseq[0] == 'pseq'
    
    return False


def parse_pseq(pseq):
    sense_list = []

    for sense in pseq[1:]:
        sense_list.append(parse_array(sense))

    return sense_list


# Binding Substitution: bs
# Hierarchical Context
#   Occurs as an element in an sseq or pseq array, where it is followed by one or more sense elements.
# Data Model:
#   array of the form ["bs", {sense}]
def is_bs(bs):
    if isinstance(bs, list):
        return 'bs' == bs[0]
    
    return False


def parse_bs(bs):
    return parse_sense(bs[1])


# Sense: sense
# Hierarchical Context
#   Occurs as an element in an sseq array.
# Data Model:
#    object or array consisting of one dt (required) and zero or more et, ins, lbs, prs, sdsense, sgram, sls, sn, or vrs
def is_sense(sense):
    if isinstance(sense, dict):
        return 'sense' in sense.keys()
    elif isinstance(sense, list):
        return 'sense' == sense[0]
    
    return False


def parse_sense(sense):
    if isinstance(sense, dict):
        sense = sense['sense']
    elif isinstance(sense, list):
        sense = sense[1]
    else: return

    sn = 1
    if 'sn' in sense.keys():
        sn = sense['sn']


    sn = str(sn)

    dt = parse_dt(sense['dt'])
    if 'sdsense' in sense.keys():
        dt += parse_sdsense(sense['sdsense'])

    return {sn: dt}


# Divided Sense: sd
# Hierarchical Context
#   Occurs within a sense, where it is always preceded by dt.
# Data Model:
#   "sdsense" : object with the following members:
#   "sd" : string	sense divider (required)
#   et, ins, lbs, prs, sgram, sls, vrs	(optional)
#   dt	definition text (required)
def parse_sdsense(sdsense):
    return parse_dt(sdsense['dt'])


# Defining Text: dt
#Hierarchical Context
#   Occurs as an element in an sseq array.
# Data Model:
#   "dt" : array consisting of one or more elements:
#   ["text", string] where string contains the definition content (required)
#   optional bnw, ca, ri, snote, uns, or vis elements
def parse_dt(dt):
    for elem in dt:
        if elem[0] == 'text':
            ### Implement text cleaning
            return re.sub(r'\{[\w]*\}', '', elem[1]).strip()
